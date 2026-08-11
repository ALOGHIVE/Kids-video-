import json
import os
import random
import re
import time
from pathlib import Path

from google import genai


# ============================================================
# NOBINEST STORY GENERATOR
# ============================================================
# Generates short preschool stories for NobiNest.
#
# TARGET:
#   60-90 second finished videos
#   approximately 110-140 spoken words
#   exactly 4 visual scenes
#
# GEMINI:
#   Gemini is attempted first.
#   If Gemini is unavailable, quota-limited, deprecated,
#   or temporarily overloaded, a built-in story is used.
#
# This prevents the entire GitHub Actions workflow from
# failing just because Gemini is temporarily unavailable.
# ============================================================


OUTPUT_DIR = Path("output")

STORY_JSON = OUTPUT_DIR / "story.json"
STORY_TXT = OUTPUT_DIR / "story.txt"


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

# Put newer models first.
# The generator will discover models available to the API key
# and only attempt models that actually support generation.

PREFERRED_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]


MAX_GEMINI_ATTEMPTS_PER_MODEL = 2


# ============================================================
# CANONICAL CHARACTERS
# ============================================================

CHARACTER_BIBLE = {
    "Bobo": {
        "appearance": (
            "small friendly brown bear with soft fluffy brown fur, "
            "round face, small rounded ears, large expressive brown eyes, "
            "short arms and legs, and a bright yellow scarf"
        ),
        "personality": (
            "curious, playful, kind and slightly funny"
        ),
    },

    "Mimi": {
        "appearance": (
            "small friendly white rabbit with soft white fur, "
            "long rounded ears with pink inner ears, large expressive eyes, "
            "tiny pink nose, and a small purple backpack"
        ),
        "personality": (
            "clever, curious, patient and encouraging"
        ),
    },

    "Kiki": {
        "appearance": (
            "small cheerful yellow bird with bright yellow feathers, "
            "bright blue wings, large expressive eyes, "
            "and a small orange beak"
        ),
        "personality": (
            "energetic, musical, cheerful and playful"
        ),
    },
}


# ============================================================
# GEMINI PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the head writer for NobiNest, an original preschool
children's educational animation universe.

Audience:
Children approximately 3 to 7 years old.

Create one short, safe, educational episode.

HARD REQUIREMENTS:

1. Exactly 4 visual scenes.
2. Approximately 110 to 140 total spoken words.
3. Finished narration should normally produce approximately
   60 to 90 seconds of video.
4. Ideal finished duration is about 70 to 80 seconds.
5. Each scene should contain approximately 20 to 30 spoken words.
6. Include a very short educational song.
7. Include a very short closing message.
8. Teach exactly ONE simple preschool concept.

STYLE:

Use simple spoken English.

The story should be:
warm,
funny,
positive,
clear,
easy to understand,
easy to animate,
and appropriate for preschool children.

Do not include:
violence,
fear,
dangerous behavior,
romance,
politics,
religion,
death,
mature themes,
weapons,
scary monsters,
or inappropriate language.

Only use:
Bobo,
Mimi,
Kiki.

CANONICAL CHARACTERS:

Bobo:
small friendly brown bear with soft fluffy brown fur,
round face, small rounded ears, large expressive brown eyes,
short arms and legs, and a bright yellow scarf.
Personality: curious, playful, kind and slightly funny.

Mimi:
small friendly white rabbit with soft white fur,
long rounded ears with pink inner ears, large expressive eyes,
tiny pink nose, and a small purple backpack.
Personality: clever, curious, patient and encouraging.

Kiki:
small cheerful yellow bird with bright yellow feathers,
bright blue wings, large expressive eyes, and a small orange beak.
Personality: energetic, musical, cheerful and playful.

IMPORTANT:

Keep the character designs consistent.

Visual descriptions must describe things that can actually be
animated with simple 2D motion.

Examples:

walking,
hopping,
flying,
turning,
pointing,
reaching,
picking something up,
moving an object,
looking surprised,
clapping,
waving,
jumping,
dancing,
celebrating.

Do NOT write static image descriptions.

Return ONLY valid JSON.
Do not use markdown.
Do not wrap the JSON in ```.

Use exactly this structure:

{
  "title": "...",
  "lesson": "...",
  "characters": ["Bobo", "Mimi", "Kiki"],
  "character_bible": {
    "Bobo": {
      "appearance": "...",
      "personality": "..."
    },
    "Mimi": {
      "appearance": "...",
      "personality": "..."
    },
    "Kiki": {
      "appearance": "...",
      "personality": "..."
    }
  },
  "scenes": [
    {
      "scene_number": 1,
      "visual_description": "...",
      "narration": "..."
    },
    {
      "scene_number": 2,
      "visual_description": "...",
      "narration": "..."
    },
    {
      "scene_number": 3,
      "visual_description": "...",
      "narration": "..."
    },
    {
      "scene_number": 4,
      "visual_description": "...",
      "narration": "..."
    }
  ],
  "song": {
    "lyrics": "..."
  },
  "ending": "..."
}
"""


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")

    if not key:
        print("WARNING: GEMINI_API_KEY is not available.")
        print("Gemini generation will be skipped.")
        return None

    return key


def clean_json_text(text):
    """
    Remove accidental markdown fences if Gemini returns them.
    """

    if not text:
        raise ValueError("Gemini returned empty text.")

    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    return text.strip()


def count_spoken_words(story):
    total = 0

    for scene in story.get("scenes", []):
        total += len(
            str(scene.get("narration", "")).split()
        )

    song = story.get("song", {})

    if isinstance(song, dict):
        total += len(
            str(song.get("lyrics", "")).split()
        )

    total += len(
        str(story.get("ending", "")).split()
    )

    return total


# ============================================================
# STORY VALIDATION
# ============================================================

def validate_story(story):
    required = [
        "title",
        "lesson",
        "characters",
        "character_bible",
        "scenes",
        "song",
        "ending",
    ]

    for key in required:
        if key not in story:
            raise ValueError(
                f"Story is missing required field: {key}"
            )

    if story["characters"] != [
        "Bobo",
        "Mimi",
        "Kiki",
    ]:
        raise ValueError(
            "Story must use exactly Bobo, Mimi and Kiki."
        )

    if len(story["scenes"]) != 4:
        raise ValueError(
            "Story must contain exactly 4 scenes."
        )

    for character in [
        "Bobo",
        "Mimi",
        "Kiki",
    ]:
        if character not in story["character_bible"]:
            raise ValueError(
                f"Missing character bible entry: {character}"
            )

    for expected_number, scene in enumerate(
        story["scenes"],
        start=1,
    ):
        if scene.get("scene_number") != expected_number:
            raise ValueError(
                f"Invalid scene number: expected {expected_number}."
            )

        if not scene.get("visual_description"):
            raise ValueError(
                f"Scene {expected_number} has no visual description."
            )

        if not scene.get("narration"):
            raise ValueError(
                f"Scene {expected_number} has no narration."
            )

    if not isinstance(story["song"], dict):
        raise ValueError(
            "Song must be an object."
        )

    if not story["song"].get("lyrics"):
        raise ValueError(
            "Song lyrics are missing."
        )

    if not story.get("ending"):
        raise ValueError(
            "Ending is missing."
        )

    total_words = count_spoken_words(story)

    print(
        f"Story spoken-word count: {total_words}"
    )

    # Keep this reasonably flexible because actual spoken
    # duration depends on the TTS voice.
    if total_words < 95:
        raise ValueError(
            f"Story is too short: {total_words} words."
        )

    if total_words > 160:
        raise ValueError(
            f"Story is too long: {total_words} words."
        )

    return True


# ============================================================
# AVAILABLE GEMINI MODELS
# ============================================================

def get_available_models(client):
    """
    Ask Gemini which models are visible to this API key.

    We do not blindly assume that a model exists.
    """

    available = []

    print("")
    print("Checking available Gemini models...")

    try:
        for model in client.models.list():

            name = getattr(
                model,
                "name",
                "",
            )

            if not name:
                continue

            model_id = name.replace(
                "models/",
                "",
            )

            supported_methods = getattr(
                model,
                "supported_actions",
                None,
            )

            # Some API versions expose supported_actions,
            # while others may not.
            if supported_methods:
                supports_generation = (
                    "generateContent"
                    in supported_methods
                )
            else:
                supports_generation = True

            if (
                model_id in PREFERRED_MODELS
                and supports_generation
            ):
                available.append(model_id)

        print("Available preferred models:")

        if available:
            for model in available:
                print(f"  - {model}")
        else:
            print("  None of the preferred models were found.")

        return available

    except Exception as exc:
        print(
            "WARNING: Could not list Gemini models."
        )
        print(
            f"Reason: {exc}"
        )

        return []


# ============================================================
# GEMINI STORY GENERATION
# ============================================================

def generate_with_gemini(client, model_name):
    print("")
    print("=" * 55)
    print(f"Trying Gemini model: {model_name}")
    print("=" * 55)

    prompt = SYSTEM_PROMPT + """

Create ONE preschool episode.

Choose one simple concept such as:

counting,
colors,
shapes,
sharing,
sorting,
big and small,
same and different,
left and right,
morning and night,
clean and tidy,
or taking turns.

Do not teach multiple concepts.

Make the four scenes form one continuous story.

The song should reinforce the SAME lesson.

The ending should reinforce the SAME lesson.

Return valid JSON only.
"""

    last_error = None

    for attempt in range(
        1,
        MAX_GEMINI_ATTEMPTS_PER_MODEL + 1,
    ):

        print(
            f"Gemini request attempt "
            f"{attempt}/{MAX_GEMINI_ATTEMPTS_PER_MODEL}"
        )

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )

            text = clean_json_text(
                response.text
            )

            story = json.loads(text)

            validate_story(story)

            print(
                f"SUCCESS: Gemini generated "
                f"'{story['title']}'"
            )

            return story

        except Exception as exc:

            last_error = exc

            error_text = str(exc)

            print(
                f"Gemini request failed: "
                f"{error_text}"
            )

            # 404 usually means the model isn't usable.
            if "404" in error_text:
                print(
                    "Model is unavailable. "
                    "Moving to next model."
                )
                break

            # 429 means quota/rate limit.
            if "429" in error_text:
                print(
                    "Gemini quota/rate limit reached."
                )

                if attempt < MAX_GEMINI_ATTEMPTS_PER_MODEL:
                    print(
                        "Waiting briefly before retry..."
                    )
                    time.sleep(5)

                continue

            # 503 means temporary server overload.
            if "503" in error_text:
                print(
                    "Gemini service is temporarily "
                    "unavailable."
                )

                if attempt < MAX_GEMINI_ATTEMPTS_PER_MODEL:
                    print(
                        "Waiting 5 seconds before retry..."
                    )
                    time.sleep(5)

                continue

            # Other errors should still get another attempt
            # when possible.
            if attempt < MAX_GEMINI_ATTEMPTS_PER_MODEL:
                time.sleep(3)

    print("")
    print(
        f"Model {model_name} failed."
    )

    if last_error:
        print(
            f"Reason: {last_error}"
        )

    return None


def create_story_with_gemini():
    key = get_api_key()

    if not key:
        return None

    try:
        client = genai.Client(
            api_key=key
        )

    except Exception as exc:
        print(
            "Could not create Gemini client."
        )
        print(str(exc))
        return None

    available_models = get_available_models(
        client
    )

    if not available_models:
        print(
            "No usable preferred Gemini model "
            "was found."
        )

        return None

    for model_name in available_models:

        story = generate_with_gemini(
            client,
            model_name,
        )

        if story:
            return story

        print(
            "Trying the next available model..."
        )

    return None


# ============================================================
# FALLBACK STORY BANK
# ============================================================
# These stories guarantee that the workflow can continue
# when Gemini is unavailable.
#
# Each story:
#   exactly 4 scenes
#   one lesson
#   song
#   ending
#
# The stories are intentionally different so repeated
# fallback runs do not produce the same episode every day.
# ============================================================

FALLBACK_STORIES = [

    {
        "title": "Bobo Counts the Apples",
        "lesson": "Counting from one to three",
        "characters": [
            "Bobo",
            "Mimi",
            "Kiki",
        ],
        "character_bible": CHARACTER_BIBLE,
        "scenes": [
            {
                "scene_number": 1,
                "visual_description": (
                    "Bobo walks into the garden and notices "
                    "three bright apples on the grass. Mimi hops closer "
                    "while Kiki flies down to look."
                ),
                "narration": (
                    "Bobo finds some apples in the garden. "
                    "Mimi asks, how many are there? "
                    "Kiki flies closer to help them count."
                ),
            },
            {
                "scene_number": 2,
                "visual_description": (
                    "Bobo points to the first apple. Mimi points to "
                    "the second, and Kiki hops beside the third."
                ),
                "narration": (
                    "Bobo points to the first apple and says one. "
                    "Mimi points to the second and says two. "
                    "Kiki points to the third and says three."
                ),
            },
            {
                "scene_number": 3,
                "visual_description": (
                    "The three friends move the apples into a neat row "
                    "and count them together while gently bouncing."
                ),
                "narration": (
                    "They put the apples in a neat little row. "
                    "Together they count again: one, two, three. "
                    "Everyone gets the answer right."
                ),
            },
            {
                "scene_number": 4,
                "visual_description": (
                    "Bobo, Mimi and Kiki clap and bounce beside the "
                    "three apples, then point to each one together."
                ),
                "narration": (
                    "Bobo smiles proudly. Mimi claps, and Kiki sings. "
                    "When we count carefully, numbers help us know "
                    "how many things we have."
                ),
            },
        ],
        "song": {
            "lyrics": (
                "One, two, three, count with me! "
                "One, two, three, happy as can be!"
            )
        },
        "ending": (
            "Count carefully and have fun!"
        ),
    },

    {
        "title": "Mimi Finds the Shapes",
        "lesson": "Recognizing circles, squares and triangles",
        "characters": [
            "Bobo",
            "Mimi",
            "Kiki",
        ],
        "character_bible": CHARACTER_BIBLE,
        "scenes": [
            {
                "scene_number": 1,
                "visual_description": (
                    "Mimi hops along a garden path and discovers "
                    "a round shape. Bobo walks over and Kiki flies above."
                ),
                "narration": (
                    "Mimi sees a round shape on the path. "
                    "She points and says, look! It is a circle. "
                    "Bobo and Kiki come to see."
                ),
            },
            {
                "scene_number": 2,
                "visual_description": (
                    "Bobo picks up a square card and turns it around. "
                    "Mimi points to its four straight sides."
                ),
                "narration": (
                    "Next, Bobo finds a square. "
                    "It has four straight sides and four corners. "
                    "Mimi smiles because she knows its shape."
                ),
            },
            {
                "scene_number": 3,
                "visual_description": (
                    "Kiki flies down beside a triangle card and taps "
                    "each corner with one wing."
                ),
                "narration": (
                    "Kiki finds a triangle. "
                    "It has three corners. "
                    "The friends look at the circle, square and triangle "
                    "and name each one together."
                ),
            },
            {
                "scene_number": 4,
                "visual_description": (
                    "The friends arrange the three shapes in a row, "
                    "then bounce and clap around them."
                ),
                "narration": (
                    "Now the three friends can spot their shapes. "
                    "A circle is round, a square has four corners, "
                    "and a triangle has three."
                ),
            },
        ],
        "song": {
            "lyrics": (
                "Circle round, square has four, "
                "triangle has three corners!"
            )
        },
        "ending": (
            "Look around and find a shape!"
        ),
    },

    {
        "title": "Kiki Sorts the Colors",
        "lesson": "Sorting objects by color",
        "characters": [
            "Bobo",
            "Mimi",
            "Kiki",
        ],
        "character_bible": CHARACTER_BIBLE,
        "scenes": [
            {
                "scene_number": 1,
                "visual_description": (
                    "Kiki flies over a group of colorful balls and lands "
                    "beside them. Bobo and Mimi walk over."
                ),
                "narration": (
                    "Kiki finds colorful balls scattered on the grass. "
                    "Some are red, some are blue, and some are yellow. "
                    "The friends decide to sort them."
                ),
            },
            {
                "scene_number": 2,
                "visual_description": (
                    "Bobo picks up red balls and places them together. "
                    "Mimi moves blue balls into a second group."
                ),
                "narration": (
                    "Bobo picks up the red balls and puts them together. "
                    "Mimi gathers the blue balls into another group. "
                    "They look neat already."
                ),
            },
            {
                "scene_number": 3,
                "visual_description": (
                    "Kiki carries yellow balls through the air and drops "
                    "them gently beside the other yellow balls."
                ),
                "narration": (
                    "Kiki carries the yellow balls to their group. "
                    "Now each color has its own little space. "
                    "The friends check every ball carefully."
                ),
            },
            {
                "scene_number": 4,
                "visual_description": (
                    "The friends point at each color group, then clap "
                    "and dance around the neatly sorted balls."
                ),
                "narration": (
                    "Red goes with red, blue goes with blue, "
                    "and yellow goes with yellow. "
                    "Sorting by color makes things easy to find."
                ),
            },
        ],
        "song": {
            "lyrics": (
                "Red with red, blue with blue, "
                "yellow finds its friends too!"
            )
        },
        "ending": (
            "Sort by color and keep learning!"
        ),
    },

    {
        "title": "Bobo Learns to Take Turns",
        "lesson": "Taking turns when playing together",
        "characters": [
            "Bobo",
            "Mimi",
            "Kiki",
        ],
        "character_bible": CHARACTER_BIBLE,
        "scenes": [
            {
                "scene_number": 1,
                "visual_description": (
                    "Bobo reaches for a bright ball while Mimi and Kiki "
                    "watch. Bobo pauses and looks at his friends."
                ),
                "narration": (
                    "Bobo sees a bright ball and wants to play. "
                    "Mimi wants a turn too, and Kiki flaps excitedly. "
                    "They need a fair way to play."
                ),
            },
            {
                "scene_number": 2,
                "visual_description": (
                    "Bobo rolls the ball to Mimi. Mimi catches it "
                    "and rolls it gently toward Kiki."
                ),
                "narration": (
                    "Bobo rolls the ball to Mimi. "
                    "Mimi catches it and rolls it to Kiki. "
                    "Everyone gets a chance to play."
                ),
            },
            {
                "scene_number": 3,
                "visual_description": (
                    "Kiki rolls the ball back to Bobo. The three friends "
                    "continue passing it around in a happy circle."
                ),
                "narration": (
                    "Kiki rolls the ball back to Bobo. "
                    "The friends keep taking turns. "
                    "Nobody has to wait forever, because everyone gets "
                    "a chance."
                ),
            },
            {
                "scene_number": 4,
                "visual_description": (
                    "The friends form a little circle and pass the ball "
                    "around while smiling and clapping."
                ),
                "narration": (
                    "Bobo smiles and says, taking turns is fun. "
                    "Mimi nods, and Kiki dances. "
                    "When everyone gets a turn, everyone can enjoy playing."
                ),
            },
        ],
        "song": {
            "lyrics": (
                "My turn, your turn, everyone's turn! "
                "Take a turn and have some fun!"
            )
        },
        "ending": {
            "text": "Take turns and play together!"
        },
    },
]


# ============================================================
# FIX FALLBACK ENDING FORMAT
# ============================================================

def normalize_fallback_story(story):
    """
    Makes sure fallback stories always have the exact format
    expected by the renderer.
    """

    if isinstance(story.get("ending"), dict):
        story["ending"] = story["ending"].get(
            "text",
            "Keep learning and have fun!",
        )

    return story


# ============================================================
# FALLBACK SELECTION
# ============================================================

def create_fallback_story():
    """
    Select a fallback story.

    Uses the GitHub Actions run number when available so
    scheduled runs naturally rotate through the story bank.
    """

    run_number = os.environ.get(
        "GITHUB_RUN_NUMBER"
    )

    if run_number:
        try:
            index = (
                int(run_number) - 1
            ) % len(FALLBACK_STORIES)

        except ValueError:
            index = random.randrange(
                len(FALLBACK_STORIES)
            )
    else:
        index = random.randrange(
            len(FALLBACK_STORIES)
        )

    story = json.loads(
        json.dumps(
            FALLBACK_STORIES[index]
        )
    )

    story = normalize_fallback_story(
        story
    )

    validate_story(story)

    print("")
    print("=" * 55)
    print("FALLBACK STORY SYSTEM")
    print("=" * 55)
    print(
        "Gemini was unavailable."
    )
    print(
        "Using built-in NobiNest episode."
    )
    print(
        f"Selected: {story['title']}"
    )
    print("=" * 55)

    return story


# ============================================================
# MAIN STORY CREATION
# ============================================================

def create_story():
    """
    Try Gemini first.

    If Gemini cannot generate a story, automatically use
    the fallback story system.
    """

    print("")
    print("=" * 55)
    print("NOBINEST STORY GENERATOR")
    print("TARGET: 60-90 SECOND EPISODES")
    print("IDEAL: 70-80 SECONDS")
    print("=" * 55)

    print("")
    print(
        "Target spoken words: approximately 110-140"
    )

    story = create_story_with_gemini()

    if story is not None:
        print("")
        print(
            "STORY SOURCE: GEMINI"
        )
        return story

    print("")
    print(
        "Gemini could not generate an episode."
    )
    print(
        "The workflow will continue using the "
        "NobiNest fallback story system."
    )

    return create_fallback_story()


# ============================================================
# SAVE STORY
# ============================================================

def save_story(story):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # JSON
    with open(
        STORY_JSON,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            story,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # Human-readable text
    parts = [
        story["title"],
        "",
        f"Lesson: {story['lesson']}",
        "",
    ]

    for scene in story["scenes"]:

        parts.append(
            f"Scene {scene['scene_number']}"
        )

        parts.append(
            scene["narration"]
        )

        parts.append("")

    parts.extend([
        "Song",
        story["song"]["lyrics"],
        "",
        "Ending",
        story["ending"],
        "",
    ])

    with open(
        STORY_TXT,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n".join(parts)
        )

    print("")
    print(
        "Story saved successfully."
    )
    print(
        f"JSON: {STORY_JSON}"
    )
    print(
        f"TXT:  {STORY_TXT}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

def main():

    try:

        story = create_story()

        save_story(story)

        total_words = count_spoken_words(
            story
        )

        print("")
        print("=" * 55)
        print("STORY GENERATION COMPLETE")
        print("=" * 55)
        print(
            f"Title: {story['title']}"
        )
        print(
            f"Lesson: {story['lesson']}"
        )
        print(
            f"Scenes: {len(story['scenes'])}"
        )
        print(
            f"Spoken words: {total_words}"
        )
        print(
            "Target duration: 60-90 seconds"
        )
        print("=" * 55)

    except Exception as exc:

        print("")
        print("=" * 55)
        print("STORY GENERATOR ERROR")
        print("=" * 55)
        print(str(exc))
        print("=" * 55)

        raise


if __name__ == "__main__":
    main()
