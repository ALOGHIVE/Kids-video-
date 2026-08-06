import json
import os
from google import genai


OUTPUT_DIR = "output"
STORY_JSON = os.path.join(OUTPUT_DIR, "story.json")
STORY_TXT = os.path.join(OUTPUT_DIR, "story.txt")


MODEL = "gemini-3.6-flash"


CHARACTERS = {
    "Bobo": {
        "name": "Bobo",
        "species": "little bear",
        "appearance": (
            "small friendly brown bear with soft fluffy brown fur, "
            "round face, small rounded ears, large expressive brown eyes, "
            "short arms and legs, and a bright yellow scarf"
        ),
        "personality": "curious, playful, kind and slightly funny"
    },

    "Mimi": {
        "name": "Mimi",
        "species": "little rabbit",
        "appearance": (
            "small friendly white rabbit with soft white fur, "
            "long rounded ears with pink inner ears, large expressive eyes, "
            "tiny pink nose, and a small purple backpack"
        ),
        "personality": "clever, curious, patient and encouraging"
    },

    "Kiki": {
        "name": "Kiki",
        "species": "little bird",
        "appearance": (
            "small cheerful yellow bird with bright yellow feathers, "
            "bright blue wings, large expressive eyes, and a small orange beak"
        ),
        "personality": "energetic, musical, cheerful and playful"
    }
}


SYSTEM_PROMPT = """
You are the head writer for NobiNest, an original preschool
children's educational story universe.

The target audience is children approximately 3 to 7 years old.

Create a short, safe, educational children's episode.

The episode must:
1. Teach one simple educational concept.
2. Use simple spoken English.
3. Have a clear beginning, middle and ending.
4. Be warm, positive and age appropriate.
5. Avoid violence, frightening situations, dangerous behavior,
   romance, politics, religion and mature themes.
6. Use only the NobiNest characters provided below.
7. Keep character appearances EXACTLY consistent.
8. Create 4 visual scenes.
9. Each scene should contain approximately 30 to 60 spoken words.
10. The total narration should be approximately 100 to 150 seconds
    when spoken naturally.
11. Include a short educational song of approximately 15 to 25 seconds.
12. Include a short closing message.
13. Do not include emojis.
14. Do not include markdown.
15. Return ONLY valid JSON.

IMPORTANT:
The characters below are fixed canonical characters.
Do not change their species, colors, clothing or physical features.

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
"""


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not available."
        )

    return key


def create_story():
    client = genai.Client(
        api_key=get_api_key()
    )

    prompt = SYSTEM_PROMPT + """

Create an episode about a simple preschool lesson.

Return exactly this JSON structure:

{
  "title": "Episode title",
  "lesson": "One sentence describing the lesson",
  "characters": ["Bobo", "Mimi", "Kiki"],

  "character_bible": {
    "Bobo": {
      "appearance": "exact canonical appearance",
      "personality": "personality"
    },
    "Mimi": {
      "appearance": "exact canonical appearance",
      "personality": "personality"
    },
    "Kiki": {
      "appearance": "exact canonical appearance",
      "personality": "personality"
    }
  },

  "scenes": [
    {
      "scene_number": 1,
      "visual_description": "Detailed visual description",
      "narration": "Spoken narration"
    },
    {
      "scene_number": 2,
      "visual_description": "Detailed visual description",
      "narration": "Spoken narration"
    },
    {
      "scene_number": 3,
      "visual_description": "Detailed visual description",
      "narration": "Spoken narration"
    },
    {
      "scene_number": 4,
      "visual_description": "Detailed visual description",
      "narration": "Spoken narration"
    }
  ],

  "song": {
    "lyrics": "Short educational song lyrics"
  },

  "ending": "Short friendly educational closing message"
}

Do not invent another character.
Do not change the canonical character designs.
Do not include duration_seconds.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    story = json.loads(text)

    validate_story(story)

    return story


def validate_story(story):

    required = [
        "title",
        "lesson",
        "characters",
        "character_bible",
        "scenes",
        "song",
        "ending"
    ]

    for key in required:
        if key not in story:
            raise ValueError(
                f"Story is missing required field: {key}"
            )

    if len(story["scenes"]) != 4:
        raise ValueError(
            "Story must contain exactly 4 scenes."
        )

    for character in CHARACTERS:

        if character not in story["character_bible"]:
            raise ValueError(
                f"Missing character bible entry: {character}"
            )

    for scene in story["scenes"]:

        if "scene_number" not in scene:
            raise ValueError(
                "Scene is missing scene_number."
            )

        if "visual_description" not in scene:
            raise ValueError(
                "Scene is missing visual_description."
            )

        if "narration" not in scene:
            raise ValueError(
                "Scene is missing narration."
            )


def save_story(story):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

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

    text_parts = [
        story["title"],
        "",
        f"Lesson: {story['lesson']}",
        ""
    ]

    for scene in story["scenes"]:

        text_parts.append(
            f"Scene {scene['scene_number']}"
        )

        text_parts.append(
            scene["narration"]
        )

        text_parts.append("")

    text_parts.append("Song")
    text_parts.append(
        story["song"]["lyrics"]
    )

    text_parts.append("")
    text_parts.append("Ending")
    text_parts.append(
        story["ending"]
    )

    with open(
        STORY_TXT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(text_parts)
        )


def main():

    print("======================================")
    print("NOBINEST STORY GENERATOR")
    print("======================================")

    story = create_story()

    save_story(story)

    print("Story generated successfully.")
    print(f"Title: {story['title']}")
    print(f"Lesson: {story['lesson']}")
    print("Scenes: 4")
    print("Saved to output/story.json")
    print("Saved to output/story.txt")


if __name__ == "__main__":
    main()
