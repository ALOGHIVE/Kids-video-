math
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NOBINEST KIDS
# SCENE-AWARE 2D MOTION VIDEO RENDERER V3
# ============================================================
#
# This is a COMPLETE self-contained renderer.
#
# It reads:
#   output/story.json
#   output/narration.mp3
#
# It creates:
#   output/nobinnest_episode.mp4
#   output/narration.srt
#
# Features:
#   - exactly 4 visual scenes
#   - reads visual_description
#   - scene-specific choreography
#   - walking
#   - hopping
#   - flying
#   - pointing
#   - reaching
#   - picking
#   - dancing
#   - waving
#   - object interaction
#   - animated educational objects
#   - moving clouds
#   - swaying grass
#   - flowers
#   - particles
#   - camera movement
#   - scene transitions
#   - subtitles
#   - automatic minimum 60-second final video
#
# IMPORTANT:
# This file intentionally contains all helper functions.
# There are no external renderer helper dependencies.
# ============================================================


OUTPUT_DIR = Path("output")
STORY_FILE = OUTPUT_DIR / "story.json"
AUDIO_FILE = OUTPUT_DIR / "narration.mp3"
VIDEO_FILE = OUTPUT_DIR / "nobinnest_episode.mp4"
SRT_FILE = OUTPUT_DIR / "narration.srt"

WIDTH = 1280
HEIGHT = 720
FPS = 24

MIN_DURATION = 60.0
MAX_DURATION = 90.0

GROUND_Y = 525


# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=False):
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


TITLE_FONT = get_font(34, True)
SCENE_FONT = get_font(18, False)
LESSON_FONT = get_font(21, True)
OBJECT_FONT = get_font(27, True)
SMALL_FONT = get_font(17, True)


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def alpha_layer(base, overlay):
    return Image.alpha_composite(
        base.convert("RGBA"),
        overlay.convert("RGBA"),
    ).convert("RGB")


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_center(draw, text, cx, y, font, fill):
    bbox = draw.textbbox((0, 0), str(text), font=font)
    width = bbox[2] - bbox[0]
    draw.text(
        (cx - width / 2, y),
        str(text),
        font=font,
        fill=fill,
    )


def wrap_text(draw, text, font, max_width):
    words = str(text).split()

    lines = []
    current = ""

    for word in words:
        candidate = (
            word
            if not current
            else current + " " + word
        )

        bbox = draw.textbbox(
            (0, 0),
            candidate,
            font=font,
        )

        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def star_points(cx, cy, radius):
    points = []

    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5

        r = (
            radius
            if i % 2 == 0
            else radius * 0.45
        )

        points.append(
            (
                cx + math.cos(angle) * r,
                cy + math.sin(angle) * r,
            )
        )

    return points


def draw_star(draw, cx, cy, radius, fill):
    draw.polygon(
        star_points(cx, cy, radius),
        fill=fill,
    )


# ============================================================
# CHARACTER: BOBO
# ============================================================

def draw_bobo(
    draw,
    x,
    y,
    scale=1.0,
    bounce=0.0,
    wave=0.0,
):
    s = scale
    y += bounce

    fur = (156, 98, 58)
    fur_light = (181, 119, 72)
    dark = (105, 65, 40)
    muzzle = (218, 165, 111)
    yellow = (248, 207, 45)

    # Body
    draw.ellipse(
        [
            x - 64*s,
            y + 72*s,
            x + 64*s,
            y + 230*s,
        ],
        fill=fur,
    )

    # Ears
    draw.ellipse(
        [
            x - 68*s,
            y - 2*s,
            x - 5*s,
            y + 62*s,
        ],
        fill=fur,
    )

    draw.ellipse(
        [
            x + 5*s,
            y - 2*s,
            x + 68*s,
            y + 62*s,
        ],
        fill=fur,
    )

    draw.ellipse(
        [
            x - 55*s,
            y + 8*s,
            x - 18*s,
            y + 45*s,
        ],
        fill=fur_light,
    )

    draw.ellipse(
        [
            x + 18*s,
            y + 8*s,
            x + 55*s,
            y + 45*s,
        ],
        fill=fur_light,
    )

    # Head
    draw.ellipse(
        [
            x - 78*s,
            y + 15*s,
            x + 78*s,
            y + 155*s,
        ],
        fill=fur_light,
    )

    # Eyes
    eye_y = y + 76*s

    for eye_x in (-30, 30):
        draw.ellipse(
            [
                x + (eye_x - 9)*s,
                eye_y - 9*s,
                x + (eye_x + 9)*s,
                eye_y + 9*s,
            ],
            fill=(30, 30, 30),
        )

        draw.ellipse(
            [
                x + (eye_x - 4)*s,
                eye_y - 6*s,
                x + (eye_x + 1)*s,
                eye_y - 1*s,
            ],
            fill=(255, 255, 255),
        )

    # Muzzle
    draw.ellipse(
        [
            x - 32*s,
            y + 94*s,
            x + 32*s,
            y + 134*s,
        ],
        fill=muzzle,
    )

    # Nose
    draw.ellipse(
        [
            x - 10*s,
            y + 101*s,
            x + 10*s,
            y + 116*s,
        ],
        fill=dark,
    )

    # Smile
    draw.arc(
        [
            x - 20*s,
            y + 105*s,
            x + 20*s,
            y + 137*s,
        ],
        15,
        165,
        fill=dark,
        width=max(1, int(3*s)),
    )

    # Left arm
    draw.line(
        [
            (x - 52*s, y + 130*s),
            (x - 88*s, y + 145*s),
        ],
        fill=fur,
        width=max(10, int(30*s)),
    )

    # Right arm
    hand_x = (
        x
        + (80 + 18*math.sin(wave))*s
    )

    hand_y = (
        y
        + (110 - 30*math.cos(wave))*s
    )

    draw.line(
        [
            (x + 52*s, y + 130*s),
            (hand_x, hand_y),
        ],
        fill=fur,
        width=max(10, int(30*s)),
    )

    draw.ellipse(
        [
            hand_x - 19*s,
            hand_y - 19*s,
            hand_x + 19*s,
            hand_y + 19*s,
        ],
        fill=fur,
    )

    # Scarf
    draw.rectangle(
        [
            x - 66*s,
            y + 145*s,
            x + 66*s,
            y + 176*s,
        ],
        fill=yellow,
    )

    draw.polygon(
        [
            (x + 28*s, y + 168*s),
            (
                x + 80*s,
                y + (210 + 8*math.sin(wave))*s,
            ),
            (x + 55*s, y + 174*s),
        ],
        fill=yellow,
    )

    # Feet
    draw.ellipse(
        [
            x - 67*s,
            y + 205*s,
            x - 4*s,
            y + 248*s,
        ],
        fill=dark,
    )

    draw.ellipse(
        [
            x + 4*s,
            y + 205*s,
            x + 67*s,
            y + 248*s,
        ],
        fill=dark,
)


# ============================================================
# CHARACTER: MIMI
# ============================================================

def draw_mimi(
    draw,
    x,
    y,
    scale=1.0,
    bounce=0.0,
    wave=0.0,
):
    s = scale
    y += bounce

    white = (250, 250, 250)
    outline = (215, 215, 215)
    pink = (250, 165, 185)
    purple = (128, 78, 175)
    dark = (40, 40, 40)

    # Backpack
    rounded(
        draw,
        [
            x + 38*s,
            y + 112*s,
            x + 94*s,
            y + 193*s,
        ],
        int(15*s),
        purple,
    )

    # Ears
    draw.ellipse(
        [
            x - 58*s,
            y - 102*s,
            x - 5*s,
            y + 48*s,
        ],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    draw.ellipse(
        [
            x + 5*s,
            y - 102*s,
            x + 58*s,
            y + 48*s,
        ],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    draw.ellipse(
        [
            x - 43*s,
            y - 80*s,
            x - 19*s,
            y + 27*s,
        ],
        fill=pink,
    )

    draw.ellipse(
        [
            x + 19*s,
            y - 80*s,
            x + 43*s,
            y + 27*s,
        ],
        fill=pink,
    )

    # Body
    draw.ellipse(
        [
            x - 62*s,
            y + 88*s,
            x + 62*s,
            y + 238*s,
        ],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    # Head
    draw.ellipse(
        [
            x - 72*s,
            y - 2*s,
            x + 72*s,
            y + 140*s,
        ],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    # Eyes
    for eye_x in (-29, 29):
        draw.ellipse(
            [
                x + (eye_x - 8)*s,
                y + 57*s,
                x + (eye_x + 8)*s,
                y + 73*s,
            ],
            fill=dark,
        )

    # Nose
    draw.ellipse(
        [
            x - 9*s,
            y + 80*s,
            x + 9*s,
            y + 95*s,
        ],
        fill=pink,
    )

    # Smile
    draw.arc(
        [
            x - 19*s,
            y + 86*s,
            x + 19*s,
            y + 120*s,
        ],
        10,
        170,
        fill=dark,
        width=max(1, int(2*s)),
    )

    # Arms
    left_y = (
        y
        + (125 + 10*math.sin(wave))*s
    )

    right_y = (
        y
        + (125 - 10*math.sin(wave))*s
    )

    draw.line(
        [
            (x - 48*s, y + 130*s),
            (x - 85*s, left_y),
        ],
        fill=white,
        width=max(10, int(30*s)),
    )

    draw.line(
        [
            (x + 48*s, y + 130*s),
            (x + 85*s, right_y),
        ],
        fill=white,
        width=max(10, int(30*s)),
    )

    # Feet
    draw.ellipse(
        [
            x - 63*s,
            y + 215*s,
            x - 5*s,
            y + 250*s,
        ],
        fill=white,
        outline=outline,
    )

    draw.ellipse(
        [
            x + 5*s,
            y + 215*s,
            x + 63*s,
            y + 250*s,
        ],
        fill=white,
        outline=outline,
    )


# ============================================================
# CHARACTER: KIKI
# ============================================================

def draw_kiki(
    draw,
    x,
    y,
    scale=1.0,
    bounce=0.0,
    flap=0.0,
):
    s = scale
    y += bounce

    yellow = (252, 221, 50)
    yellow_light = (255, 231, 75)
    blue = (55, 145, 220)
    orange = (242, 132, 35)
    dark = (35, 35, 35)

    # Body
    draw.ellipse(
        [
            x - 60*s,
            y + 45*s,
            x + 60*s,
            y + 205*s,
        ],
        fill=yellow,
    )

    # Head
    draw.ellipse(
        [
            x - 70*s,
            y - 20*s,
            x + 70*s,
            y + 112*s,
        ],
        fill=yellow_light,
    )

    # Wings
    flap_amount = math.sin(flap)

    wing_y = (
        y
        + (105 - 35*flap_amount)*s
    )

    draw.ellipse(
        [
            x - 105*s,
            wing_y - 35*s,
            x - 28*s,
            wing_y + 55*s,
        ],
        fill=blue,
    )

    draw.ellipse(
        [
            x + 28*s,
            wing_y - 35*s,
            x + 105*s,
            wing_y + 55*s,
        ],
        fill=blue,
    )

    # Eyes
    for eye_x in (-29, 29):
        draw.ellipse(
            [
                x + (eye_x - 9)*s,
                y + 33*s,
                x + (eye_x + 9)*s,
                y + 51*s,
            ],
            fill=dark,
        )

    # Beak
    draw.polygon(
        [
            (x, y + 61*s),
            (x + 52*s, y + 77*s),
            (x, y + 94*s),
        ],
        fill=orange,
    )

    # Feet
    draw.ellipse(
        [
            x - 46*s,
            y + 183*s,
            x - 5*s,
            y + 210*s,
        ],
        fill=orange,
    )

    draw.ellipse(
        [
            x + 5*s,
            y + 183*s,
            x + 46*s,
            y + 210*s,
        ],
        fill=orange,
    )


# ============================================================
# BACKGROUND
# ============================================================

SKIES = [
    (188, 225, 250),
    (205, 238, 198),
    (252, 226, 177),
    (226, 213, 246),
]


def draw_cloud(draw, x, y, scale=1.0):
    s = scale

    white = (255, 255, 255)

    draw.ellipse(
        [
            x,
            y + 18*s,
            x + 100*s,
            y + 62*s,
        ],
        fill=white,
    )

    draw.ellipse(
        [
            x + 25*s,
            y,
            x + 88*s,
            y + 62*s,
        ],
        fill=white,
    )

    draw.ellipse(
        [
            x + 60*s,
            y + 12*s,
            x + 135*s,
            y + 64*s,
        ],
        fill=white,
    )


def draw_background(
    draw,
    scene_no,
    time_s,
    camera_x,
):
    sky = SKIES[
        (scene_no - 1) % len(SKIES)
    ]

    draw.rectangle(
        [0, 0, WIDTH, HEIGHT],
        fill=sky,
    )

    # Sun
    pulse = (
        1.0
        + 0.025 * math.sin(time_s * 1.2)
    )

    sun = 105 * pulse

    draw.ellipse(
        [
            1080 - sun/2,
            82 - sun/2,
            1080 + sun/2,
            82 + sun/2,
        ],
        fill=(255, 220, 78),
    )

    # Clouds
    for bx, by, scale in [
        (110, 105, 0.85),
        (410, 75, 1.05),
        (780, 125, 0.72),
    ]:
        x = (
            bx
            + time_s * 12 * scale
        ) % (WIDTH + 180) - 150

        draw_cloud(
            draw,
            x - camera_x * 0.05,
            by,
            scale,
        )

    # Hills
    offset = camera_x * 0.08

    draw.polygon(
        [
            (-100-offset, GROUND_Y),
            (180-offset, 350),
            (400-offset, GROUND_Y),
            (680-offset, 335),
            (950-offset, GROUND_Y),
            (1200-offset, 365),
            (1450-offset, GROUND_Y),
        ],
        fill=(155, 205, 145),
    )

    # Ground
    draw.rectangle(
        [0, GROUND_Y, WIDTH, HEIGHT],
        fill=(123, 190, 103),
    )

    # Grass
    for i in range(
        0,
        WIDTH + 50,
        35,
    ):
        sway = (
            5
            * math.sin(
                time_s * 2.2
                + i * 0.08
            )
        )

        x = (
            i
            - (camera_x * 0.18) % 35
        )

        draw.line(
            [
                (x, GROUND_Y + 22),
                (
                    x + sway,
                    GROUND_Y + 5,
                ),
            ],
            fill=(83, 158, 75),
            width=2,
        )

    # Flowers
    for i in range(9):
        fx = (
            70
            + i * 145
            - (camera_x * 0.25) % 145
        )

        fy = (
            GROUND_Y
            + 25
            + (i % 3) * 12
        )

        sway = (
            3
            * math.sin(
                time_s * 2 + i
            )
        )

        draw.line(
            [
                (fx, fy + 30),
                (fx + sway, fy),
            ],
            fill=(70, 140, 70),
            width=3,
        )

        flower_color = (
            (255, 210, 80)
            if i % 2 == 0
            else (245, 130, 160)
        )

        draw.ellipse(
            [
                fx - 8 + sway,
                fy - 8,
                fx + 8 + sway,
                fy + 8,
            ],
            fill=flower_color,
        )


# ============================================================
# STORY TEXT UNDERSTANDING
# ============================================================

def normalize(text):
    text = str(text or "").lower()

    text = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def contains_any(text, words):
    return any(
        word in text
        for word in words
    )


def detect_color(text):
    colors = {
        "red": (235, 70, 70),
        "blue": (70, 120, 235),
        "green": (70, 180, 100),
        "yellow": (250, 210, 50),
        "orange": (242, 145, 55),
        "purple": (145, 90, 190),
        "pink": (245, 125, 165),
    }

    for name, value in colors.items():
        if name in text:
            return name, value

    return "red", colors["red"]


def detect_action(text, scene_no):
    text = normalize(text)

    priority = [
        ("dance", ["dance", "dancing"]),
        ("fly", ["fly", "flies", "flying", "flies in"]),
        ("hop", ["hop", "hops", "hopping", "jump", "jumps"]),
        ("pick", ["pick", "picks", "picked", "pick up", "picks up"]),
        ("reach", ["reach", "reaches", "reaching"]),
        ("point", ["point", "points", "pointing"]),
        ("roll", ["roll", "rolls", "rolling"]),
        ("walk", ["walk", "walks", "walking", "enter"]),
        ("wave", ["wave", "waves", "waving"]),
        ("celebrate", ["celebrate", "celebrating", "celebration"]),
    ]

    for action, words in priority:
        if contains_any(text, words):
            return action

    defaults = {
        1: "walk",
        2: "hop",
        3: "fly",
        4: "dance",
    }

    return defaults.get(
        scene_no,
        "general",
    )


def detect_focus(text, action):
    text = normalize(text)

    if "kiki" in text:
        return "Kiki"

    if "mimi" in text:
        return "Mimi"

    if "bobo" in text:
        return "Bobo"

    if action in ("fly",):
        return "Kiki"

    if action in ("hop", "pick", "reach"):
        return "Mimi"

    if action in (
        "walk",
        "point",
        "roll",
    ):
        return "Bobo"

    return "group"


def detect_object(text):
    text = normalize(text)

    object_keywords = [
        "watermelon",
        "strawberry",
        "apple",
        "berry",
        "ball",
        "flower",
        "leaf",
        "basket",
        "circle",
        "square",
        "triangle",
        "star",
        "number",
        "numbers",
        "color",
        "colour",
        "shape",
        "big",
        "small",
        "large",
        "tiny",
    ]

    for obj in object_keywords:
        if obj in text:
            if obj in (
                "big",
                "small",
                "large",
                "tiny",
            ):
                continue

            if obj in (
                "number",
                "numbers",
            ):
                return "numbers"

            if obj in (
                "color",
                "colour",
            ):
                return "colors"

            if obj == "berry":
                return "berry"

            return obj

    return "learning stars"


def detect_camera(action):
    if action == "walk":
        return "track"

    if action == "fly":
        return "follow"

    if action in (
        "point",
        "pick",
        "reach",
    ):
        return "focus"

    if action in (
        "dance",
        "celebrate",
    ):
        return "wide"

    return "gentle"


def build_scene_plan(story, scene_no):
    scenes = story.get(
        "scenes",
        [],
    )

    if scene_no < 1 or scene_no > len(scenes):
        raise ValueError(
            f"Invalid scene number: {scene_no}"
        )

    scene = scenes[scene_no - 1]

    description = str(
        scene.get(
            "visual_description",
            "",
        )
    )

    narration = str(
        scene.get(
            "narration",
            "",
        )
    )

    combined = (
        description
        + " "
        + narration
    )

    action = detect_action(
        combined,
        scene_no,
    )

    focus = detect_focus(
        combined,
        action,
    )

    object_name = detect_object(
        combined,
    )

    color_name, color = detect_color(
        combined,
    )

    return {
        "scene_number": scene_no,
        "visual_description": description,
        "narration": narration,
        "action": action,
        "focus": focus,
        "object": object_name,
        "object_name": object_name,
        "color_name": color_name,
        "color": color,
        "camera": detect_camera(action),
    }


# ============================================================
# EDUCATIONAL OBJECTS
# ============================================================

def draw_ball(
    draw,
    cx,
    cy,
    radius,
    color,
    rotation=0,
):
    draw.ellipse(
        [
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
        ],
        fill=color,
        outline=(255, 255, 255),
        width=4,
    )

    # Highlight
    draw.ellipse(
        [
            cx - radius * 0.45,
            cy - radius * 0.55,
            cx - radius * 0.15,
            cy - radius * 0.25,
        ],
        fill=(255, 255, 255),
    )

    # Moving seam
    draw.arc(
        [
            cx - radius * 0.65,
            cy - radius * 0.65,
            cx + radius * 0.65,
            cy + radius * 0.65,
        ],
        int(rotation) % 360,
        int(rotation) % 360 + 120,
        fill=(255, 255, 255),
        width=3,
    )


def draw_flower_object(
    draw,
    cx,
    cy,
    scale,
    color,
):
    s = scale

    for i in range(6):
        angle = (
            i * math.pi / 3
        )

        px = (
            cx
            + math.cos(angle)
            * 45 * s
        )

        py = (
            cy
            + math.sin(angle)
            * 45 * s
        )

        draw.ellipse(
            [
                px - 28*s,
                py - 28*s,
                px + 28*s,
                py + 28*s,
            ],
            fill=color,
        )

    draw.ellipse(
        [
            cx - 28*s,
            cy - 28*s,
            cx + 28*s,
            cy + 28*s,
        ],
        fill=(255, 215, 60),
    )

    draw.line(
        [
            (cx, cy + 28*s),
            (cx, cy + 110*s),
        ],
        fill=(70, 145, 70),
        width=max(2, int(7*s)),
    )


def draw_basket(
    draw,
    cx,
    cy,
    width,
    height,
    label,
):
    # Basket body
    rounded(
        draw,
        [
            cx - width/2,
            cy,
            cx + width/2,
            cy + height,
        ],
        18,
        fill=(181, 125, 65),
        outline=(125, 80, 40),
        width=4,
    )

    # Handle
    draw.arc(
        [
            cx - width * 0.35,
            cy - height * 0.65,
            cx + width * 0.35,
            cy + height * 0.35,
        ],
        180,
        360,
        fill=(125, 80, 40),
        width=9,
    )

    draw_center(
        draw,
        label,
        cx,
        cy + height/2 - 16,
        OBJECT_FONT,
        (255, 240, 210),
    )


def draw_object(
    draw,
    plan,
    t,
    anchor,
):
    obj = plan["object"]
    color = plan["color"]

    cx, cy = anchor

    action = plan["action"]

    bob = (
        8
        * math.sin(
            t * math.pi * 2
        )
    )

    rotation = (
        t * 360
    )

    # Big/small learning object
    if obj in (
        "big",
        "small",
        "learning stars",
    ):
        # Two objects are useful for size lessons.
        big_y = cy - 20 + bob
        small_y = cy + 50 + bob

        draw.ellipse(
            [
                540,
                big_y - 85,
                710,
                big_y + 85,
            ],
            fill=(90, 175, 90),
            outline=(255, 255, 255),
            width=4,
        )

        draw.ellipse(
            [
                765,
                small_y - 32,
                829,
                small_y + 32,
            ],
            fill=(235, 70, 70),
            outline=(255, 255, 255),
            width=4,
        )

        draw_center(
            draw,
            "BIG",
            625,
            big_y - 18,
            OBJECT_FONT,
            (255, 255, 255),
        )

        draw_center(
            draw,
            "SMALL",
            797,
            small_y - 15,
            SMALL_FONT,
            (255, 255, 255),
        )

        return

    if obj in (
        "ball",
        "circle",
    ):
        radius = (
            62
            if obj == "ball"
            else 72
        )

        draw_ball(
            draw,
            cx,
            cy + bob,
            radius,
            color,
            rotation,
        )

        if obj == "circle":
            draw_center(
                draw,
                "CIRCLE",
                cx,
                cy - 15 + bob,
                OBJECT_FONT,
                (255, 255, 255),
            )

        return

    if obj == "flower":
        draw_flower_object(
            draw,
            cx,
            cy + bob,
            1.0,
            color,
        )
        return

    if obj == "leaf":
        draw.ellipse(
            [
                cx - 90,
                cy - 40 + bob,
                cx + 90,
                cy + 40 + bob,
            ],
            fill=(80, 175, 90),
        )

        draw.line(
            [
                (cx - 80, cy + 25 + bob),
                (cx + 80, cy - 25 + bob),
            ],
            fill=(50, 125, 65),
            width=5,
        )
        return

    if obj == "square":
        size = 75

        draw.rectangle(
            [
                cx - size,
                cy - size + bob,
                cx + size,
                cy + size + bob,
            ],
            fill=color,
            outline=(255, 255, 255),
            width=5,
        )
        return

    if obj == "triangle":
        draw.polygon(
            [
                (cx, cy - 100 + bob),
                (cx - 110, cy + 85 + bob),
                (cx + 110, cy + 85 + bob),
            ],
            fill=color,
            outline=(255, 255, 255),
        )
        return

    if obj == "star":
        draw_star(
            draw,
            cx,
            cy + bob,
            80,
            color,
        )
        return

    if obj == "numbers":
        for i in range(3):
            nx = (
                cx
                - 145
                + i * 145
            )

            ny = (
                cy
                + 15
                * math.sin(
                    t * math.pi * 2
                    + i
                )
            )

            draw.ellipse(
                [
                    nx - 48,
                    ny - 48,
                    nx + 48,
                    ny + 48,
                ],
                fill=(245, 180, 70),
            )

            draw_center(
                draw,
                str(i + 1),
                nx,
                ny - 23,
                OBJECT_FONT,
                (70, 70, 90),
            )

        return

    if obj == "basket":
        draw_basket(
            draw,
            cx,
            cy - 20,
            180,
            105,
            "BASKET",
        )
        return

    if obj in (
        "apple",
        "berry",
        "strawberry",
        "watermelon",
    ):
        # Generic fruit shape.
        radius = 65

        if obj == "watermelon":
            radius = 90

        draw.ellipse(
            [
                cx - radius,
                cy - radius + bob,
                cx + radius,
                cy + radius + bob,
            ],
            fill=color,
            outline=(255, 255, 255),
            width=4,
        )

        if obj == "watermelon":
            for offset in (-30, 0, 30):
                draw.arc(
                    [
                        cx - radius + offset,
                        cy - radius + bob,
                        cx + radius + offset,
                        cy + radius + bob,
                    ],
                    250,
                    290,
                    fill=(50, 120, 65),
                    width=5,
                )

        if obj == "strawberry":
            draw.polygon(
                [
                    (cx, cy + 80 + bob),
                    (cx - 60, cy - 30 + bob),
                    (cx + 60, cy - 30 + bob),
                ],
                fill=color,
            )

        draw_center(
            draw,
            obj.upper(),
            cx,
            cy - 15 + bob,
            SMALL_FONT,
            (255, 255, 255),
        )

        return

    # Generic learning stars.
    for i in range(5):
        sx = (
            430
            + i * 105
        )

        sy = (
            cy
            + 14
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
    anchor,
):
    action = plan["action"]

    x, y = anchor

    # Walking
    if action == "walk":
        for i in range(3):
            px = (
                250
                + i * 30
                + t * 100
            )

            draw.ellipse(
                [
                    px,
                    485,
                    px + 8,
                    493,
                ],
                fill=(255, 255, 255),
            )

    # Hopping
    if action == "hop":
        for i in range(3):
            px = (
                x - 45
                + i * 45
            )

            draw.arc(
                [
                    px - 12,
                    480,
                    px + 12,
                    496,
                ],
                200,
                340,
                fill=(90, 130, 80),
                width=3,
            )

    # Flying
    if action == "fly":
        for i in range(5):
            yy = (
                y - 50
                + i * 20
            )

            length = (
                30
                + 18
                * math.sin(
                    t * 8 + i
                )
            )

            draw.line(
                [
                    (
                        x - 115,
                        yy,
                    ),
                    (
                        x - 115 - length,
                        yy,
                    ),
                ],
                fill=(255, 255, 255),
                width=3,
            )

    # Pointing
    if action == "point":
        pulse = (
            1
            + 0.15
            * math.sin(
                t * math.pi * 8
            )
        )

        radius = 48 * pulse

        draw.ellipse(
            [
                x - radius,
                y - radius,
                x + radius,
                y + radius,
            ],
            outline=(255, 245, 150),
            width=3,
        )

    # Reach/pick
    if action in (
        "reach",
        "pick",
    ):
        for i in range(6):
            angle = (
                t * 2
                + i * math.pi / 3
            )

            radius = (
                65
                + 8
                * math.sin(
                    t * 6 + i
                )
            )

            px = (
                x
                + math.cos(angle)
                * radius
            )

            py = (
                y
                + math.sin(angle)
                * radius
            )

            draw_star(
                draw,
                px,
                py,
                7,
                (255, 220, 80),
            )

    # Rolling
    if action == "roll":
        for i in range(4):
            yy = (
                y + 25 + i * 12
            )

            draw.line(
                [
                    (
                        x - 80 - i * 15,
                        yy,
                    ),
                    (
                        x - 25,
                        yy,
                    ),
                ],
                fill=(120, 140, 150),
                width=3,
            )

    # Dance
    if action in (
        "dance",
        "celebrate",
    ):
        for i in range(12):
            angle = (
                i * 0.55
                + t * 2
            )

            radius = (
                120
                + 30
                * math.sin(
                    t * 2 + i
                )
            )

            px = (
                WIDTH / 2
                + math.cos(angle)
                * radius
            )

            py = (
                310
                + math.sin(angle)
                * 110
            )

            draw_star(
                draw,
                px,
                py,
                5 + i % 3,
                (255, 220, 75),
        )


# ============================================================
# CHARACTER POSITIONS
# ============================================================

def get_character_positions(
    scene_no,
    t,
    plan,
):
    p = ease_in_out(t)

    bobo = [360, 285]
    mimi = [650, 285]
    kiki = [930, 255]

    action = plan["action"]
    focus = plan["focus"]

    if scene_no == 1:
        # Bobo enters.
        bobo[0] = lerp(
            -170,
            360,
            ease_in_out(
                clamp(t / 0.55, 0, 1)
            ),
        )

        bobo[1] += (
            8
            * math.sin(
                t * math.pi * 10
            )
        )

        mimi[0] = (
            620
            + 25
            * math.sin(
                t * math.pi * 2
            )
        )

        mimi[1] += (
            -12
            * max(
                0,
                math.sin(
                    t * math.pi * 4
                ),
            )
        )

        kiki[0] = (
            940
            + 45
            * math.sin(
                t * math.pi * 1.5
            )
        )

        kiki[1] = (
            250
            + 30
            * math.sin(
                t * math.pi * 3
            )
        )

    elif scene_no == 2:
        # Mimi becomes lead.
        bobo[0] = lerp(
            300,
            455,
            p,
        )

        mimi[0] = lerp(
            820,
            690,
            p,
        )

        mimi[1] += (
            -25
            * max(
                0,
                math.sin(
                    t * math.pi * 5
                ),
            )
        )

        kiki[0] = lerp(
            1020,
            860,
            p,
        )

        kiki[1] = (
            245
            + 25
            * math.sin(
                t * math.pi * 3
            )
        )

    elif scene_no == 3:
        # Kiki flies around.
        bobo[0] = (
            380
            + 25
            * math.sin(
                t * math.pi * 2
            )
        )

        mimi[0] = lerp(
            520,
            690,
            p,
        )

        mimi[1] += (
            -15
            * max(
                0,
                math.sin(
                    t * math.pi * 5
                ),
            )
        )

        kiki[0] = lerp(
            1040,
            790,
            p,
        )

        kiki[1] = (
            190
            + 115
            * math.sin(
                t * math.pi * 2
            )
        )

    else:
        # Finale.
        bobo[0] = lerp(
            350,
            455,
            p,
        )

        mimi[0] = lerp(
            650,
            640,
            p,
        )

        kiki[0] = lerp(
            950,
            825,
            p,
        )

        bobo[1] += (
            10
            * math.sin(
                t * math.pi * 7
            )
        )

        mimi[1] += (
            -18
            * max(
                0,
                math.sin(
                    t * math.pi * 6
                ),
            )
        )

        kiki[1] += (
            20
            * math.sin(
                t * math.pi * 5
            )
        )

    # Action-specific staging
    if action == "fly":
        kiki[1] -= 40

    if action == "hop":
        mimi[1] -= 20

    if action == "walk" and focus == "Bobo":
        bobo[0] += 20 * p

    return {
        "Bobo": tuple(bobo),
        "Mimi": tuple(mimi),
        "Kiki": tuple(kiki),
    }


# ============================================================
# OBJECT ANCHOR
# ============================================================

def scene_object_anchor(
    scene_no,
    plan,
    t,
):
    if scene_no == 1:
        return (
            700
            + 35
            * math.sin(
                t * math.pi * 2
            ),
            405,
        )

    if scene_no == 2:
        return (
            650,
            405
            - 12
            * math.sin(
                t * math.pi * 2
            ),
        )

    if scene_no == 3:
        return (
            730,
            405,
        )

    return (
        650,
        405,
    )


# ============================================================
# ACTION CAPTION
# ============================================================

def draw_action_caption(
    draw,
    plan,
    t,
):
    labels = {
        "walk": "GO!",
        "hop": "HOP!",
        "fly": "FLY!",
        "point": "LOOK!",
        "reach": "REACH!",
        "pick": "PICK!",
        "roll": "ROLL!",
        "dance": "DANCE!",
        "celebrate": "YAY!",
    }

    label = labels.get(
        plan["action"]
    )

    if not label:
        return

    if math.sin(
        t * math.pi * 8
    ) < -0.25:
        return

    draw_center(
        draw,
        label,
        WIDTH / 2,
        95,
        SMALL_FONT,
        (70, 85, 100),
            )


# ============================================================
# SPARKLES
# ============================================================

def draw_sparkles(
    draw,
    t,
    scene_no,
):
    for i in range(12):
        phase = (
            i * 0.73
            + scene_no
        )

        x = (
            80
            + (i * 103) % 1120
        )

        y = (
            160
            + (i * 67) % 270
        )

        twinkle = (
            0.5
            + 0.5
            * math.sin(
                t * 3
                + phase
            )
        )

        if twinkle > 0.65:
            radius = (
                3
                + 4 * twinkle
            )

            draw.ellipse(
                [
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                ],
                fill=(255, 255, 245),
            )


# ============================================================
# LESSON CARD
# ============================================================

def draw_lesson_card(
    image,
    lesson,
    t,
):
    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        overlay
    )

    alpha = int(
        205
        * clamp(
            (t - 0.10) / 0.55,
            0,
            1,
        )
    )

    rounded(
        draw,
        [
            55,
            575,
            WIDTH - 55,
            692,
        ],
        22,
        fill=(
            255,
            255,
            255,
            alpha,
        ),
        outline=(
            80,
            100,
            120,
            alpha,
        ),
        width=2,
    )

    lines = wrap_text(
        draw,
        "Lesson: " + str(lesson),
        LESSON_FONT,
        WIDTH - 165,
    )

    y = 589

    for line in lines[:3]:
        bbox = draw.textbbox(
            (0, 0),
            line,
            font=LESSON_FONT,
        )

        x = (
            WIDTH
            - (bbox[2] - bbox[0])
        ) / 2

        draw.text(
            (x, y),
            line,
            font=LESSON_FONT,
            fill=(
                40,
                50,
                65,
                alpha,
            ),
        )

        y += 27

    return alpha_layer(
        image,
        overlay,
    )


# ============================================================
# SCENE TRANSITION
# ============================================================

def draw_scene_transition_overlay(
    image,
    t,
):
    fade_seconds = 0.55

    fade = clamp(
        t / fade_seconds,
        0,
        1,
    )

    alpha = int(
        255
        * (
            1
            - ease_in_out(fade)
        )
    )

    if alpha <= 0:
        return image

    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (
            0,
            0,
            0,
            alpha,
        ),
    )

    return alpha_layer(
        image,
        overlay,
    )


# ============================================================
# FRAME RENDER
# ============================================================

def render_frame(
    story,
    scene_no,
    local_t,
    scene_duration,
    total_duration,
):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (255, 255, 255),
    )

    draw = ImageDraw.Draw(
        image
    )

    plan = build_scene_plan(
        story,
        scene_no,
    )

    t = clamp(
        local_t
        / max(
            scene_duration,
            0.001,
        ),
        0,
        1,
    )

    # Camera
    camera_style = plan["camera"]

    if camera_style == "track":
        camera_x = lerp(
            -25,
            35,
            ease_in_out(t),
        )

    elif camera_style == "follow":
        camera_x = (
            35
            * math.sin(
                t * math.pi * 1.2
            )
        )

    elif camera_style == "focus":
        camera_x = (
            -18
            * math.sin(
                t * math.pi
            )
        )

    elif camera_style == "wide":
        camera_x = (
            12
            * math.sin(
                t * math.pi
            )
        )

    else:
        camera_x = (
            18
            * math.sin(
                t * math.pi * 1.2
            )
        )

    # Background
    draw_background(
        draw,
        scene_no,
        local_t,
        camera_x,
    )

    # Foreground depth
    for i in range(12):
        x = (
            i * 121
            + 30
            - camera_x * 0.25
        ) % WIDTH

        y = (
            GROUND_Y
            + 18
            + (i % 3) * 13
        )

        draw.ellipse(
            [
                x - 4,
                y - 4,
                x + 4,
                y + 4,
            ],
            fill=(95, 165, 85),
        )

    # Title
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

    draw_center(
        draw,
        title,
        WIDTH / 2,
        18,
        TITLE_FONT,
        (55, 70, 90),
    )

    draw_center(
        draw,
        f"Scene {scene_no} of 4",
        WIDTH / 2,
        58,
        SCENE_FONT,
        (70, 90, 105),
    )

    draw_action_caption(
        draw,
        plan,
        t,
    )

    # Main educational object
    object_xy = scene_object_anchor(
        scene_no,
        plan,
        t,
    )

    draw_object(
        draw,
        plan,
        t,
        object_xy,
    )

    # Action effects
    draw_action_effects(
        draw,
        plan,
        t,
        object_xy,
    )

    # Characters
    positions = get_character_positions(
        scene_no,
        t,
        plan,
    )

    bobo_x, bobo_y = positions["Bobo"]
    mimi_x, mimi_y = positions["Mimi"]
    kiki_x, kiki_y = positions["Kiki"]

    action = plan["action"]
    focus = plan["focus"]

    # Secondary movement
    bobo_bounce = (
        6
        * math.sin(
            local_t * 7
        )
    )

    mimi_bounce = (
        -8
        * max(
            0,
            math.sin(
                local_t * 4.2
            ),
        )
    )

    kiki_float = (
        10
        * math.sin(
            local_t * 2.8
        )
    )

    if action == "hop":
        mimi_bounce = (
            -35
            * max(
                0,
                math.sin(
                    local_t * 6.5
                ),
            )
        )

    if action == "fly":
        kiki_float = (
            25
            * math.sin(
                local_t * 5.5
            )
        )

    # Waving
    bobo_wave = (
        local_t
        * (
            4.2
            if (
                focus == "Bobo"
                or action
                in (
                    "dance",
                    "celebrate",
                    "wave",
                )
            )
            else 1.0
        )
    )

    mimi_wave = (
        local_t
        * (
            4.0
            if (
                focus == "Mimi"
                or action
                in (
                    "dance",
                    "celebrate",
                    "wave",
                )
            )
            else 1.1
        )
    )

    kiki_flap = (
        local_t
        * (
            11
            if action == "fly"
            else 7
        )
    )

    # Draw Bobo
    draw_bobo(
        draw,
        bobo_x
        - camera_x * 0.30,
        bobo_y,
        scale=1.08,
        bounce=bobo_bounce,
        wave=bobo_wave,
    )

    # Draw Mimi
    draw_mimi(
        draw,
        mimi_x
        - camera_x * 0.35,
        mimi_y,
        scale=1.04,
        bounce=mimi_bounce,
        wave=mimi_wave,
    )

    # Draw Kiki
    draw_kiki(
        draw,
        kiki_x
        - camera_x * 0.42,
        kiki_y,
        scale=0.92,
        bounce=kiki_float,
        flap=kiki_flap,
    )

    # Lesson card
    image = draw_lesson_card(
        image,
        story.get(
            "lesson",
            "",
        ),
        t,
    )

    # Transition
    image = draw_scene_transition_overlay(
        image,
        t,
    )

    return image


# ============================================================
# AUDIO
# ============================================================

def get_audio_duration():
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(AUDIO_FILE),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    value = result.stdout.strip()

    if not value:
        raise RuntimeError(
            "Could not determine narration duration."
        )

    return float(value)


# ============================================================
# SUBTITLE TIMESTAMP
# ============================================================

def format_timestamp(seconds):
    total_seconds = int(seconds)

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
        total_seconds % 3600
        // 60
    )

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
    duration,
):
    segments = []

    for i, scene in enumerate(
        story.get(
            "scenes",
            [],
        ),
        1,
    ):
        text = str(
            scene.get(
                "narration",
                "",
            )
        ).strip()

        if text:
            segments.append(
                {
                    "label": f"Scene {i}",
                    "text": text,
                }
            )

    song = story.get(
        "song",
        {},
    )

    if isinstance(song, dict):
        lyrics = str(
            song.get(
                "lyrics",
                "",
            )
        ).strip()

        if lyrics:
            segments.append(
                {
                    "label": "Song",
                    "text": lyrics,
                }
            )

    ending = str(
        story.get(
            "ending",
            "",
        )
    ).strip()

    if ending:
        segments.append(
            {
                "label": "Ending",
                "text": ending,
            }
        )

    if not segments:
        raise RuntimeError(
            "No spoken text found for subtitles."
        )

    total_words = sum(
        max(
            1,
            len(
                segment["text"].split()
            ),
        )
        for segment in segments
    )

    cursor = 0.0
    cues = []

    for segment in segments:
        words = segment["text"].split()

        count = max(
            1,
            len(words),
        )

        segment_duration = (
            duration
            * count
            / total_words
        )

        start = cursor

        end = min(
            duration,
            cursor + segment_duration,
        )

        cursor = end

        chunk_size = 6

        chunks = [
            words[i:i + chunk_size]
            for i in range(
                0,
                len(words),
                chunk_size,
            )
        ]

        chunk_words = sum(
            len(chunk)
            for chunk in chunks
        )

        local_cursor = start

        for chunk in chunks:
            chunk_duration = (
                (end - start)
                * len(chunk)
                / max(
                    1,
                    chunk_words,
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

        for index, (
            start,
            end,
            caption,
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
# VALIDATION
# ============================================================

def validate_story(story):
    if not isinstance(
        story,
        dict,
    ):
        raise ValueError(
            "story.json is not a JSON object."
        )

    scenes = story.get(
        "scenes"
    )

    if not isinstance(
        scenes,
        list,
    ):
        raise ValueError(
            "story.json does not contain scenes."
        )

    if len(scenes) != 4:
        raise ValueError(
            "NobiNest requires exactly 4 scenes."
        )

    for i, scene in enumerate(
        scenes,
        1,
    ):
        if not isinstance(
            scene,
            dict,
        ):
            raise ValueError(
                f"Scene {i} is invalid."
            )

        if not scene.get(
            "visual_description"
        ):
            raise ValueError(
                f"Scene {i} is missing visual_description."
            )

        if not scene.get(
            "narration"
        ):
            raise ValueError(
                f"Scene {i} is missing narration."
            )


# ============================================================
# FFmpeg PATH ESCAPING
# ============================================================

def ffmpeg_filter_path(path):
    value = str(path).replace(
        "\\",
        "/",
    )

    value = value.replace(
        ":",
        "\\:",
    )

    value = value.replace(
        "'",
        "\\'",
    )

    return value


# ============================================================
# VIDEO RENDER
# ============================================================

def render_video(
    story,
    audio_duration,
):
    # IMPORTANT:
    # If narration is 59.47 seconds, we still create
    # a 60-second MP4 with silence after narration.
    target_duration = max(
        MIN_DURATION,
        audio_duration,
    )

    if target_duration > MAX_DURATION:
        raise RuntimeError(
            f"Audio is {audio_duration:.2f}s, "
            f"which exceeds the maximum "
            f"{MAX_DURATION:.0f}s."
        )

    print("")
    print("=" * 55)
    print(
        "NOBINEST SCENE-AWARE "
        "2D MOTION RENDERER V3"
    )
    print("=" * 55)

    print(
        f"Resolution: "
        f"{WIDTH}x{HEIGHT}"
    )

    print(
        f"Frame rate: "
        f"{FPS}"
    )

    print(
        f"Narration duration: "
        f"{audio_duration:.2f}s"
    )

    print(
        f"Final video target: "
        f"{target_duration:.2f}s"
    )

    print("")

    # Print parsed scenes.
    for i in range(1, 5):
        plan = build_scene_plan(
            story,
            i,
        )

        print(
            f"Scene {i}: "
            f"object={plan['object_name']}, "
            f"action={plan['action']}, "
            f"focus={plan['focus']}"
        )

        print(
            "  visual_description: "
            + plan[
                "visual_description"
            ]
        )

    subtitle_path = ffmpeg_filter_path(
        SRT_FILE
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

    command = [
        "ffmpeg",
        "-y",

        # Raw animation frames
        "-f",
        "rawvideo",

        "-vcodec",
        "rawvideo",

        "-pix_fmt",
        "rgb24",

        "-s",
        f"{WIDTH}x{HEIGHT}",

        "-r",
        str(FPS),

        "-i",
        "-",

        # Audio
        "-i",
        str(AUDIO_FILE),

        # Video subtitles
        "-vf",
        subtitle_filter,

        # Video codec
        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "22",

        "-pix_fmt",
        "yuv420p",

        # Audio codec
        "-c:a",
        "aac",

        "-b:a",
        "128k",

        # Add silence if audio is shorter than 60 sec.
        "-af",
        "apad",

        # Force final minimum duration.
        "-t",
        f"{target_duration:.3f}",

        # Prevent old output issues.
        "-movflags",
        "+faststart",

        str(VIDEO_FILE),
    ]

    print("")
    print("Starting FFmpeg...")
    print("")

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
                target_duration
                * FPS
            )
        ),
    )

    last_scene = None

    try:
        for frame_index in range(
            total_frames
        ):
            current_time = (
                frame_index
                / FPS
            )

            scene_no = min(
                4,
                int(
                    (
                        current_time
                        / target_duration
                    )
                    * 4
                )
                + 1,
            )

            scene_duration = (
                target_duration
                / 4.0
            )

            local_t = (
                current_time
                - (
                    scene_no - 1
                )
                * scene_duration
            )

            local_t = clamp(
                local_t,
                0,
                scene_duration,
            )

            if scene_no != last_scene:
                print(
                    f"Animating "
                    f"scene {scene_no}/4..."
                )

                last_scene = scene_no

            frame = render_frame(
                story,
                scene_no,
                local_t,
                scene_duration,
                target_duration,
            )

            process.stdin.write(
                frame.tobytes()
            )

            if (
                frame_index % FPS
                == 0
            ):
                percent = (
                    frame_index
                    / total_frames
                    * 100
                )

                print(
                    f"Rendered "
                    f"{current_time:6.1f}s / "
                    f"{target_duration:6.1f}s "
                    f"({percent:5.1f}%)"
                )

        process.stdin.close()

        stderr = (
            process.stderr.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        return_code = (
            process.wait()
        )

        if return_code != 0:
            print(stderr)

            raise RuntimeError(
                "FFmpeg failed with "
                f"exit code {return_code}"
            )

    except BrokenPipeError:
        stderr = (
            process.stderr.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        process.wait()

        print(stderr)

        raise RuntimeError(
            "FFmpeg closed the video "
            "pipe unexpectedly."
        )


# ============================================================
# VERIFY FINAL VIDEO
# ============================================================

def verify_video():
    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "Renderer finished but MP4 "
            "was not created."
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(VIDEO_FILE),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    duration = float(
        result.stdout.strip()
    )

    print("")
    print(
        f"Final MP4 duration: "
        f"{duration:.2f}s"
    )

    if duration < MIN_DURATION:
        raise RuntimeError(
            f"Final video is only "
            f"{duration:.2f}s. "
            f"Minimum is "
            f"{MIN_DURATION:.0f}s."
        )

    if duration > MAX_DURATION:
        raise RuntimeError(
            f"Final video is "
            f"{duration:.2f}s. "
            f"Maximum is "
            f"{MAX_DURATION:.0f}s."
        )

    return duration


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 55)
    print(
        "NOBINEST KIDS "
        "SCENE-AWARE VIDEO RENDERER V3"
    )
    print("=" * 55)

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

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        STORY_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        story = json.load(file)

    validate_story(
        story
    )

    audio_duration = (
        get_audio_duration()
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
        f"Audio duration: "
        f"{audio_duration:.2f}s"
    )

    print("")
    print(
        "Reading AI visual descriptions..."
    )

    for i in range(1, 5):
        plan = build_scene_plan(
            story,
            i,
        )

        print(
            f"Scene {i}: "
            f"{plan['object_name']} | "
            f"{plan['action']} | "
            f"focus={plan['focus']}"
        )

    print("")
    print(
        "Creating subtitles..."
    )

    subtitle_duration = max(
        MIN_DURATION,
        audio_duration,
    )

    create_subtitles(
        story,
        subtitle_duration,
    )

    print(
        "Rendering scene-specific animation..."
    )

    render_video(
        story,
        audio_duration,
    )

    final_duration = (
        verify_video()
    )

    size_mb = (
        VIDEO_FILE.stat().st_size
        / (1024 * 1024)
    )

    print("")
    print("=" * 55)
    print(
        "NOBINEST EPISODE CREATED "
        "SUCCESSFULLY"
    )
    print("=" * 55)

    print(
        f"Video: "
        f"{VIDEO_FILE}"
    )

    print(
        f"Size: "
        f"{size_mb:.2f} MB"
    )

    print(
        f"Duration: "
        f"{final_duration:.2f}s"
    )

    print(
        f"Subtitles: "
        f"{SRT_FILE}"
    )

    print("")
    print(
        "Scene-aware animation enabled:"
    )

    print(
        "  visual_description parsing"
    )

    print(
        "  scene-specific choreography"
    )

    print(
        "  walking"
    )

    print(
        "  hopping"
    )

    print(
        "  flying"
    )

    print(
        "  pointing"
    )

    print(
        "  reaching"
    )

    print(
        "  picking"
    )

    print(
        "  dancing"
    )

    print(
        "  waving"
    )

    print(
        "  animated objects"
    )

    print(
        "  moving clouds"
    )

    print(
        "  swaying grass"
    )

    print(
        "  flowers"
    )

    print(
        "  particles"
    )

    print(
        "  camera movement"
    )

    print(
        "  scene transitions"
    )

    print(
        "  animated subtitles"
    )

    print(
        "  automatic 60-second minimum"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as exc:
        print("")
        print("=" * 55)
        print("RENDERER ERROR")
        print("=" * 55)
        print(str(exc))
        print("=" * 55)

        sys.exit(1)
