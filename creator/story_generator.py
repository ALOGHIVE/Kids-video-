import json
import os
import re
import time

from google import genai


# ============================================================
# NOBINEST KIDS STORY GENERATOR
# ============================================================
# Generates short preschool educational stories for the
# NobiNest animated video system.
#
# TARGET:
#   60-90 second finished videos
#
# IMPORTANT:
#   The actual duration is determined by the narration.
#   Therefore we target approximately 145-175 spoken words.
#
# The generator also includes:
#   - Gemini model fallback
#   - Automatic retry for temporary 503 errors
#   - JSON cleanup
#   - Strong story validation
#   - Exactly 4 scenes
#   - Consistent characters
#   - Animation-friendly visual descriptions
# ============================================================


OUTPUT_DIR = "output"

STORY_JSON = os.path.join(
    OUTPUT_DIR,
    "story.json"
)

STORY_TXT = os.path.join(
    OUTPUT_DIR,
    "story.txt"
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

# We try models in order.
#
# If the first model is temporarily unavailable,
# the generator automatically tries the next one.
#
# This prevents a temporary Gemini 503 from killing
# the entire GitHub Actions workflow.

MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]


MAX_RETRIES_PER_MODEL = 3

RETRY_DELAYS = [
    5,
    15,
    30,
]


# ============================================================
# STORY PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the head writer for NobiNest, an original preschool
children's educational animation universe.

AUDIENCE:
Children approximately 3 to 7 years old.

Your job is to create ONE short, entertaining and educational
episode that will be turned into a real 2D animated video.

============================================================
HARD DURATION REQUIREMENT
============================================================

The finished video must be between 60 and 90 seconds.

The narration engine speaks naturally, so the story should contain
approximately 145 to 175 total spoken words.

TARGET:
Approximately 155 to 165 spoken words.

Do NOT make the story extremely short.

Do NOT write 100-word stories.

Do NOT write 200+ word stories.

The spoken word count includes:

1. Scene narration
2. Song lyrics
3. Ending

The story should sound natural when spoken aloud.

============================================================
STORY STRUCTURE
============================================================

Exactly 4 visual scenes.

Each scene should contain approximately:

26 to 32 spoken words.

The episode should contain:

Scene 1:
A simple beginning that introduces the situation.

Scene 2:
The characters discover or explore the concept.

Scene 3:
The characters demonstrate or practice the lesson.

Scene 4:
The characters understand the lesson and celebrate.

Song:
A short educational song of approximately 15 to 20 spoken words.

Ending:
Approximately 5 to 8 spoken words.

The complete episode should feel like one coherent story.

============================================================
EDUCATIONAL REQUIREMENT
============================================================

Teach EXACTLY ONE simple preschool concept.

Examples:

Counting from 1 to 3
Colors
Shapes
Sharing
Taking turns
Being kind
Cleaning up
Big and small
Hot and cold
Near and far
Up and down
Healthy food
Hand washing
Good manners
Listening
Patience
Simple nature concepts

Do not teach multiple unrelated concepts.

The lesson must be demonstrated through the story.

============================================================
STYLE
============================================================

Use very simple spoken English.

The story should be:

Warm
Funny
Positive
Playful
Easy to understand
Memorable
Age appropriate

Use short sentences.

Avoid complicated vocabulary.

Avoid long explanations.

Avoid filler.

Avoid unnecessary dialogue.

No violence.

No frightening situations.

No dangerous behavior.

No romance.

No politics.

No religion.

No mature themes.

============================================================
CANONICAL CHARACTERS
============================================================

ONLY use:

Bobo
Mimi
Kiki

Never invent another character.

------------------------------------------------------------
BOBO
------------------------------------------------------------

Appearance:

Small friendly brown bear with soft fluffy brown fur,
round face, small rounded ears, large expressive brown eyes,
short arms and legs, and a bright yellow scarf.

Personality:

Curious, playful, kind and slightly funny.

------------------------------------------------------------
MIMI
------------------------------------------------------------

Appearance:

Small friendly white rabbit with soft white fur,
long rounded ears with pink inner ears, large expressive eyes,
tiny pink nose, and a small purple backpack.

Personality:

Clever, curious, patient and encouraging.

------------------------------------------------------------
KIKI
------------------------------------------------------------

Appearance:

Small cheerful yellow bird with bright yellow feathers,
bright blue wings, large expressive eyes, and a small orange beak.

Personality:

Energetic, musical, cheerful and playful.

============================================================
ANIMATION REQUIREMENT
============================================================

Every visual_description must describe things that can actually
be animated procedurally.

Use actions such as:

walking
running gently
hopping
flying
turning
waving
pointing
reaching
picking something up
placing something down
moving an object
looking around
jumping
bouncing
clapping
dancing
smiling
reacting
celebrating
interacting with another character

Do NOT describe:

cinematic photographs
static illustrations
photorealism
complex camera effects
things that cannot be represented by simple 2D animation

Characters must keep their canonical appearance.

============================================================
JSON REQUIREMENT
============================================================

Return ONLY valid JSON.

Do not use markdown.

Do not use code fences.

Do not write explanations before or after the JSON.

The JSON must have exactly this structure:

{
  "title": "Episode title",
  "lesson": "One sentence describing the lesson",
  "characters": ["Bobo", "Mimi", "Kiki"],
  "character_bible": {
    "Bobo": {
      "appearance": "exact canonical appearance",
      "personality": "exact personality"
    },
    "Mimi": {
      "appearance": "exact canonical appearance",
      "personality": "exact personality"
    },
    "Kiki": {
      "appearance": "exact canonical appearance",
      "personality": "exact personality"
    }
  },
  "scenes": [
    {
      "scene_number": 1,
      "visual_description": "Animation-friendly description",
      "narration": "Approximately 26-32 spoken words"
    },
    {
      "scene_number": 2,
      "visual_description": "Animation-friendly description",
      "narration": "Approximately 26-32 spoken words"
    },
    {
      "scene_number": 3,
      "visual_description": "Animation-friendly description",
      "narration": "Approximately 26-32 spoken words"
    },
    {
      "scene_number": 4,
      "visual_description": "Animation-friendly description",
      "narration": "Approximately 26-32 spoken words"
    }
  ],
  "song": {
    "lyrics": "Approximately 15-20 spoken words"
  },
  "ending": "Approximately 5-8 spoken words"
}

============================================================
FINAL QUALITY CHECK
============================================================

Before returning the JSON, internally check:

1. Exactly 4 scenes exist.
2. Only Bobo, Mimi and Kiki appear.
3. Exactly one educational lesson is taught.
4. Total spoken words are approximately 145-175.
5. The story has a clear beginning, middle and ending.
6. The song teaches or reinforces the lesson.
7. The ending is short.
8. Every visual description contains movement.
9. Character appearances remain consistent.
10. The output is valid JSON.
"""


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not available. "
            "Check your GitHub repository secret."
        )

    return key


def get_available_models(client):
    """
    Ask the Gemini API which models are actually available
    to this project.
    """

    available = []

    print("")
    print("Checking available Gemini models...")

    try:
        for model in client.models.list():

            name = getattr(model, "name", "")

            if not name:
                continue

            model_id = name.replace(
                "models/",
                ""
            )

            supported_methods = getattr(
                model,
                "supported_actions",
                []
            )

            if (
                model_id in PREFERRED_MODELS
                and (
                    not supported_methods
                    or "generateContent" in supported_methods
                )
            ):
                available.append(model_id)

        print("Available preferred models:")

        for model in available:
            print(f"  - {model}")

        return available

    except Exception as exc:

        print("WARNING: Could not list models.")
        print(str(exc))

        return PREFERRED_MODELS.copy()

# ============================================================
# JSON CLEANING
# ============================================================

def clean_json_response(text):
    """
    Gemini normally returns plain JSON, but occasionally it
    wraps the response in markdown code fences.

    Remove those fences before json.loads().
    """

    if not text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    # Remove markdown code fences.
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

        text = text.strip()

    # Sometimes the model adds text before or after JSON.
    # Try to isolate the outermost JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "Gemini response did not contain a valid JSON object."
        )

    text = text[start:end + 1]

    return text


# ============================================================
# GEMINI REQUEST
# ============================================================

def request_story(client, model):
    """
    Ask one Gemini model to generate the episode.

    Temporary server errors are retried automatically.
    """

    prompt = SYSTEM_PROMPT + """

Create a completely new NobiNest preschool episode now.

Choose one simple educational concept.

Make the story entertaining enough that a child would want
to watch another NobiNest episode.

Remember:

TARGET TOTAL SPOKEN WORDS:
145-175

IDEAL:
155-165

Exactly 4 scenes.

Return ONLY valid JSON.
"""

    for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):

        print(
            f"Gemini model: {model} "
            f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
        )

        try:

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            text = response.text

            if not text:
                raise RuntimeError(
                    "Gemini returned no text."
                )

            return text

        except Exception as exc:

            error_text = str(exc)

            print(
                f"Gemini request failed: {error_text}"
            )

            # Retry temporary server failures.
            temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "high demand" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "500" in error_text
                or "INTERNAL" in error_text
            )

            if not temporary_error:
                raise

            if attempt < MAX_RETRIES_PER_MODEL:

                delay = RETRY_DELAYS[
                    min(
                        attempt - 1,
                        len(RETRY_DELAYS) - 1,
                    )
                ]

                print(
                    f"Temporary Gemini error. "
                    f"Waiting {delay} seconds before retry..."
                )

                time.sleep(delay)

            else:

                print(
                    f"Model {model} failed after "
                    f"{MAX_RETRIES_PER_MODEL} attempts."
                )

    raise RuntimeError(
        f"Gemini model {model} could not generate a story."
    )


# ============================================================
# STORY CREATION
# ============================================================

def create_story():

    client = genai.Client(
        api_key=get_api_key()
    )

    last_error = None

    for model in MODELS:

        try:

            print("")
            print(
                "================================================"
            )
            print(
                f"Trying Gemini model: {model}"
            )
            print(
                "================================================"
            )

            raw_text = request_story(
                client,
                model,
            )

            cleaned = clean_json_response(
                raw_text
            )

            story = json.loads(
                cleaned
            )

            validate_story(
                story
            )

            print("")
            print(
                f"SUCCESS: Story generated with {model}"
            )

            return story

        except Exception as exc:

            last_error = exc

            print("")
            print(
                f"Model {model} could not generate "
                f"a valid story."
            )

            print(
                f"Reason: {exc}"
            )

            print(
                "Trying the next available model..."
            )

    raise RuntimeError(
        "All Gemini models failed.\n"
        f"Last error: {last_error}"
    )


# ============================================================
# STORY VALIDATION
# ============================================================

def count_words(text):
    """
    Count spoken words.
    """

    return len(
        str(text).split()
    )


def validate_story(story):

    # --------------------------------------------------------
    # Required top-level fields
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Characters
    # --------------------------------------------------------

    expected_characters = [
        "Bobo",
        "Mimi",
        "Kiki",
    ]

    if story["characters"] != expected_characters:

        raise ValueError(
            "Story must use exactly the canonical "
            "characters: Bobo, Mimi and Kiki."
        )

    # --------------------------------------------------------
    # Character bible
    # --------------------------------------------------------

    for character in expected_characters:

        if character not in story["character_bible"]:

            raise ValueError(
                f"Missing character bible entry: {character}"
            )

        bible = story["character_bible"][character]

        if not bible.get("appearance"):

            raise ValueError(
                f"{character} is missing appearance."
            )

        if not bible.get("personality"):

            raise ValueError(
                f"{character} is missing personality."
            )

    # --------------------------------------------------------
    # Scenes
    # --------------------------------------------------------

    scenes = story["scenes"]

    if not isinstance(scenes, list):

        raise ValueError(
            "Scenes must be a list."
        )

    if len(scenes) != 4:

        raise ValueError(
            f"Story must contain exactly 4 scenes. "
            f"Found {len(scenes)}."
        )

    total_words = 0

    expected_scene_numbers = [
        1,
        2,
        3,
        4,
    ]

    for index, scene in enumerate(scenes):

        scene_number = scene.get(
            "scene_number"
        )

        if scene_number != expected_scene_numbers[index]:

            raise ValueError(
                f"Invalid scene number: "
                f"{scene_number}"
            )

        visual = str(
            scene.get(
                "visual_description",
                ""
            )
        ).strip()

        narration = str(
            scene.get(
                "narration",
                ""
            )
        ).strip()

        if not visual:

            raise ValueError(
                f"Scene {scene_number} "
                f"is missing visual_description."
            )

        if not narration:

            raise ValueError(
                f"Scene {scene_number} "
                f"is missing narration."
            )

        scene_words = count_words(
            narration
        )

        print(
            f"Scene {scene_number}: "
            f"{scene_words} words"
        )

        # We allow a little flexibility because natural language
        # generation will not always hit an exact number.
        if scene_words < 22 or scene_words > 38:

            raise ValueError(
                f"Scene {scene_number} contains "
                f"{scene_words} words. "
                f"Expected approximately 26-32."
            )

        total_words += scene_words

    # --------------------------------------------------------
    # Song
    # --------------------------------------------------------

    song = story["song"]

    if not isinstance(song, dict):

        raise ValueError(
            "Song must be an object."
        )

    lyrics = str(
        song.get(
            "lyrics",
            ""
        )
    ).strip()

    if not lyrics:

        raise ValueError(
            "Song lyrics are missing."
        )

    song_words = count_words(
        lyrics
    )

    print(
        f"Song: {song_words} words"
    )

    if song_words < 12 or song_words > 25:

        raise ValueError(
            f"Song contains {song_words} words. "
            f"Expected approximately 15-20."
        )

    total_words += song_words

    # --------------------------------------------------------
    # Ending
    # --------------------------------------------------------

    ending = str(
        story.get(
            "ending",
            ""
        )
    ).strip()

    if not ending:

        raise ValueError(
            "Ending is missing."
        )

    ending_words = count_words(
        ending
    )

    print(
        f"Ending: {ending_words} words"
    )

    if ending_words < 4 or ending_words > 12:

        raise ValueError(
            f"Ending contains {ending_words} words. "
            f"Expected approximately 5-8."
        )

    total_words += ending_words

    # --------------------------------------------------------
    # Total word count
    # --------------------------------------------------------

    print("")
    print(
        f"TOTAL SPOKEN WORDS: {total_words}"
    )

    # This is intentionally wider than the ideal range.
    # The audio duration verification in the workflow remains
    # the final authority.
    if total_words < 135:

        raise ValueError(
            f"Story has only {total_words} spoken words. "
            f"It is too short for a 60-second episode."
        )

    if total_words > 185:

        raise ValueError(
            f"Story has {total_words} spoken words. "
            f"It is too long for the target episode."
        )

    if 145 <= total_words <= 175:

        print(
            "PASS: Story word count is in the ideal range."
        )

    else:

        print(
            "WARNING: Story is acceptable but outside "
            "the ideal 145-175 word range."
        )

    print("Story validation passed.")


# ============================================================
# SAVE STORY
# ============================================================

def save_story(story):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Human-readable TXT
    # --------------------------------------------------------

    parts = [
        story["title"],
        "",
        f"Lesson: {story['lesson']}",
        "",
    ]

    for scene in story["scenes"]:

        parts.extend(
            [
                f"Scene {scene['scene_number']}",
                "",
                "Visual:",
                scene["visual_description"],
                "",
                "Narration:",
                scene["narration"],
                "",
            ]
        )

    parts.extend(
        [
            "Song",
            "",
            story["song"]["lyrics"],
            "",
            "Ending",
            "",
            story["ending"],
        ]
    )

    with open(
        STORY_TXT,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "\n".join(parts)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 55)
    print("NOBINEST STORY GENERATOR")
    print("TARGET: 60-90 SECOND EPISODES")
    print("IDEAL: 70-80 SECONDS")
    print("=" * 55)

    print("")
    print(
        "Target spoken words: approximately 145-175"
    )

    print(
        "Gemini automatic model fallback: ENABLED"
    )

    print(
        "Temporary 503 retry protection: ENABLED"
    )

    print("")

    story = create_story()

    save_story(
        story
    )

    total_words = 0

    for scene in story["scenes"]:

        total_words += count_words(
            scene["narration"]
        )

    total_words += count_words(
        story["song"]["lyrics"]
    )

    total_words += count_words(
        story["ending"]
    )

    print("")
    print("=" * 55)
    print("STORY GENERATED SUCCESSFULLY")
    print("=" * 55)

    print(
        f"Title: {story['title']}"
    )

    print(
        f"Lesson: {story['lesson']}"
    )

    print(
        "Scenes: 4"
    )

    print(
        f"Spoken words: {total_words}"
    )

    print(
        "Target video duration: 60-90 seconds"
    )

    print(
        "Ideal video duration: 70-80 seconds"
    )

    print(
        f"Saved: {STORY_JSON}"
    )

    print(
        f"Saved: {STORY_TXT}"
    )

    print("=" * 55)


if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print("")
        print("=" * 55)
        print("STORY GENERATOR ERROR")
        print("=" * 55)

        print(
            str(exc)
        )

        print("=" * 55)

        raise
