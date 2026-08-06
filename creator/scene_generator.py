import json
import os


OUTPUT_DIR = "output"

STORY_FILE = os.path.join(
    OUTPUT_DIR,
    "story.json"
)

SCENE_FILE = os.path.join(
    OUTPUT_DIR,
    "scenes.json"
)


VISUAL_STYLE = """
Original NobiNest preschool animation.

Bright, warm, friendly 2D cartoon illustration.
Soft rounded shapes.
Clean simple backgrounds.
Gentle cheerful lighting.
Large expressive eyes.
Child-friendly proportions.
Wholesome preschool atmosphere.
Clear visual storytelling.
High visual clarity.
No frightening imagery.
No realistic humans.
No copyrighted characters.
No imitation of existing cartoon franchises.
No written text inside the artwork.
No logos.
16:9 landscape composition.
"""


def load_story():

    with open(
        STORY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def build_character_bible(
    story
):

    bible = []

    characters = story[
        "character_bible"
    ]

    for name, data in characters.items():

        bible.append(
            f"""
{name}:
{data['appearance']}
Personality:
{data['personality']}
""".strip()
        )

    return "\n\n".join(
        bible
    )


def build_prompt(
    story,
    scene
):

    character_bible = (
        build_character_bible(
            story
        )
    )

    return f"""
Create one original NobiNest preschool
animation scene.

EPISODE:
{story['title']}

EDUCATIONAL LESSON:
{story['lesson']}

SCENE NUMBER:
{scene['scene_number']}

SCENE DESCRIPTION:
{scene['visual_description']}

CANONICAL CHARACTER BIBLE:

{character_bible}

VISUAL STYLE:

{VISUAL_STYLE}

STRICT CONSISTENCY RULES:

Use the character descriptions exactly.

Do not change character species.

Do not change fur or feather colors.

Do not change clothing.

Do not change important physical features.

Do not invent additional main characters.

Keep the characters visually consistent
with every other scene in this episode.

The image must clearly communicate
the action described in the scene.

Make the composition suitable for
children aged approximately 3 to 7.

Do not include captions.

Do not include subtitles.

Do not include written words.

Do not include watermarks.

Do not include logos.

Do not imitate an existing cartoon.

Create an original NobiNest visual.

Use a 16:9 landscape composition.
""".strip()


def generate_scene_manifest(
    story
):

    scenes = []

    for scene in story["scenes"]:

        scenes.append({
            "scene_number": scene[
                "scene_number"
            ],

            "narration": scene[
                "narration"
            ],

            "visual_description": scene[
                "visual_description"
            ],

            "image_prompt": build_prompt(
                story,
                scene
            )
        })

    return scenes


def save_manifest(
    scenes
):

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

    save_manifest(
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
