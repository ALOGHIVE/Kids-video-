import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NOBINEST KIDS
# SCENE-AWARE 2D MOTION VIDEO RENDERER
# ============================================================
#
# INPUT:
#   output/story.json
#   output/narration.mp3
#
# OUTPUT:
#   output/nobinnest_episode.mp4
#   output/narration.srt
#
# DURATION:
#   Minimum: 60 seconds
#   Maximum: 90 seconds
#
# IMPORTANT:
# If narration is shorter than 60 seconds, the renderer
# automatically adds silence AFTER the narration.
#
# This means:
#
#   55.85 sec narration
#          ↓
#   + 4.15 sec silence
#          ↓
#   60.00 sec final episode
#
# The narration itself is NEVER stretched or cut.
# ============================================================


# ============================================================
# PATHS
# ============================================================

OUTPUT_DIR = Path("output")

STORY_FILE = OUTPUT_DIR / "story.json"
AUDIO_FILE = OUTPUT_DIR / "narration.mp3"

NORMALIZED_AUDIO_FILE = (
    OUTPUT_DIR / "narration_normalized.m4a"
)

VIDEO_FILE = (
    OUTPUT_DIR / "nobinnest_episode.mp4"
)

SRT_FILE = (
    OUTPUT_DIR / "narration.srt"
)


# ============================================================
# VIDEO SETTINGS
# ============================================================

WIDTH = 1280
HEIGHT = 720

FPS = 24

GROUND_Y = 525

MIN_DURATION = 60.0
MAX_DURATION = 90.0


# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=False):

    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf",

            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf",
        ]

    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf",

            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf",
        ]

    for path in candidates:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size,
            )

    return ImageFont.load_default()


TITLE_FONT = get_font(
    34,
    True,
)

LESSON_FONT = get_font(
    21,
    True,
)

SMALL_FONT = get_font(
    18,
    False,
)


OBJECT_FONT = get_font(
    25,
    True,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(
    value,
    low,
    high,
):

    return max(
        low,
        min(high, value),
    )


def lerp(
    a,
    b,
    t,
):

    return a + (
        b - a
    ) * t


def ease(
    t,
):

    t = clamp(
        t,
        0.0,
        1.0,
    )

    return (
        t
        * t
        * (3.0 - 2.0 * t)
    )


def rounded(
    draw,
    box,
    radius,
    fill,
    outline=None,
    width=1,
):

    draw.rounded_rectangle(
        box,
        radius=int(radius),
        fill=fill,
        outline=outline,
        width=max(
            1,
            int(width),
        ),
    )


def center_text(
    draw,
    text,
    center_x,
    y,
    font,
    fill,
):

    text = str(text)

    box = draw.textbbox(
        (0, 0),
        text,
        font=font,
    )

    text_width = (
        box[2] - box[0]
    )

    draw.text(
        (
            center_x
            - text_width / 2,
            y,
        ),
        text,
        font=font,
        fill=fill,
    )


def wrap_text(
    draw,
    text,
    font,
    max_width,
):

    words = str(text).split()

    lines = []

    current = ""

    for word in words:

        candidate = (
            word
            if not current
            else current + " " + word
        )

        box = draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )

        width = (
            box[2] - box[0]
        )

        if width <= max_width:

            current = candidate

        else:

            if current:

                lines.append(
                    current
                )

            current = word

    if current:

        lines.append(
            current
        )

    return lines


def normalize_text(text):

    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip().lower()


def has_any(
    text,
    words,
):

    return any(
        word in text
        for word in words
    )


# ============================================================
# COLOR DETECTION
# ============================================================

def detect_color(text):

    rules = [

        (
            ["red", "crimson"],
            "red",
            (225, 75, 75),
        ),

        (
            ["blue", "sky blue"],
            "blue",
            (75, 145, 230),
        ),

        (
            ["green"],
            "green",
            (80, 170, 90),
        ),

        (
            ["yellow", "gold"],
            "yellow",
            (245, 195, 55),
        ),

        (
            ["purple", "violet"],
            "purple",
            (155, 95, 205),
        ),

        (
            ["orange"],
            "orange",
            (240, 145, 55),
        ),

        (
            ["pink"],
            "pink",
            (235, 125, 170),
        ),

    ]

    for keywords, name, color in rules:

        if has_any(
            text,
            keywords,
        ):

            return (
                name,
                color,
            )

    return (
        "yellow",
        (245, 195, 55),
)


# ============================================================
# SCENE PLAN
# ============================================================

def build_scene_plan(
    story,
    scene_number,
):

    scene = story[
        "scenes"
    ][scene_number - 1]

    description = normalize_text(
        scene.get(
            "visual_description",
            "",
        )
    )

    narration = normalize_text(
        scene.get(
            "narration",
            "",
        )
    )

    lesson = normalize_text(
        story.get(
            "lesson",
            "",
        )
    )

    combined = (
        description
        + " "
        + narration
        + " "
        + lesson
    )

    color_name, color = (
        detect_color(
            combined
        )
    )

    # --------------------------------------------------------
    # OBJECT
    # --------------------------------------------------------

    object_rules = [

        (
            ["watermelon"],
            "watermelon",
            "watermelon",
        ),

        (
            ["strawberry"],
            "strawberry",
            "strawberry",
        ),

        (
            ["basket", "baskets"],
            "basket",
            "basket",
        ),

        (
            ["ball", "sphere"],
            "ball",
            color_name + " ball",
        ),

        (
            ["flower", "flowers"],
            "flower",
            color_name + " flower",
        ),

        (
            ["leaf", "leaves"],
            "leaf",
            "leaf",
        ),

        (
            ["apple", "apples"],
            "apple",
            color_name + " apple",
        ),

        (
            ["circle", "circular"],
            "circle",
            "circle",
        ),

        (
            ["square"],
            "square",
            "square",
        ),

        (
            ["triangle"],
            "triangle",
            "triangle",
        ),

        (
            ["book"],
            "book",
            "book",
        ),

        (
            ["star", "stars"],
            "star",
            "learning stars",
        ),

    ]

    object_type = "star"

    object_name = (
        "learning stars"
    )

    for (
        keywords,
        candidate,
        label,
    ) in object_rules:

        if has_any(
            combined,
            keywords,
        ):

            object_type = candidate
            object_name = label
            break

    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------

    action_rules = [

        (
            "walk",
            [
                "walk",
                "walks",
                "walking",
                "move",
                "moves",
                "moving",
            ],
        ),

        (
            "hop",
            [
                "hop",
                "hops",
                "hopping",
                "jump",
                "jumps",
                "jumping",
            ],
        ),

        (
            "fly",
            [
                "fly",
                "flies",
                "flying",
                "flew",
                "hover",
                "hovers",
            ],
        ),

        (
            "point",
            [
                "point",
                "points",
                "pointing",
            ],
        ),

        (
            "pick",
            [
                "pick",
                "picks",
                "picking",
                "reach",
                "reaches",
                "reaching",
                "place",
                "places",
            ],
        ),

        (
            "roll",
            [
                "roll",
                "rolls",
                "rolling",
            ],
        ),

        (
            "dance",
            [
                "dance",
                "dances",
                "dancing",
            ],
        ),

        (
            "celebrate",
            [
                "celebrate",
                "celebrates",
                "celebrating",
                "clap",
                "claps",
                "wave",
                "waves",
            ],
        ),

    ]

    ordered_actions = []

    for action, keywords in action_rules:

        positions = []

        for keyword in keywords:

            position = (
                description.find(
                    keyword
                )
            )

            if position >= 0:

                positions.append(
                    position
                )

        if positions:

            ordered_actions.append(
                (
                    min(positions),
                    action,
                )
            )

    ordered_actions.sort()

    actions = [
        action
        for _, action
        in ordered_actions
    ]

    if not actions:

        actions = [
            "general"
        ]

    # --------------------------------------------------------
    # CHARACTER FOCUS
    # --------------------------------------------------------

    characters = []

    for name in (
        "Bobo",
        "Mimi",
        "Kiki",
    ):

        if (
            name.lower()
            in description
        ):

            characters.append(
                name
            )

    if len(characters) == 1:

        focus = characters[0]

    else:

        focus = "group"

    if (
        "Kiki" in characters
        and "fly" in actions
    ):

        focus = "Kiki"

    elif (
        "Bobo" in characters
        and "walk" in actions
    ):

        focus = "Bobo"

    elif (
        "Mimi" in characters
        and "hop" in actions
    ):

        focus = "Mimi"

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    camera = "gentle"

    if "fly" in description:

        camera = "follow"

    elif (
        "walks into"
        in description
        or
        "walks through"
        in description
    ):

        camera = "track"

    elif "point" in description:

        camera = "focus"

    elif (
        "together"
        in description
        or
        "stand together"
        in description
    ):

        camera = "wide"

    return {

        "object":
            object_type,

        "object_name":
            object_name,

        "color":
            color,

        "action":
            actions[0],

        "actions":
            actions,

        "focus":
            focus,

        "camera":
            camera,

        "description":
            description,

    }


def beat_action(
    plan,
    t,
):

    actions = plan[
        "actions"
    ]

    if len(actions) <= 1:

        return actions[0]

    index = int(
        clamp(
            t,
            0.0,
            0.9999,
        )
        * len(actions)
    )

    index = min(
        index,
        len(actions) - 1,
    )

    return actions[index]


# ============================================================
# BACKGROUND
# ============================================================

def draw_background(
    draw,
    scene_number,
    time,
    camera_x,
):

    draw.rectangle(
        [
            0,
            0,
            WIDTH,
            HEIGHT,
        ],
        fill=(194, 231, 255),
    )

    # --------------------------------------------------------
    # SUN
    # --------------------------------------------------------

    sun_x = (
        110
        + 20
        * math.sin(
            time * 0.5
        )
    )

    draw.ellipse(
        [
            sun_x - 48,
            55,
            sun_x + 48,
            151,
        ],
        fill=(255, 221, 90),
    )

    # --------------------------------------------------------
    # CLOUDS
    # --------------------------------------------------------

    for i in range(4):

        x = (
            160
            + i * 330
            + 35
            * math.sin(
                time * 0.25 + i
            )
            - camera_x * 0.2
        )

        x %= 1400
        x -= 60

        y = (
            110
            + (i % 2) * 45
        )

        for (
            dx,
            dy,
            radius,
        ) in (
            (0, 15, 28),
            (32, 0, 36),
            (68, 16, 27),
        ):

            draw.ellipse(
                [
                    x + dx - radius,
                    y + dy - radius,
                    x + dx + radius,
                    y + dy + radius,
                ],
                fill=(255, 255, 255),
            )

    # --------------------------------------------------------
    # DISTANT TREES
    # --------------------------------------------------------

    for i in range(9):

        x = (
            i * 170
            - 50
            - camera_x * 0.15
        )

        x %= 1450
        x -= 80

        height = (
            95
            + (i % 3) * 18
        )

        draw.rectangle(
            [
                x + 45,
                GROUND_Y - height,
                x + 61,
                GROUND_Y,
            ],
            fill=(115, 85, 55),
        )

        draw.ellipse(
            [
                x,
                GROUND_Y
                - height
                - 70,
                x + 110,
                GROUND_Y
                - height
                + 40,
            ],
            fill=(105, 180, 105),
        )

    # --------------------------------------------------------
    # GROUND
    # --------------------------------------------------------

    draw.rectangle(
        [
            0,
            GROUND_Y,
            WIDTH,
            HEIGHT,
        ],
        fill=(126, 196, 103),
    )

    # --------------------------------------------------------
    # MOVING GRASS
    # --------------------------------------------------------

    for i in range(45):

        x = (
            i * 31
            - camera_x * 0.35
        ) % WIDTH

        sway = (
            5
            * math.sin(
                time * 3 + i
            )
        )

        y = (
            GROUND_Y
            + 5
            + (i % 5) * 24
        )

        draw.line(
            [
                (x, y + 24),
                (x + sway, y),
            ],
            fill=(73, 150, 72),
            width=2,
            )


# ============================================================
# STAR
# ============================================================

def star_points(
    center_x,
    center_y,
    radius,
):

    points = []

    for i in range(10):

        angle = (
            -math.pi / 2
            + i * math.pi / 5
        )

        r = (
            radius
            if i % 2 == 0
            else radius * 0.43
        )

        points.append(
            (
                center_x
                + math.cos(angle) * r,

                center_y
                + math.sin(angle) * r,
            )
        )

    return points


def draw_star(
    draw,
    center_x,
    center_y,
    radius,
    fill,
):

    draw.polygon(
        star_points(
            center_x,
            center_y,
            radius,
        ),
        fill=fill,
        outline=(255, 255, 255),
    )


# ============================================================
# BOBO
# ============================================================

def draw_bobo(
    draw,
    x,
    y,
    scale=1.0,
    phase=0.0,
    wave=0.0,
    bounce=0.0,
):

    s = scale

    fur = (
        154,
        96,
        57,
    )

    fur_light = (
        188,
        130,
        82,
    )

    dark = (
        85,
        52,
        35,
    )

    y += bounce

    walk = math.sin(
        phase
    )

    # shadow

    draw.ellipse(
        [
            x - 62 * s,
            GROUND_Y - 6,
            x + 62 * s,
            GROUND_Y + 10,
        ],
        fill=(93, 157, 83),
    )

    leg_shift = (
        8
        * walk
        * s
    )

    # legs

    draw.ellipse(
        [
            x - 60 * s + leg_shift,
            y + 205 * s,
            x - 5 * s + leg_shift,
            y + 250 * s,
        ],
        fill=dark,
    )

    draw.ellipse(
        [
            x + 5 * s - leg_shift,
            y + 205 * s,
            x + 60 * s - leg_shift,
            y + 250 * s,
        ],
        fill=dark,
    )

    # body

    draw.ellipse(
        [
            x - 65 * s,
            y + 65 * s,
            x + 65 * s,
            y + 230 * s,
        ],
        fill=fur,
    )

    # head

    draw.ellipse(
        [
            x - 76 * s,
            y - 5 * s,
            x + 76 * s,
            y + 145 * s,
        ],
        fill=fur_light,
        outline=dark,
        width=max(
            1,
            int(3 * s),
        ),
    )

    # ears

    draw.ellipse(
        [
            x - 76 * s,
            y - 38 * s,
            x - 28 * s,
            y + 45 * s,
        ],
        fill=fur,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    draw.ellipse(
        [
            x + 28 * s,
            y - 38 * s,
            x + 76 * s,
            y + 45 * s,
        ],
        fill=fur,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # eyes

    for eye_x in (
        -29,
        29,
    ):

        draw.ellipse(
            [
                x
                + (eye_x - 8) * s,
                y + 55 * s,
                x
                + (eye_x + 8) * s,
                y + 72 * s,
            ],
            fill=dark,
        )

    # muzzle

    draw.ellipse(
        [
            x - 16 * s,
            y + 83 * s,
            x + 16 * s,
            y + 107 * s,
        ],
        fill=(224, 169, 115),
    )

    # smile

    draw.arc(
        [
            x - 20 * s,
            y + 88 * s,
            x + 20 * s,
            y + 120 * s,
        ],
        10,
        170,
        fill=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # arms

    left_y = (
        y
        + (
            125
            + 14
            * math.sin(wave)
        ) * s
    )

    right_y = (
        y
        + (
            125
            - 14
            * math.sin(wave)
        ) * s
    )

    draw.line(
        [
            (
                x - 50 * s,
                y + 125 * s,
            ),
            (
                x - 88 * s,
                left_y,
            ),
        ],
        fill=fur_light,
        width=max(
            8,
            int(27 * s),
        ),
    )

    draw.line(
        [
            (
                x + 50 * s,
                y + 125 * s,
            ),
            (
                x + 88 * s,
                right_y,
            ),
        ],
        fill=fur_light,
        width=max(
            8,
            int(27 * s),
        ),
    )


# ============================================================
# MIMI
# ============================================================

def draw_mimi(
    draw,
    x,
    y,
    scale=1.0,
    phase=0.0,
    wave=0.0,
    bounce=0.0,
):

    s = scale

    white = (
        248,
        248,
        248,
    )

    pink = (
        242,
        165,
        190,
    )

    dark = (
        75,
        55,
        65,
    )

    y += bounce

    draw.ellipse(
        [
            x - 60 * s,
            GROUND_Y - 6,
            x + 60 * s,
            GROUND_Y + 10,
        ],
        fill=(93, 157, 83),
    )

    leg_shift = (
        7
        * math.sin(phase)
        * s
    )

    draw.ellipse(
        [
            x - 58 * s + leg_shift,
            y + 210 * s,
            x - 5 * s + leg_shift,
            y + 250 * s,
        ],
        fill=dark,
    )

    draw.ellipse(
        [
            x + 5 * s - leg_shift,
            y + 210 * s,
            x + 58 * s - leg_shift,
            y + 250 * s,
        ],
        fill=dark,
    )

    # body

    draw.ellipse(
        [
            x - 62 * s,
            y + 75 * s,
            x + 62 * s,
            y + 238 * s,
        ],
        fill=white,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # ears

    draw.ellipse(
        [
            x - 58 * s,
            y - 100 * s,
            x - 5 * s,
            y + 48 * s,
        ],
        fill=white,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    draw.ellipse(
        [
            x + 5 * s,
            y - 100 * s,
            x + 58 * s,
            y + 48 * s,
        ],
        fill=white,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    draw.ellipse(
        [
            x - 43 * s,
            y - 80 * s,
            x - 19 * s,
            y + 27 * s,
        ],
        fill=pink,
    )

    draw.ellipse(
        [
            x + 19 * s,
            y - 80 * s,
            x + 43 * s,
            y + 27 * s,
        ],
        fill=pink,
    )

    # head

    draw.ellipse(
        [
            x - 72 * s,
            y - 2 * s,
            x + 72 * s,
            y + 140 * s,
        ],
        fill=white,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # eyes

    for eye_x in (
        -29,
        29,
    ):

        draw.ellipse(
            [
                x
                + (eye_x - 8) * s,
                y + 57 * s,
                x
                + (eye_x + 8) * s,
                y + 73 * s,
            ],
            fill=dark,
        )

    draw.ellipse(
        [
            x - 9 * s,
            y + 80 * s,
            x + 9 * s,
            y + 95 * s,
        ],
        fill=pink,
    )

    draw.arc(
        [
            x - 19 * s,
            y + 86 * s,
            x + 19 * s,
            y + 120 * s,
        ],
        10,
        170,
        fill=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # arms

    left_y = (
        y
        + (
            125
            + 12
            * math.sin(wave)
        ) * s
    )

    right_y = (
        y
        + (
            125
            - 12
            * math.sin(wave)
        ) * s
    )

    draw.line(
        [
            (
                x - 48 * s,
                y + 130 * s,
            ),
            (
                x - 85 * s,
                left_y,
            ),
        ],
        fill=white,
        width=max(
            8,
            int(28 * s),
        ),
    )

    draw.line(
        [
            (
                x + 48 * s,
                y + 130 * s,
            ),
            (
                x + 85 * s,
                right_y,
            ),
        ],
        fill=white,
        width=max(
            8,
            int(28 * s),
        ),
    )


# ============================================================
# KIKI
# ============================================================

def draw_kiki(
    draw,
    x,
    y,
    scale=1.0,
    phase=0.0,
    flight=0.0,
):

    s = scale

    body_color = (
        90,
        170,
        220,
    )

    dark = (
        55,
        95,
        135,
    )

    white = (
        250,
        250,
        250,
    )

    y += (
        10
        * math.sin(
            flight
            * math.pi
            * 2
        )
    )

    flap = math.sin(
        phase * 2.3
    )

    # wings

    draw.ellipse(
        [
            x - 100 * s,
            y + 20 * s
            + flap * 25 * s,
            x - 20 * s,
            y + 95 * s
            - flap * 10 * s,
        ],
        fill=white,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    draw.ellipse(
        [
            x + 20 * s,
            y + 20 * s
            - flap * 10 * s,
            x + 100 * s,
            y + 95 * s
            + flap * 25 * s,
        ],
        fill=white,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # body

    draw.ellipse(
        [
            x - 58 * s,
            y + 45 * s,
            x + 58 * s,
            y + 145 * s,
        ],
        fill=body_color,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # head

    draw.ellipse(
        [
            x - 65 * s,
            y - 20 * s,
            x + 65 * s,
            y + 95 * s,
        ],
        fill=body_color,
        outline=dark,
        width=max(
            1,
            int(2 * s),
        ),
    )

    # eyes

    for eye_x in (
        -25,
        25,
    ):

        draw.ellipse(
            [
                x
                + (eye_x - 7) * s,
                y + 22 * s,
                x
                + (eye_x + 7) * s,
                y + 37 * s,
            ],
            fill=dark,
        )

    # beak

    draw.polygon(
        [
            (
                x + 60 * s,
                y + 28 * s,
            ),
            (
                x + 102 * s,
                y + 48 * s,
            ),
            (
                x + 60 * s,
                y + 65 * s,
            ),
        ],
        fill=(245, 175, 60),
    )


# ============================================================
# BASKET
# ============================================================

def draw_basket(
    draw,
    x,
    y,
    scale=1.0,
):

    s = scale

    rounded(
        draw,
        [
            x - 70 * s,
            y - 30 * s,
            x + 70 * s,
            y + 70 * s,
        ],
        14 * s,
        (188, 126, 65),
        (115, 75, 40),
        4,
    )

    for dx in (
        -35,
        0,
        35,
    ):

        draw.line(
            [
                (
                    x + dx * s,
                    y - 25 * s,
                ),
                (
                    x + dx * s,
                    y + 65 * s,
                ),
            ],
            fill=(220, 160, 90),
            width=max(
                2,
                int(4 * s),
            ),
        )


# ============================================================
# OBJECTS
# ============================================================

def draw_object(
    draw,
    plan,
    t,
):

    obj = plan[
        "object"
    ]

    color = plan[
        "color"
    ]

    # --------------------------------------------------------
    # BASKETS
    # --------------------------------------------------------

    if obj == "basket":

        draw_basket(
            draw,
            640,
            470,
            1.15,
        )

        draw_basket(
            draw,
            900,
            490,
            0.62,
        )

        return

    # --------------------------------------------------------
    # WATERMELON
    # --------------------------------------------------------

    if obj == "watermelon":

        x = (
            720
            + 25
            * math.sin(
                t * 2
            )
        )

        y = 405

        draw.ellipse(
            [
                x - 110,
                y - 65,
                x + 110,
                y + 65,
            ],
            fill=(65, 170, 85),
            outline=(255, 255, 255),
            width=4,
        )

        return

    # --------------------------------------------------------
    # STRAWBERRY
    # --------------------------------------------------------

    if obj == "strawberry":

        x = 700

        y = (
            420
            - 8
            * math.sin(
                t * 3
            )
        )

        draw.polygon(
            [
                (x, y - 45),
                (x - 38, y + 35),
                (x, y + 65),
                (x + 38, y + 35),
            ],
            fill=(225, 70, 75),
            outline=(255, 255, 255),
        )

        return

    # --------------------------------------------------------
    # GENERAL OBJECT
    # --------------------------------------------------------

    x = (
        650
        + 35
        * math.sin(
            t * 2
        )
    )

    y = (
        405
        + 10
        * math.sin(
            t * 3
        )
    )

    if obj == "ball":

        radius = 68

        draw.ellipse(
            [
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ],
            fill=color,
            outline=(255, 255, 255),
            width=4,
        )

        draw.ellipse(
            [
                x - 25,
                y - 35,
                x - 5,
                y - 15,
            ],
            fill=(255, 255, 255),
        )

    elif obj == "flower":

        for i in range(6):

            angle = (
                i
                * math.pi
                / 3
            )

            px = (
                x
                + 45
                * math.cos(angle)
            )

            py = (
                y
                + 45
                * math.sin(angle)
            )

            draw.ellipse(
                [
                    px - 30,
                    py - 30,
                    px + 30,
                    py + 30,
                ],
                fill=color,
            )

        draw.ellipse(
            [
                x - 25,
                y - 25,
                x + 25,
                y + 25,
            ],
            fill=(248, 205, 55),
        )

        draw.line(
            [
                (x, y + 25),
                (x, y + 110),
            ],
            fill=(70, 145, 70),
            width=8,
        )

    elif obj == "leaf":

        draw.ellipse(
            [
                x - 90,
                y - 35,
                x + 90,
                y + 35,
            ],
            fill=(80, 175, 90),
            outline=(255, 255, 255),
            width=3,
        )

        draw.line(
            [
                (x - 80, y + 25),
                (x + 80, y - 25),
            ],
            fill=(45, 120, 65),
            width=5,
        )

    elif obj == "apple":

        draw.ellipse(
            [
                x - 62,
                y - 55,
                x + 62,
                y + 65,
            ],
            fill=color,
            outline=(255, 255, 255),
            width=3,
        )

        draw.line(
            [
                (x, y - 48),
                (x + 8, y - 90),
            ],
            fill=(95, 65, 35),
            width=8,
        )

    elif obj == "circle":

        draw.ellipse(
            [
                x - 80,
                y - 80,
                x + 80,
                y + 80,
            ],
            fill=color,
            outline=(255, 255, 255),
            width=5,
        )

    elif obj == "square":

        draw.rectangle(
            [
                x - 75,
                y - 75,
                x + 75,
                y + 75,
            ],
            fill=color,
            outline=(255, 255, 255),
            width=5,
        )

    elif obj == "triangle":

        draw.polygon(
            [
                (x, y - 95),
                (x - 100, y + 75),
                (x + 100, y + 75),
            ],
            fill=color,
            outline=(255, 255, 255),
        )

    elif obj == "book":

        draw.rectangle(
            [
                x - 100,
                y - 55,
                x,
                y + 55,
            ],
            fill=(235, 110, 105),
            outline=(255, 255, 255),
            width=3,
        )

        draw.rectangle(
            [
                x,
                y - 55,
                x + 100,
                y + 55,
            ],
            fill=(90, 145, 220),
            outline=(255, 255, 255),
            width=3,
        )

    else:

        for i in range(5):

            sx = (
                430
                + i * 105
            )

            sy = (
                400
                + 12
                * math.sin(
                    t * 2 + i
                )
            )

            draw_star(
                draw,
                sx,
                sy,
                28,
                (248, 204, 70),
    )


# ============================================================
# ACTION EFFECTS
# ============================================================

def draw_action_effects(
    draw,
    plan,
    t,
):

    action = beat_action(
        plan,
        t,
    )

    x = 650
    y = 405

    # --------------------------------------------------------
    # FLY
    # --------------------------------------------------------

    if action == "fly":

        for i in range(4):

            yy = (
                y - 45
                + i * 22
            )

            length = (
                35
                + 15
                * math.sin(
                    t * 7 + i
                )
            )

            draw.line(
                [
                    (
                        x - 95,
                        yy,
                    ),
                    (
                        x - 95 - length,
                        yy,
                    ),
                ],
                fill=(255, 255, 255),
                width=3,
            )

    # --------------------------------------------------------
    # POINT
    # --------------------------------------------------------

    elif action == "point":

        radius = (
            50
            + 8
            * math.sin(
                t * 8
            )
        )

        draw.ellipse(
            [
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ],
            outline=(255, 240, 130),
            width=3,
        )

    # --------------------------------------------------------
    # PICK
    # --------------------------------------------------------

    elif action == "pick":

        for i in range(6):

            angle = (
                t * 2
                + i
                * math.pi
                / 3
            )

            radius = 58

            draw_star(
                draw,
                x
                + math.cos(angle)
                * radius,

                y
                + math.sin(angle)
                * radius,

                7,
                (255, 220, 80),
            )

    # --------------------------------------------------------
    # DANCE
    # --------------------------------------------------------

    elif action in (
        "dance",
        "celebrate",
    ):

        for i in range(12):

            angle = (
                i * 0.7
                + t * 1.5
            )

            radius = (
                90
                + 20
                * math.sin(
                    t * 2 + i
                )
            )

            px = (
                640
                + math.cos(angle)
                * radius
            )

            py = (
                300
                + math.sin(
                    angle * 1.2
                )
                * 120
            )

            draw.ellipse(
                [
                    px - 3,
                    py - 3,
                    px + 3,
                    py + 3,
                ],
                fill=(255, 215, 75),
            )


# ============================================================
# CHARACTER POSITIONS
# ============================================================

def get_positions(
    scene_number,
    t,
):

    progress = ease(t)

    bobo = [
        360,
        285,
    ]

    mimi = [
        650,
        285,
    ]

    kiki = [
        930,
        255,
    ]

    if scene_number == 1:

        bobo[0] = lerp(
            -150,
            360,
            ease(
                min(
                    1,
                    t / 0.55,
                )
            ),
        )

        mimi[0] = (
            610
            + 25
            * math.sin(
                t
                * math.pi
                * 2
            )
        )

        kiki[0] = (
            930
            + 55
            * math.sin(
                t
                * math.pi
                * 1.5
            )
        )

        kiki[1] = (
            250
            + 35
            * math.sin(
                t
                * math.pi
                * 3
            )
        )

    elif scene_number == 2:

        bobo[0] = lerp(
            350,
            455,
            progress,
        )

        mimi[0] = lerp(
            680,
            620,
            progress,
        )

        kiki[0] = lerp(
            970,
            820,
            progress,
        )

        kiki[1] = (
            275
            + 25
            * math.sin(
                t * 2.5
            )
        )

    elif scene_number == 3:

        bobo[0] = lerp(
            455,
            390,
            progress,
        )

        mimi[0] = lerp(
            620,
            700,
            progress,
        )

        kiki[0] = (
            900
            + 80
            * math.sin(
                t * 0.9
            )
        )

        kiki[1] = (
            235
            + 50
            * math.sin(
                t * 1.7
            )
        )

    else:

        bobo[0] = lerp(
            390,
            455,
            progress,
        )

        mimi[0] = lerp(
            700,
            650,
            progress,
        )

        kiki[0] = lerp(
            900,
            820,
            progress,
        )

        kiki[1] = (
            255
            + 35
            * math.sin(
                t * 1.8
            )
        )

    return {
        "Bobo":
            tuple(bobo),

        "Mimi":
            tuple(mimi),

        "Kiki":
            tuple(kiki),
    }


# ============================================================
# FRAME RENDER
# ============================================================

def render_frame(
    story,
    scene_number,
    local_time,
    scene_duration,
    total_duration,
):

    image = Image.new(
        "RGB",
        (
            WIDTH,
            HEIGHT,
        ),
        (255, 255, 255),
    )

    draw = ImageDraw.Draw(
        image
    )

    plan = build_scene_plan(
        story,
        scene_number,
    )

    t = clamp(
        local_time
        / max(
            scene_duration,
            0.001,
        ),
        0,
        1,
    )

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    camera_x = (
        18
        * math.sin(
            t
            * math.pi
            * 1.2
        )
    )

    if plan["camera"] == "track":

        camera_x = lerp(
            -25,
            35,
            ease(t),
        )

    elif plan["camera"] == "follow":

        camera_x = (
            35
            * math.sin(
                t
                * math.pi
                * 1.2
            )
        )

    elif plan["camera"] == "focus":

        camera_x = (
            -18
            * math.sin(
                t * math.pi
            )
        )

    elif plan["camera"] == "wide":

        camera_x = (
            12
            * math.sin(
                t * math.pi
            )
        )

    draw_background(
        draw,
        scene_number,
        local_time,
        camera_x,
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = str(
        story.get(
            "title",
            "NobiNest Adventure",
        )
    )

    if len(title) > 48:

        title = (
            title[:45]
            + "..."
        )

    center_text(
        draw,
        title,
        WIDTH / 2,
        18,
        TITLE_FONT,
        (55, 70, 90),
    )

    center_text(
        draw,
        (
            f"Scene "
            f"{scene_number}"
            f" of 4"
        ),
        WIDTH / 2,
        58,
        SMALL_FONT,
        (70, 90, 105),
    )

    # --------------------------------------------------------
    # ACTION LABEL
    # --------------------------------------------------------

    action = beat_action(
        plan,
        t,
    )

    labels = {

        "walk":
            "GO!",

        "hop":
            "HOP!",

        "fly":
            "FLY!",

        "point":
            "LOOK!",

        "pick":
            "REACH!",

        "roll":
            "ROLL!",

        "dance":
            "DANCE!",

        "celebrate":
            "YAY!",
    }

    if (
        action in labels
        and
        math.sin(
            t * math.pi * 8
        ) > -0.25
    ):

        center_text(
            draw,
            labels[action],
            WIDTH / 2,
            92,
            SMALL_FONT,
            (70, 85, 100),
        )

    # --------------------------------------------------------
    # OBJECT
    # --------------------------------------------------------

    draw_object(
        draw,
        plan,
        t,
    )

    draw_action_effects(
        draw,
        plan,
        t,
                )


    # --------------------------------------------------------
    # CHARACTERS
    # --------------------------------------------------------

    positions = get_positions(
        scene_number,
        t,
    )

    bobo_x, bobo_y = (
        positions["Bobo"]
    )

    mimi_x, mimi_y = (
        positions["Mimi"]
    )

    kiki_x, kiki_y = (
        positions["Kiki"]
    )

    bobo_bounce = (
        6
        * math.sin(
            local_time * 7
        )
    )

    mimi_bounce = (
        -8
        * max(
            0,
            math.sin(
                local_time * 4.2
            ),
        )
    )

    kiki_bounce = (
        10
        * math.sin(
            local_time * 2.8
        )
    )

    if action == "hop":

        mimi_bounce = (
            -35
            * max(
                0,
                math.sin(
                    local_time * 6.5
                ),
            )
        )

    if action == "fly":

        kiki_bounce = (
            25
            * math.sin(
                local_time * 5.5
            )
        )

    if action in (
        "dance",
        "celebrate",
    ):

        bobo_bounce = (
            15
            * math.sin(
                local_time * 8
            )
        )

        mimi_bounce = (
            -20
            * max(
                0,
                math.sin(
                    local_time * 7
                ),
            )
        )

        kiki_bounce = (
            24
            * math.sin(
                local_time * 6
            )
        )

    draw_bobo(
        draw,
        bobo_x
        - camera_x * 0.30,
        bobo_y,
        1.08,
        local_time * 5.5,
        local_time
        * (
            4.2
            if action
            in (
                "dance",
                "celebrate",
                "walk",
            )
            else 1
        ),
        bobo_bounce,
    )

    draw_mimi(
        draw,
        mimi_x
        - camera_x * 0.35,
        mimi_y,
        1.04,
        local_time * 4.2,
        local_time
        * (
            4
            if action
            in (
                "dance",
                "celebrate",
                "hop",
            )
            else 1.1
        ),
        mimi_bounce,
    )

    draw_kiki(
        draw,
        kiki_x
        - camera_x * 0.42,
        kiki_y,
        0.92,
        local_time * 7,
        kiki_bounce,
    )

    # --------------------------------------------------------
    # LESSON CARD
    # --------------------------------------------------------

    lesson = str(
        story.get(
            "lesson",
            "",
        )
    ).strip()

    if lesson:

        overlay = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT,
            ),
            (
                0,
                0,
                0,
                0,
            ),
        )

        overlay_draw = ImageDraw.Draw(
            overlay
        )

        rounded(
            overlay_draw,
            [
                55,
                600,
                WIDTH - 55,
                690,
            ],
            20,
            (
                255,
                255,
                255,
                205,
            ),
            (
                80,
                100,
                120,
                180,
            ),
            2,
        )

        lines = wrap_text(
            overlay_draw,
            "Lesson: " + lesson,
            LESSON_FONT,
            WIDTH - 160,
        )

        y = 616

        for line in lines[:2]:

            center_text(
                overlay_draw,
                line,
                WIDTH / 2,
                y,
                LESSON_FONT,
                (
                    40,
                    50,
                    65,
                    230,
                ),
            )

            y += 25

        image = Image.alpha_composite(
            image.convert("RGBA"),
            overlay,
        ).convert("RGB")

    # --------------------------------------------------------
    # SCENE FADE-IN
    # --------------------------------------------------------

    fade_seconds = 0.45

    fade_alpha = (
        1
        - clamp(
            t / fade_seconds,
            0,
            1,
        )
    )

    if fade_alpha > 0:

        overlay = Image.new(
            "RGBA",
            (
                WIDTH,
                HEIGHT,
            ),
            (
                0,
                0,
                0,
                int(
                    255
                    * fade_alpha
                ),
            ),
        )

        image = Image.alpha_composite(
            image.convert("RGBA"),
            overlay,
        ).convert("RGB")

    return image


# ============================================================
# AUDIO
# ============================================================

def get_audio_duration(
    audio_path,
):

    command = [

        "ffprobe",

        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-of",
        "default=noprint_wrappers=1:nokey=1",

        str(audio_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    value = (
        result.stdout
        .strip()
    )

    if not value:

        raise RuntimeError(
            "Could not determine "
            "narration duration."
        )

    return float(value)


# ============================================================
# AUDIO NORMALIZATION
# ============================================================

def normalize_audio_duration(
    actual_duration,
):

    # --------------------------------------------------------
    # SHORT AUDIO
    # --------------------------------------------------------

    if (
        actual_duration
        < MIN_DURATION
    ):

        silence_needed = (
            MIN_DURATION
            - actual_duration
        )

        print("")
        print(
            "AUDIO NORMALIZATION"
        )
        print(
            "--------------------"
        )

        print(
            f"Original narration: "
            f"{actual_duration:.2f}s"
        )

        print(
            f"Silence required: "
            f"{silence_needed:.2f}s"
        )

        print(
            f"Final target: "
            f"{MIN_DURATION:.2f}s"
        )

        print(
            "Adding silence after narration..."
        )

        command = [

            "ffmpeg",

            "-y",

            "-i",
            str(AUDIO_FILE),

            "-af",
            (
                "apad="
                f"pad_dur={silence_needed:.3f}"
            ),

            "-t",
            f"{MIN_DURATION:.3f}",

            "-c:a",
            "aac",

            "-b:a",
            "128k",

            str(
                NORMALIZED_AUDIO_FILE
            ),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:

            raise RuntimeError(
                "FFmpeg could not "
                "normalize the audio.\n\n"
                + result.stderr
            )

        return (
            MIN_DURATION,
            NORMALIZED_AUDIO_FILE,
        )

    # --------------------------------------------------------
    # ALREADY VALID
    # --------------------------------------------------------

    if (
        actual_duration
        <= MAX_DURATION
    ):

        return (
            actual_duration,
            AUDIO_FILE,
        )

    # --------------------------------------------------------
    # TOO LONG
    # --------------------------------------------------------

    raise RuntimeError(
        "Narration is "
        f"{actual_duration:.2f}s. "
        "NobiNest episodes must be "
        f"{MIN_DURATION:.0f}-{MAX_DURATION:.0f} "
        "seconds. "
        "The renderer will not cut "
        "spoken words."
    )


# ============================================================
# SRT TIMESTAMP
# ============================================================

def format_timestamp(
    seconds,
):

    total_seconds = int(
        seconds
    )

    milliseconds = int(
        round(
            (
                seconds
                - total_seconds
            )
            * 1000
        )
    )

    if milliseconds >= 1000:

        milliseconds = 0
        total_seconds += 1

    hours = (
        total_seconds
        // 3600
    )

    minutes = (
        total_seconds
        % 3600
    ) // 60

    secs = (
        total_seconds
        % 60
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


# ============================================================
# SUBTITLES
# ============================================================

def create_subtitles(
    story,
    spoken_duration,
):

    segments = []

    # --------------------------------------------------------
    # SCENE NARRATION
    # --------------------------------------------------------

    for index, scene in enumerate(
        story.get(
            "scenes",
            [],
        ),
        1,
    ):

        narration = str(
            scene.get(
                "narration",
                "",
            )
        ).strip()

        if narration:

            segments.append(
                {
                    "label":
                        f"Scene {index}",

                    "text":
                        narration,
                }
            )

    # --------------------------------------------------------
    # SONG
    # --------------------------------------------------------

    song = story.get(
        "song",
        {},
    )

    if isinstance(
        song,
        dict,
    ):

        lyrics = str(
            song.get(
                "lyrics",
                "",
            )
        ).strip()

        if lyrics:

            segments.append(
                {
                    "label":
                        "Song",

                    "text":
                        lyrics,
                }
            )

    # --------------------------------------------------------
    # ENDING
    # --------------------------------------------------------

    ending = str(
        story.get(
            "ending",
            "",
        )
    ).strip()

    if ending:

        segments.append(
            {
                "label":
                    "Ending",

                "text":
                    ending,
            }
        )

    if not segments:

        SRT_FILE.write_text(
            "",
            encoding="utf-8",
        )

        return

    total_words = sum(
        max(
            1,
            len(
                segment[
                    "text"
                ].split()
            ),
        )
        for segment in segments
    )

    cursor = 0.0

    cues = []

    for segment in segments:

        words = segment[
            "text"
        ].split()

        segment_duration = (
            spoken_duration
            * len(words)
            / total_words
        )

        start = cursor

        end = min(
            spoken_duration,
            cursor
            + segment_duration,
        )

        cursor = end

        # Short child-friendly captions.

        chunk_size = 6

        chunks = [

            words[i:i + chunk_size]

            for i in range(
                0,
                len(words),
                chunk_size,
            )
        ]

        chunk_word_count = sum(
            len(chunk)
            for chunk in chunks
        )

        local_cursor = start

        for chunk in chunks:

            chunk_duration = (
                (
                    end
                    - start
                )
                * len(chunk)
                / max(
                    1,
                    chunk_word_count,
                )
            )

            cue_end = min(
                end,
                local_cursor
                + chunk_duration,
            )

            cues.append(
                (
                    local_cursor,
                    cue_end,
                    " ".join(chunk),
                )
            )

            local_cursor = cue_end

    with open(
        SRT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        for (
            index,
            (
                start,
                end,
                caption,
            ),
        ) in enumerate(
            cues,
            1,
        ):

            file.write(
                f"{index}\n"
            )

            file.write(
                f"{format_timestamp(start)} "
                f"--> "
                f"{format_timestamp(end)}\n"
            )

            file.write(
                caption
            )

            file.write(
                "\n\n"
            )


# ============================================================
# VIDEO RENDER
# ============================================================

def render_video(
    story,
    final_duration,
    audio_path,
):

    print("")
    print(
        "=" * 60
    )

    print(
        "NOBINEST SCENE-AWARE "
        "2D MOTION RENDERER"
    )

    print(
        "=" * 60
    )

    print(
        f"Resolution: "
        f"{WIDTH}x{HEIGHT}"
    )

    print(
        f"Frame rate: "
        f"{FPS}"
    )

    print(
        f"Final duration: "
        f"{final_duration:.2f}s"
    )

    print("")

    # --------------------------------------------------------
    # SHOW SCENE PLANS
    # --------------------------------------------------------

    for index in range(
        1,
        5,
    ):

        plan = build_scene_plan(
            story,
            index,
        )

        print(
            f"Scene {index}: "
            f"object="
            f"{plan['object_name']} | "
            f"action="
            f"{plan['action']} | "
            f"focus="
            f"{plan['focus']}"
        )

        print(
            "  visual_description: "
            + str(
                story[
                    "scenes"
                ][index - 1].get(
                    "visual_description",
                    "",
                )
            )
        )

    # --------------------------------------------------------
    # SUBTITLE FILTER
    # --------------------------------------------------------

    subtitle_path = str(
        SRT_FILE
    )

    subtitle_path = (
        subtitle_path
        .replace(
            "\\",
            "/",
        )
        .replace(
            ":",
            "\\:",
        )
    )

    subtitle_filter = (
        "subtitles="
        + subtitle_path
        + ":force_style="
        "'FontName=DejaVu Sans,"
        "FontSize=21,"
        "Bold=1,"
        "Alignment=2,"
        "MarginV=34,"
        "Outline=2,"
        "Shadow=1'"
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # DO NOT USE -shortest
    #
    # The normalized audio is exactly the final duration.
    # -shortest caused the old renderer to terminate at the
    # original narration duration.
    # --------------------------------------------------------

    command = [

        "ffmpeg",

        "-y",

        # VIDEO INPUT

        "-f",
        "rawvideo",

        "-pix_fmt",
        "rgb24",

        "-s",
        f"{WIDTH}x{HEIGHT}",

        "-r",
        str(FPS),

        "-i",
        "-",

        # AUDIO INPUT

        "-i",
        str(audio_path),

        # SUBTITLES

        "-vf",
        subtitle_filter,

        # VIDEO

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "22",

        "-pix_fmt",
        "yuv420p",

        # AUDIO

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # EXACT FINAL LENGTH

        "-t",
        f"{final_duration:.3f}",

        str(VIDEO_FILE),
    ]

    print("")
    print(
        "Starting FFmpeg..."
    )

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    total_frames = max(
        1,
        int(
            math.ceil(
                final_duration
                * FPS
            )
        ),
    )

    last_scene = 0

    try:

        for frame_index in range(
            total_frames
        ):

            current_time = (
                frame_index
                / FPS
            )

            # Four equal visual chapters.

            scene_number = min(
                4,
                int(
                    (
                        current_time
                        / final_duration
                    )
                    * 4
                )
                + 1,
            )

            scene_duration = (
                final_duration
                / 4
            )

            local_time = (
                current_time
                - (
                    scene_number
                    - 1
                )
                * scene_duration
            )

            local_time = clamp(
                local_time,
                0,
                scene_duration,
            )

            if (
                scene_number
                != last_scene
            ):

                print(
                    f"Animating "
                    f"scene "
                    f"{scene_number}/4..."
                )

                last_scene = (
                    scene_number
                )

            frame = render_frame(
                story,
                scene_number,
                local_time,
                scene_duration,
                final_duration,
            )

            process.stdin.write(
                frame.tobytes()
            )

            if (
                frame_index % FPS
                == 0
            ):

                percentage = (
                    frame_index
                    / total_frames
                    * 100
                )

                print(
                    f"Rendered "
                    f"{current_time:5.1f}s / "
                    f"{final_duration:5.1f}s "
                    f"("
                    f"{percentage:5.1f}%"
                    f")"
                )

        process.stdin.close()

        stderr = (
            process.stderr
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        return_code = (
            process.wait()
        )

        if return_code != 0:

            raise RuntimeError(
                "FFmpeg failed "
                f"with exit code "
                f"{return_code}\n\n"
                f"{stderr}"
            )

    except BrokenPipeError:

        stderr = (
            process.stderr
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        process.wait()

        raise RuntimeError(
            "FFmpeg closed the "
            "video pipe unexpectedly."
            "\n\n"
            + stderr
    )


# ============================================================
# STORY VALIDATION
# ============================================================

def validate_story(
    story,
):

    if not isinstance(
        story,
        dict,
    ):

        raise RuntimeError(
            "story.json is not "
            "a JSON object."
        )

    scenes = story.get(
        "scenes"
    )

    if not isinstance(
        scenes,
        list,
    ):

        raise RuntimeError(
            "story.json does not "
            "contain scenes."
        )

    if len(scenes) != 4:

        raise RuntimeError(
            "NobiNest requires "
            "exactly 4 scenes."
        )

    for index, scene in enumerate(
        scenes,
        1,
    ):

        if not str(
            scene.get(
                "visual_description",
                "",
            )
        ).strip():

            raise RuntimeError(
                f"Scene {index} "
                "is missing "
                "visual_description."
            )

        if not str(
            scene.get(
                "narration",
                "",
            )
        ).strip():

            raise RuntimeError(
                f"Scene {index} "
                "is missing "
                "narration."
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print(
        "=" * 60
    )

    print(
        "NOBINEST KIDS "
        "ANIMATED VIDEO RENDERER"
    )

    print(
        "=" * 60
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # FILE CHECKS
    # --------------------------------------------------------

    if not STORY_FILE.exists():

        raise FileNotFoundError(
            f"Missing story file: "
            f"{STORY_FILE}"
        )

    if not AUDIO_FILE.exists():

        raise FileNotFoundError(
            f"Missing narration file: "
            f"{AUDIO_FILE}"
        )

    # --------------------------------------------------------
    # LOAD STORY
    # --------------------------------------------------------

    with open(
        STORY_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        story = json.load(
            file
        )

    validate_story(
        story
    )

    # --------------------------------------------------------
    # READ ACTUAL AUDIO LENGTH
    # --------------------------------------------------------

    spoken_duration = (
        get_audio_duration(
            AUDIO_FILE
        )
    )

    print(
        f"Story: "
        f"{story.get('title', 'Untitled')}"
    )

    print(
        f"Lesson: "
        f"{story.get('lesson', '')}"
    )

    print(
        f"Original narration: "
        f"{spoken_duration:.2f}s"
    )

    # --------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------

    final_duration, audio_path = (
        normalize_audio_duration(
            spoken_duration
        )
    )

    print("")

    print(
        f"Final episode target: "
        f"{final_duration:.2f}s"
    )

    if (
        final_duration
        > spoken_duration
    ):

        print(
            f"Added silence: "
            f"{final_duration - spoken_duration:.2f}s"
        )

    # --------------------------------------------------------
    # SUBTITLES USE SPOKEN AUDIO ONLY
    #
    # This is important.
    #
    # If narration = 55.85 sec
    # and final episode = 60 sec,
    # subtitles still end at 55.85 sec.
    #
    # The final 4.15 sec contains no fake subtitles.
    # --------------------------------------------------------

    print("")
    print(
        "Creating subtitles..."
    )

    create_subtitles(
        story,
        spoken_duration,
    )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    print("")
    print(
        "Rendering scene-specific "
        "animation..."
    )

    render_video(
        story,
        final_duration,
        audio_path,
    )

    # --------------------------------------------------------
    # VERIFY OUTPUT
    # --------------------------------------------------------

    if not VIDEO_FILE.exists():

        raise RuntimeError(
            "Renderer finished but "
            "the MP4 was not created."
        )

    actual_video_duration = (
        get_audio_duration(
            VIDEO_FILE
        )
    )

    print("")
    print(
        "=" * 60
    )

    print(
        "FINAL VIDEO VALIDATION"
    )

    print(
        "=" * 60
    )

    print(
        f"MP4 duration: "
        f"{actual_video_duration:.2f}s"
    )

    print(
        f"Required minimum: "
        f"{MIN_DURATION:.2f}s"
    )

    print(
        f"Required maximum: "
        f"{MAX_DURATION:.2f}s"
    )

    if (
        actual_video_duration
        < MIN_DURATION - 0.10
    ):

        raise RuntimeError(
            "FINAL VIDEO IS TOO SHORT: "
            f"{actual_video_duration:.2f}s"
        )

    if (
        actual_video_duration
        > MAX_DURATION + 0.15
    ):

        raise RuntimeError(
            "FINAL VIDEO IS TOO LONG: "
            f"{actual_video_duration:.2f}s"
        )

    size_mb = (
        VIDEO_FILE.stat().st_size
        / (1024 * 1024)
    )

    print("")
    print(
        "=" * 60
    )

    print(
        "NOBINEST VIDEO CREATED "
        "SUCCESSFULLY"
    )

    print(
        "=" * 60
    )

    print(
        f"Video: "
        f"{VIDEO_FILE}"
    )

    print(
        f"Duration: "
        f"{actual_video_duration:.2f}s"
    )

    print(
        f"Size: "
        f"{size_mb:.2f} MB"
    )

    print(
        f"Subtitles: "
        f"{SRT_FILE}"
    )

    print("")
    print(
        "Duration normalization: ENABLED"
    )

    print(
        "Scene-aware animation: ENABLED"
    )

    print(
        "Visual descriptions: ENABLED"
    )

    print(
        "Automatic short-audio padding: ENABLED"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print("")
        print(
            "=" * 60
        )

        print(
            "RENDERER ERROR"
        )

        print(
            "=" * 60
        )

        print(
            str(exc)
        )

        sys.exit(1)
