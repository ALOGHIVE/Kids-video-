import json
import os
from google import genai


OUTPUT_DIR = "output"

STORY_JSON = os.path.join(
    OUTPUT_DIR,
    "story.json"
)

STORY_TXT = os.path.join(
    OUTPUT_DIR,
    "story.txt"
)


# =========================================================
# MODEL CONFIGURATION
# =========================================================

MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


# =========================================================
# CANONICAL CHARACTERS
# =========================================================

CHARACTERS = {
    "Bobo": {
        "name": "Bobo",
        "species": "little bear",
        "appearance": (
            "small friendly brown bear with soft fluffy brown fur, "
            "round face, small rounded ears, large expressive brown eyes, "
            "short arms and legs, and a bright yellow scarf"
        ),
        "personality": (
            "curious, playful, kind and slightly funny"
        )
    },

    "Mimi": {
        "name": "Mimi",
        "species": "little rabbit",
        "appearance": (
            "small friendly white rabbit with soft white fur, "
            "long rounded ears with pink inner ears, large expressive eyes, "
            "tiny pink nose, and a small purple backpack"
        ),
        "personality": (
            "clever, curious, patient and encouraging"
        )
    },

    "Kiki": {
        "name": "Kiki",
        "species": "little bird",
        "appearance": (
            "small cheerful yellow bird with bright yellow feathers, "
            "bright blue wings, large expressive eyes, "
            "and a small orange beak"
        ),
        "personality": (
            "energetic, musical, cheerful and playful"
        )
    }
}


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are the head writer for NobiNest.

NobiNest is an original preschool children's
educational entertainment universe.

TARGET AUDIENCE:
Children approximately 3 to 7 years old.

Create one short, safe, educational episode.

The episode must:

1. Teach ONE simple educational concept.

2. Use very simple spoken English.

3. Have a clear beginning, middle and ending.

4. Be warm, playful and positive.

5. Avoid violence.

6. Avoid frightening situations.

7. Avoid dangerous behavior.

8. Avoid romance.

9. Avoid politics.

10. Avoid religion.

11. Avoid mature themes.

12. Use ONLY the canonical NobiNest characters.

13. NEVER change their species.

14. NEVER change their colors.

15. NEVER change their clothing.

16. NEVER change their important physical features.

17. Create exactly FOUR scenes.

18. Each scene should contain approximately
30 to 60 spoken words.

19. The total spoken story should be suitable
for a short children's video.

20. Include a short educational song.

21. Include a short friendly ending.

22. Do not use emojis.

23. Do not use Markdown.

24. Return ONLY valid JSON.

CANONICAL CHARACTERS:

BOBO:

Small friendly brown bear with soft fluffy brown fur,
round face, small rounded ears, large expressive brown eyes,
short arms and legs, and a bright yellow scarf.

Personality:
Curious, playful, kind and slightly funny.

MIMI:

Small friendly white rabbit with soft white fur,
long rounded ears with pink inner ears, large expressive eyes,
tiny pink nose, and a small purple backpack.

Personality:
Clever, curious, patient and encouraging.

KIKI:

Small cheerful yellow bird with bright yellow feathers,
bright blue wings, large expressive eyes, and a small orange beak.

Personality:
Energetic, musical, cheerful and playful.
"""


# =========================================================
# API KEY
# =========================================================

def get_api_key():

    key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not key:

        raise RuntimeError(
            "GEMINI_API_KEY is not available. "
            "Check your GitHub repository secret."
        )

    return key


# =========================================================
# GEMINI CLIENT
# =========================================================

def create_client():

    return genai.Client(
        api_key=get_api_key()
    )


# =========================================================
# STORY GENERATION
# =========================================================

def create_story():

    client = create_client()

    prompt = SYSTEM_PROMPT + """

Create a completely new NobiNest episode.

Choose ONE simple preschool lesson.

Good examples include:

colors
shapes
counting
big and small
hot and cold
up and down
inside and outside
sharing
kindness
friendship
animals
fruits
weather
cleaning up
simple emotions
basic nature
good manners

The lesson should be demonstrated naturally
through the story.

Return EXACTLY this JSON structure:

{
  "title": "Episode title",

  "lesson": "One simple sentence describing what children learn",

  "characters": [
    "Bobo",
    "Mimi",
    "Kiki"
  ],

  "character_bible": {

    "Bobo": {
      "appearance": "Exact canonical Bobo appearance",
      "personality": "Exact canonical Bobo personality"
    },

    "Mimi": {
      "appearance": "Exact canonical Mimi appearance",
      "personality": "Exact canonical Mimi personality"
    },

    "Kiki": {
      "appearance": "Exact canonical Kiki appearance",
      "personality": "Exact canonical Kiki personality"
    }

  },

  "scenes": [

    {
      "scene_number": 1,

      "visual_description":
      "Detailed description of what the viewer sees.",

      "image_prompt":
      "Detailed visual prompt for creating this scene.",

      "narration":
      "Spoken narration for the scene."
    },

    {
      "scene_number": 2,

      "visual_description":
      "Detailed description of what the viewer sees.",

      "image_prompt":
      "Detailed visual prompt for creating this scene.",

      "narration":
      "Spoken narration for the scene."
    },

    {
      "scene_number": 3,

      "visual_description":
      "Detailed description of what the viewer sees.",

      "image_prompt":
      "Detailed visual prompt for creating this scene.",

      "narration":
      "Spoken narration for the scene."
    },

    {
      "scene_number": 4,

      "visual_description":
      "Detailed description of what the viewer sees.",

      "image_prompt":
      "Detailed visual prompt for creating this scene.",

      "narration":
      "Spoken narration for the scene."
    }

  ],

  "song": {

    "lyrics":
    "Short simple educational song."
  },

  "ending":
  "Short friendly educational closing message."
}

IMAGE PROMPT RULES:

Every image_prompt must describe the canonical
characters accurately.

Always repeat the relevant character appearance
inside the image prompt.

Use bright, friendly, colorful 2D children's
storybook artwork.

Use a clean composition.

Use expressive faces.

Use simple backgrounds.

Keep the characters visually consistent.

Do not introduce new named characters.

Do not include text inside the image.

Do not include logos.

Do not include watermarks.

Do not make the scene frightening.

Do not make the scene realistic.

The images should look like frames from the
same children's animated story.

IMPORTANT:

Do not add fields that are not specified.

Do not add duration_seconds.

Do not add Markdown.

Return ONLY valid JSON.
"""

    print(
        f"Using Gemini model: {MODEL}"
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    text = response.text.strip()

    # Remove accidental Markdown fences.
    if text.startswith(
        "```json"
    ):

        text = text[
            7:
        ].strip()

    elif text.startswith(
        "```"
    ):

        text = text[
            3:
        ].strip()

    if text.endswith(
        "```"
    ):

        text = text[
            :-3
        ].strip()

    try:

        story = json.loads(
            text
        )

    except json.JSONDecodeError as error:

        print()
        print(
            "Gemini returned invalid JSON:"
        )
        print(text)

        raise RuntimeError(
            "Gemini did not return valid JSON."
        ) from error

    validate_story(
        story
    )

    return story


# =========================================================
# VALIDATION
# =========================================================

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

    # -----------------------------------------------------
    # Characters
    # -----------------------------------------------------

    expected_characters = [
        "Bobo",
        "Mimi",
        "Kiki"
    ]

    if story[
        "characters"
    ] != expected_characters:

        raise ValueError(
            "The story must use exactly "
            "Bobo, Mimi and Kiki."
        )

    # -----------------------------------------------------
    # Character bible
    # -----------------------------------------------------

    for character in CHARACTERS:

        if character not in story[
            "character_bible"
        ]:

            raise ValueError(
                f"Missing character bible entry: {character}"
            )

    # -----------------------------------------------------
    # Scenes
    # -----------------------------------------------------

    scenes = story[
        "scenes"
    ]

    if not isinstance(
        scenes,
        list
    ):

        raise ValueError(
            "scenes must be a list."
        )

    if len(
        scenes
    ) != 4:

        raise ValueError(
            "Story must contain exactly 4 scenes."
        )

    for expected_number, scene in enumerate(
        scenes,
        start=1
    ):

        if scene.get(
            "scene_number"
        ) != expected_number:

            raise ValueError(
                f"Expected scene number {expected_number}."
            )

        if not scene.get(
            "visual_description"
        ):

            raise ValueError(
                f"Scene {expected_number} "
                "has no visual_description."
            )

        if not scene.get(
            "image_prompt"
        ):

            raise ValueError(
                f"Scene {expected_number} "
                "has no image_prompt."
            )

        if not scene.get(
            "narration"
        ):

            raise ValueError(
                f"Scene {expected_number} "
                "has no narration."
            )

    # -----------------------------------------------------
    # Song
    # -----------------------------------------------------

    if not isinstance(
        story["song"],
        dict
    ):

        raise ValueError(
            "song must be an object."
        )

    if not story["song"].get(
        "lyrics"
    ):

        raise ValueError(
            "Song lyrics are missing."
        )

    # -----------------------------------------------------
    # Ending
    # -----------------------------------------------------

    if not story.get(
        "ending"
    ):

        raise ValueError(
            "Story ending is missing."
        )


# =========================================================
# SAVE STORY
# =========================================================

def save_story(story):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # Save JSON.

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

    # -----------------------------------------------------
    # Create readable TXT
    # -----------------------------------------------------

    text_parts = [
        story["title"],
        "",
        f"Lesson: {story['lesson']}",
        "",
    ]

    for scene in story[
        "scenes"
    ]:

        text_parts.append(
            f"Scene {scene['scene_number']}"
        )

        text_parts.append(
            scene["narration"]
        )

        text_parts.append("")

    text_parts.append(
        "Song"
    )

    text_parts.append(
        story["song"]["lyrics"]
    )

    text_parts.append("")

    text_parts.append(
        "Ending"
    )

    text_parts.append(
        story["ending"]
    )

    with open(
        STORY_TXT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(
                text_parts
            )
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "======================================"
    )

    print(
        "NOBINEST STORY GENERATOR"
    )

    print(
        "======================================"
    )

    print(
        f"Model: {MODEL}"
    )

    print()

    story = create_story()

    save_story(
        story
    )

    print()

    print(
        "STORY GENERATED SUCCESSFULLY"
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
        "Image prompts: 4"
    )

    print(
        "Saved: output/story.json"
    )

    print(
        "Saved: output/story.txt"
    )


if __name__ == "__main__":

    main()
