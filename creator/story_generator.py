import json
import os
import re

from google import genai


# ============================================================
# OUTPUT FILES
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
# GEMINI MODEL
# ============================================================

MODEL = "gemini-3.6-flash"


# ============================================================
# STORY SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are the head writer for NobiNest, an original preschool
children's educational story universe.

Audience:
Children approximately 3 to 7 years old.

Your job is to create ONE short, entertaining and educational
animated episode.

============================================================
HARD EPISODE LENGTH REQUIREMENT
============================================================

The finished video must be between 60 and 90 seconds.

The ideal finished duration is approximately 70 to 80 seconds.

Write approximately 135 to 155 total spoken words.

This total includes:

1. Scene narration
2. Song lyrics
3. Ending message

Do NOT write a long story.

Do NOT add filler.

Do NOT add unnecessary dialogue.

Do NOT use long explanations.

The story must feel complete and natural while remaining short.

============================================================
STORY STRUCTURE
============================================================

Use exactly 4 visual scenes.

Each scene should contain approximately 24 to 30 spoken words.

Include one very short educational song.

The song should contain approximately 15 to 20 spoken words.

Include a short closing message of approximately 5 to 8 spoken words.

The episode should have:

1. A clear beginning.
2. A simple problem or question.
3. A lesson demonstration.
4. A clear educational conclusion.

Teach exactly ONE preschool concept.

Examples:

counting
colors
shapes
sharing
opposites
letters
numbers
simple patterns
cleanliness
kindness
taking turns
basic science
nature
weather
healthy habits

Do not combine multiple lessons.

============================================================
WRITING STYLE
============================================================

Use simple spoken English.

Sentences should be short.

Use language a 3 to 7 year old can understand.

Make the story warm, funny, playful and positive.

Characters should speak and act naturally.

Avoid:

violence
fear
dangerous behavior
romance
politics
religion
mature themes
sad or disturbing situations
complicated vocabulary

Do not use emojis.

Do not use markdown.

Return ONLY valid JSON.

============================================================
ANIMATION REQUIREMENTS
============================================================

The visual descriptions are going to be used by an animation
renderer.

Therefore, describe ACTIONS rather than static poses.

Good examples:

Bobo walks toward a basket.

Mimi hops beside Bobo.

Kiki flies around the tree.

Bobo reaches for a red ball.

Mimi points at three apples.

Kiki flaps his wings excitedly.

The characters move an object.

The characters react to something.

The characters celebrate after learning the lesson.

Avoid descriptions such as:

"Bobo is standing in the forest."

Instead write:

"Bobo walks through the sunny forest and notices three colorful
apples beside a tree."

Every scene should contain things that can actually be animated.

============================================================
CANONICAL CHARACTERS
============================================================

Bobo:

small friendly brown bear with soft fluffy brown fur,
round face, small rounded ears, large expressive brown eyes,
short arms and legs, and a bright yellow scarf.

Personality:
curious, playful, kind and slightly funny.


Mimi:

small friendly white rabbit with soft white fur,
long rounded ears with pink inner ears, large expressive eyes,
tiny pink nose, and a small purple backpack.

Personality:
clever, curious, patient and encouraging.


Kiki:

small cheerful yellow bird with bright yellow feathers,
bright blue wings, large expressive eyes, and a small orange beak.

Personality:
energetic, musical, cheerful and playful.

============================================================
CHARACTER CONSISTENCY
============================================================

These three characters are FIXED.

Never change:

their species
their colors
their clothing
their physical features
their personalities

Do not invent additional characters.

Only Bobo, Mimi and Kiki may appear.

============================================================
JSON REQUIREMENT
============================================================

Return ONLY valid JSON.

Do not wrap the JSON in markdown.

Do not use code fences.

Do not include comments.

Do not include duration_seconds.
"""

# ============================================================
# API KEY
# ============================================================

def get_api_key():

    key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not available."
        )

    return key


# ============================================================
# GENERATE STORY
# ============================================================

def create_story():

    client = genai.Client(
        api_key=get_api_key()
    )

    prompt = SYSTEM_PROMPT + """

Create a new preschool NobiNest episode.

Choose one simple educational concept.

Make the episode entertaining enough for a child to watch from
beginning to end.

The four scenes must connect naturally.

Return exactly this JSON structure:

{
  "title": "Episode title",

  "lesson": "One simple sentence describing the educational lesson",

  "characters": [
    "Bobo",
    "Mimi",
    "Kiki"
  ],

  "character_bible": {
    "Bobo": {
      "appearance": "exact canonical appearance",
      "personality": "exact canonical personality"
    },

    "Mimi": {
      "appearance": "exact canonical appearance",
      "personality": "exact canonical personality"
    },

    "Kiki": {
      "appearance": "exact canonical appearance",
      "personality": "exact canonical personality"
    }
  },

  "scenes": [
    {
      "scene_number": 1,
      "visual_description": "Action-focused description suitable for 2D animation",
      "narration": "Approximately 24 to 30 spoken words"
    },

    {
      "scene_number": 2,
      "visual_description": "Action-focused description suitable for 2D animation",
      "narration": "Approximately 24 to 30 spoken words"
    },

    {
      "scene_number": 3,
      "visual_description": "Action-focused description suitable for 2D animation",
      "narration": "Approximately 24 to 30 spoken words"
    },

    {
      "scene_number": 4,
      "visual_description": "Action-focused description suitable for 2D animation",
      "narration": "Approximately 24 to 30 spoken words"
    }
  ],

  "song": {
    "lyrics": "Approximately 15 to 20 spoken words with a simple educational rhythm"
  },

  "ending": "Approximately 5 to 8 spoken words"
}

IMPORTANT:

The total spoken word count should be approximately
135 to 155 words.

Do NOT exceed 165 words.

Do NOT go below 125 words.

Keep the narration natural for children's voice generation.

Do not invent another character.

Do not change the canonical character designs.

Do not include duration_seconds.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    text = response.text.strip()

    # Remove accidental markdown code fences
    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        text = text.strip()

    try:

        story = json.loads(
            text
        )

    except json.JSONDecodeError as error:

        print("Gemini returned invalid JSON.")
        print("Response:")
        print(text)

        raise RuntimeError(
            f"Could not parse Gemini response as JSON: {error}"
        )

    validate_story(
        story
    )

    return story


# ============================================================
# VALIDATE STORY
# ============================================================

def validate_story(story):

    required_fields = [
        "title",
        "lesson",
        "characters",
        "character_bible",
        "scenes",
        "song",
        "ending"
    ]

    for field in required_fields:

        if field not in story:

            raise ValueError(
                f"Story is missing required field: {field}"
            )


    # --------------------------------------------------------
    # CHARACTER LIST
    # --------------------------------------------------------

    expected_characters = [
        "Bobo",
        "Mimi",
        "Kiki"
    ]

    if story["characters"] != expected_characters:

        raise ValueError(
            "Story must use exactly Bobo, Mimi and Kiki."
        )


    # --------------------------------------------------------
    # SCENES
    # --------------------------------------------------------

    if len(story["scenes"]) != 4:

        raise ValueError(
            "Story must contain exactly 4 scenes."
        )


    expected_scene_numbers = [
        1,
        2,
        3,
        4
    ]

    actual_scene_numbers = [
        scene.get("scene_number")
        for scene in story["scenes"]
    ]

    if actual_scene_numbers != expected_scene_numbers:

        raise ValueError(
            "Scenes must be numbered 1, 2, 3 and 4."
        )


    # --------------------------------------------------------
    # CHARACTER BIBLE
    # --------------------------------------------------------

    for character in expected_characters:

        if character not in story["character_bible"]:

            raise ValueError(
                f"Missing character bible entry: {character}"
            )


  # --------------------------------------------------------
    # SCENE CONTENT
    # --------------------------------------------------------

    total_words = 0

    for scene in story["scenes"]:

        if not scene.get("visual_description"):

            raise ValueError(
                "Scene is missing visual_description."
            )

        if not scene.get("narration"):

            raise ValueError(
                "Scene is missing narration."
            )

        narration_words = len(
            scene["narration"].split()
        )

        print(
            f"Scene {scene['scene_number']} words: "
            f"{narration_words}"
        )

        total_words += narration_words


    # --------------------------------------------------------
    # SONG
    # --------------------------------------------------------

    if not story["song"].get("lyrics"):

        raise ValueError(
            "Story is missing song lyrics."
        )

    song_words = len(
        story["song"]["lyrics"].split()
    )

    print(
        f"Song words: {song_words}"
    )

    total_words += song_words


    # --------------------------------------------------------
    # ENDING
    # --------------------------------------------------------

    if not story.get("ending"):

        raise ValueError(
            "Story is missing ending."
        )

    ending_words = len(
        story["ending"].split()
    )

    print(
        f"Ending words: {ending_words}"
    )

    total_words += ending_words


    # --------------------------------------------------------
    # TOTAL WORD COUNT
    # --------------------------------------------------------

    print(
        f"Total spoken words: {total_words}"
    )


    if total_words < 125:

        raise ValueError(
            f"Story has only {total_words} spoken words. "
            "Target is approximately 135-155 words."
        )


    if total_words > 165:

        raise ValueError(
            f"Story has {total_words} spoken words. "
            "Target is approximately 135-155 words."
        )


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
        encoding="utf-8"
    ) as file:

        json.dump(
            story,
            file,
            indent=2,
            ensure_ascii=False
        )


    # --------------------------------------------------------
    # TEXT VERSION
    # --------------------------------------------------------

    parts = [
        story["title"],
        "",
        f"Lesson: {story['lesson']}",
        ""
    ]


    for scene in story["scenes"]:

        parts.append(
            f"Scene {scene['scene_number']}"
        )

        parts.append(
            scene["narration"]
        )

        parts.append("")


    parts.append(
        "Song"
    )

    parts.append(
        story["song"]["lyrics"]
    )

    parts.append("")

    parts.append(
        "Ending"
    )

    parts.append(
        story["ending"]
    )


    with open(
        STORY_TXT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(parts)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "======================================"
    )

    print(
        "NOBINEST STORY GENERATOR"
    )

    print(
        "TARGET: 60-90 SECOND EPISODES"
    )

    print(
        "IDEAL: 70-80 SECONDS"
    )

    print(
        "======================================"
    )

    story = create_story()

    save_story(
        story
    )

    print(
        "Story generated successfully."
    )

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
        "Target duration: 60-90 seconds"
    )

    print(
        "Target spoken words: 135-155"
    )

    print(
        "Saved to output/story.json"
    )

    print(
        "Saved to output/story.txt"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
