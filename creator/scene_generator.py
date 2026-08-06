import json
import os


# =========================================================
# NOBINEST SCENE GENERATOR
# =========================================================

OUTPUT_DIR = "output"
STORY_FILE = os.path.join(OUTPUT_DIR, "story.json")
SCENE_FILE = os.path.join(OUTPUT_DIR, "scenes.json")


VISUAL_STYLE = """
Original NobiNest children's animation style.

Bright, friendly 2D cartoon appearance.
Soft rounded shapes.
Large expressive eyes.
Simple clean backgrounds.
Warm cheerful lighting.
Safe and wholesome preschool environment.
Strong visual contrast.
No frightening elements.
No realistic humans.
No text inside the artwork unless specifically requested.

The characters must remain visually consistent from scene to scene.
"""


CHARACTER_DESIGNS = {
    "Bobo": {
        "species": "little bear",
        "appearance": (
            "small friendly bear, round face, soft brown fur, "
            "large expressive eyes, small rounded ears, "
            "cheerful childlike expression"
        ),
        "personality": "curious, playful and kind"
    },

    "Mimi": {
        "species": "little rabbit",
        "appearance": (
            "small friendly rabbit, soft cream fur, "
            "long rounded ears, large expressive eyes, "
            "tiny pink nose, cheerful childlike expression"
        ),
        "personality": "clever, curious and thoughtful"
    },

    "Kiki": {
        "species": "little bird",
        "appearance": (
            "small cheerful bird, bright yellow feathers, "
            "round body, tiny wings, large expressive eyes, "
            "small orange beak"
        ),
        "personality": "musical, energetic and cheerful"
    }
}


def load_story():
    if not os.path.exists(STORY_FILE):
        raise FileNotFoundError(
            f"{STORY_FILE} was not found."
        )

    with open(
        STORY_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def character_description(character_names):
    descriptions = []

    for name in character_names:
        if name in CHARACTER_DESIGNS:
            character = CHARACTER_DESIGNS[name]

            descriptions.append(
                f"{name}: {character['appearance']}. "
                f"Personality: {character['personality']}."
            )

    return " ".join(descriptions)


def build_scene_prompt(scene, story):

    characters = story.get(
        "characters",
        ["Bobo"]
    )

    characters_text = character_description(
        characters
    )

    prompt = f"""
Create one original children's animation scene
for the NobiNest universe.

EPISODE:
{story["title"]}

EDUCATIONAL LESSON:
{story["lesson"]}

SCENE:
{scene["scene_number"]}

SCENE DESCRIPTION:
{scene["visual_description"]}

CHARACTERS:
{characters_text}

VISUAL STYLE:
{VISUAL_STYLE}

IMPORTANT:
Keep the same character appearance throughout
the entire episode.

Do not introduce random characters.

Do not use copyrighted characters.

Do not imitate an existing cartoon.

Make the composition clear enough for preschool
children to immediately understand what is happening.

Use a 16:9 landscape composition suitable for
YouTube video.

Do not place written words, captions or logos
inside the artwork.
"""

    return " ".join(prompt.split())


def generate_scene_manifest(story):

    scenes = []

    for scene in story.get("scenes", []):

        scene_data = {
            "scene_number": scene["scene_number"],
            "duration_seconds": scene["duration_seconds"],
            "narration": scene["narration"],
            "visual_description": scene["visual_description"],
            "image_prompt": build_scene_prompt(
                scene,
                story
            )
        }

        scenes.append(scene_data)

    return scenes


def save_scenes(scenes):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    with open(
        SCENE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            scenes,
            file,
            indent=2,
            ensure_ascii=False
        )


def main():

    print("======================================")
    print("NOBINEST SCENE GENERATOR")
    print("======================================")

    story = load_story()

    scenes = generate_scene_manifest(
        story
    )

    save_scenes(
        scenes
    )

    print()
    print(
        f"Created {len(scenes)} scene prompts."
    )

    print(
        f"Saved to {SCENE_FILE}"
    )


if __name__ == "__main__":
    main()
