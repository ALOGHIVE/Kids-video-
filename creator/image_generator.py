import json
import math
import os
import re

from PIL import Image, ImageDraw


OUTPUT_DIR = "output"
SCENE_FILE = os.path.join(OUTPUT_DIR, "scenes.json")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

WIDTH = 1280
HEIGHT = 720


def load_scenes():
    with open(
        SCENE_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def clean_text(text):
    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip().lower()


def contains(text, *words):
    text = clean_text(text)

    return any(
        word.lower() in text
        for word in words
    )


def create_canvas(scene_text):
    text = clean_text(scene_text)

    if contains(
        text,
        "night",
        "moon",
        "star",
        "evening"
    ):
        sky = (35, 48, 90)
        ground = (52, 91, 61)

    elif contains(
        text,
        "beach",
        "sea",
        "ocean"
    ):
        sky = (145, 210, 245)
        ground = (235, 210, 145)

    elif contains(
        text,
        "garden",
        "flower",
        "flowers"
    ):
        sky = (155, 220, 250)
        ground = (105, 175, 85)

    elif contains(
        text,
        "forest",
        "woods",
        "tree"
    ):
        sky = (150, 215, 245)
        ground = (82, 145, 72)

    elif contains(
        text,
        "school",
        "classroom"
    ):
        sky = (190, 220, 245)
        ground = (205, 185, 155)

    else:
        sky = (160, 220, 250)
        ground = (110, 175, 90)

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        sky
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (
            0,
            HEIGHT * 0.62,
            WIDTH,
            HEIGHT
        ),
        fill=ground
    )

    draw_sun(draw, text)

    if contains(
        text,
        "forest",
        "woods",
        "tree",
        "garden"
    ):
        draw_trees(draw)

    if contains(
        text,
        "beach",
        "sea",
        "ocean"
    ):
        draw_water(draw)

    if contains(
        text,
        "night",
        "moon",
        "star"
    ):
        draw_moon(draw)

    return image


def draw_sun(draw, text):

    if contains(
        text,
        "night",
        "moon",
        "evening"
    ):
        return

    x = 1080
    y = 110
    r = 55

    draw.ellipse(
        (
            x - r,
            y - r,
            x + r,
            y + r
        ),
        fill=(255, 220, 80)
    )


def draw_moon(draw):

    draw.ellipse(
        (
            1040,
            70,
            1140,
            170
        ),
        fill=(245, 245, 205)
    )

    draw.ellipse(
        (
            1070,
            55,
            1170,
            155
        ),
        fill=(35, 48, 90)
    )


def draw_trees(draw):

    positions = [
        100,
        260,
        1050,
        1180
    ]

    for x in positions:

        draw.rectangle(
            (
                x - 15,
                350,
                x + 15,
                520
            ),
            fill=(120, 75, 40)
        )

        draw.ellipse(
            (
                x - 75,
                250,
                x + 75,
                400
            ),
            fill=(65, 145, 70)
        )

        draw.ellipse(
            (
                x - 55,
                210,
                x + 80,
                350
            ),
            fill=(75, 160, 75)
        )


def draw_water(draw):

    draw.rectangle(
        (
            0,
            450,
            WIDTH,
            720
        ),
        fill=(85, 175, 220)
    )

    for y in range(
        480,
        700,
        55
    ):

        for x in range(
            30,
            WIDTH,
            180
        ):

            draw.arc(
                (
                    x,
                    y,
                    x + 90,
                    y + 25
                ),
                0,
                180,
                fill=(220, 245, 255),
                width=4
            )


def draw_cloud(draw, x, y):

    draw.ellipse(
        (
            x,
            y + 20,
            x + 90,
            y + 70
        ),
        fill=(250, 250, 250)
    )

    draw.ellipse(
        (
            x + 35,
            y,
            x + 115,
            y + 70
        ),
        fill=(250, 250, 250)
    )

    draw.ellipse(
        (
            x + 75,
            y + 20,
            x + 165,
            y + 70
        ),
        fill=(250, 250, 250)
    )


def draw_bobo(draw, x, y, scale=1.0):

    s = scale

    # Body

    draw.ellipse(
        (
            x - 65*s,
            y + 40*s,
            x + 65*s,
            y + 190*s
        ),
        fill=(150, 95, 55),
        outline=(80, 50, 35),
        width=max(1, int(4*s))
    )

    # Head

    draw.ellipse(
        (
            x - 75*s,
            y - 70*s,
            x + 75*s,
            y + 70*s
        ),
        fill=(165, 105, 60),
        outline=(80, 50, 35),
        width=max(1, int(4*s))
    )

    # Ears

    draw.ellipse(
        (
            x - 70*s,
            y - 90*s,
            x - 20*s,
            y - 40*s
        ),
        fill=(145, 90, 55)
    )

    draw.ellipse(
        (
            x + 20*s,
            y - 90*s,
            x + 70*s,
            y - 40*s
        ),
        fill=(145, 90, 55)
    )

    # Eyes

    draw.ellipse(
        (
            x - 38*s,
            y - 25*s,
            x - 18*s,
            y - 5*s
        ),
        fill=(30, 25, 20)
    )

    draw.ellipse(
        (
            x + 18*s,
            y - 25*s,
            x + 38*s,
            y - 5*s
        ),
        fill=(30, 25, 20)
    )

    # Nose

    draw.ellipse(
        (
            x - 12*s,
            y + 5*s,
            x + 12*s,
            y + 22*s
        ),
        fill=(50, 35, 30)
    )

    # Yellow scarf

    draw.rectangle(
        (
            x - 70*s,
            y + 55*s,
            x + 70*s,
            y + 80*s
        ),
        fill=(245, 205, 45)
    )

    draw.rectangle(
        (
            x + 40*s,
            y + 70*s,
            x + 70*s,
            y + 130*s
        ),
        fill=(245, 205, 45)
    )


def draw_mimi(draw, x, y, scale=1.0):

    s = scale

    # Body

    draw.ellipse(
        (
            x - 55*s,
            y + 45*s,
            x + 55*s,
            y + 180*s
        ),
        fill=(245, 245, 245),
        outline=(160, 160, 160),
        width=max(1, int(3*s))
    )

    # Head

    draw.ellipse(
        (
            x - 65*s,
            y - 60*s,
            x + 65*s,
            y + 65*s
        ),
        fill=(250, 250, 250),
        outline=(160, 160, 160),
        width=max(1, int(3*s))
    )

    # Ears

    draw.ellipse(
        (
            x - 65*s,
            y - 180*s,
            x - 15*s,
            y - 30*s
        ),
        fill=(250, 250, 250),
        outline=(160, 160, 160),
        width=max(1, int(3*s))
    )

    draw.ellipse(
        (
            x + 15*s,
            y - 180*s,
            x + 65*s,
            y - 30*s
        ),
        fill=(250, 250, 250),
        outline=(160, 160, 160),
        width=max(1, int(3*s))
    )

    # Inner ears

    draw.ellipse(
        (
            x - 50*s,
            y - 160*s,
            x - 25*s,
            y - 50*s
        ),
        fill=(245, 175, 190)
    )

    draw.ellipse(
        (
            x + 25*s,
            y - 160*s,
            x + 50*s,
            y - 50*s
        ),
        fill=(245, 175, 190)
    )

    # Eyes

    draw.ellipse(
        (
            x - 32*s,
            y - 20*s,
            x - 12*s,
            y
        ),
        fill=(35, 30, 30)
    )

    draw.ellipse(
        (
            x + 12*s,
            y - 20*s,
            x + 32*s,
            y
        ),
        fill=(35, 30, 30)
    )

    # Nose

    draw.ellipse(
        (
            x - 9*s,
            y + 5*s,
            x + 9*s,
            y + 20*s
        ),
        fill=(240, 145, 170)
    )

    # Purple backpack

    draw.ellipse(
        (
            x - 70*s,
            y + 70*s,
            x - 35*s,
            y + 135*s
        ),
        fill=(150, 100, 210)
    )


def draw_kiki(draw, x, y, scale=1.0):

    s = scale

    # Body

    draw.ellipse(
        (
            x - 50*s,
            y,
            x + 50*s,
            y + 120*s
        ),
        fill=(250, 220, 45),
        outline=(150, 120, 20),
        width=max(1, int(3*s))
    )

    # Head

    draw.ellipse(
        (
            x - 55*s,
            y - 65*s,
            x + 55*s,
            y + 35*s
        ),
        fill=(255, 225, 50),
        outline=(150, 120, 20),
        width=max(1, int(3*s))
    )

    # Blue wings

    draw.ellipse(
        (
            x - 75*s,
            y + 25*s,
            x - 25*s,
            y + 95*s
        ),
        fill=(65, 145, 225)
    )

    draw.ellipse(
        (
            x + 25*s,
            y + 25*s,
            x + 75*s,
            y + 95*s
        ),
        fill=(65, 145, 225)
    )

    # Eyes

    draw.ellipse(
        (
            x - 30*s,
            y - 35*s,
            x - 10*s,
            y - 15*s
        ),
        fill=(30, 30, 30)
    )

    draw.ellipse(
        (
            x + 10*s,
            y - 35*s,
            x + 30*s,
            y - 15*s
        ),
        fill=(30, 30, 30)
    )

    # Beak

    draw.polygon(
        [
            (
                x - 10*s,
                y - 5*s
            ),
            (
                x + 10*s,
                y - 5*s
            ),
            (
                x,
                y + 18*s
            )
        ],
        fill=(240, 140, 35)
    )


def draw_characters(
    draw,
    scene_text
):

    text = clean_text(scene_text)

    characters = []

    if "bobo" in text:
        characters.append("bobo")

    if "mimi" in text:
        characters.append("mimi")

    if "kiki" in text:
        characters.append("kiki")

    if not characters:
        characters = [
            "bobo",
            "mimi",
            "kiki"
        ]

    positions = {
        1: (WIDTH * 0.30, HEIGHT * 0.43),
        2: (WIDTH * 0.50, HEIGHT * 0.43),
        3: (WIDTH * 0.70, HEIGHT * 0.43)
    }

    for index, character in enumerate(
        characters[:3],
        start=1
    ):

        x, y = positions[index]

        if character == "bobo":
            draw_bobo(
                draw,
                x,
                y,
                1.0
            )

        elif character == "mimi":
            draw_mimi(
                draw,
                x,
                y,
                0.85
            )

        elif character == "kiki":
            draw_kiki(
                draw,
                x,
                y,
                1.0
            )


def add_simple_environment(
    draw,
    scene_text
):

    text = clean_text(scene_text)

    draw_cloud(
        draw,
        180,
        90
    )

    draw_cloud(
        draw,
        700,
        130
    )

    if contains(
        text,
        "flower",
        "flowers",
        "garden"
    ):

        for x in range(
            100,
            1200,
            180
        ):

            draw.line(
                (
                    x,
                    600,
                    x,
                    550
                ),
                fill=(45, 120, 50),
                width=6
            )

            draw.ellipse(
                (
                    x - 12,
                    535,
                    x + 12,
                    559
                ),
                fill=(245, 100, 150)
            )

    if contains(
        text,
        "ball"
    ):

        draw.ellipse(
            (
                900,
                520,
                980,
                600
            ),
            fill=(235, 90, 80),
            outline=(120, 50, 50),
            width=4
        )


def create_scene_image(
    scene
):

    description = scene.get(
        "visual_description",
        ""
    )

    prompt = scene.get(
        "image_prompt",
        ""
    )

    combined_text = (
        description
        + " "
        + prompt
    )

    image = create_canvas(
        combined_text
    )

    draw = ImageDraw.Draw(
        image
    )

    add_simple_environment(
        draw,
        combined_text
    )

    draw_characters(
        draw,
        combined_text
    )

    return image


def main():

    print("======================================")
    print("NOBINEST FREE IMAGE GENERATOR")
    print("======================================")

    os.makedirs(
        IMAGE_DIR,
        exist_ok=True
    )

    scenes = load_scenes()

    for scene in scenes:

        number = scene[
            "scene_number"
        ]

        filename = (
            f"scene_{number:02d}.png"
        )

        path = os.path.join(
            IMAGE_DIR,
            filename
        )

        print(
            f"Creating scene {number}..."
        )

        image = create_scene_image(
            scene
        )

        image.save(
            path,
            "PNG",
            optimize=True
        )

        print(
            f"Saved {path}"
        )

    print()
    print("IMAGE GENERATION COMPLETE")
    print(
        f"Created {len(scenes)} images."
    )


if __name__ == "__main__":
    main()
