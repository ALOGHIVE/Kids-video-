import json
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NOBINEST 2D MOTION VIDEO RENDERER
# ============================================================
# Free, procedural 2D animation renderer.
#
# It does NOT create a slideshow.
# Every frame is drawn independently so characters, camera,
# clouds, flowers, particles and educational objects can move.
#
# Input:
#   output/story.json
#   output/narration.mp3
#
# Output:
#   output/nobinnest_episode.mp4
#   output/narration.srt
# ============================================================


OUTPUT_DIR = Path("output")
STORY_FILE = OUTPUT_DIR / "story.json"
AUDIO_FILE = OUTPUT_DIR / "narration.mp3"
VIDEO_FILE = OUTPUT_DIR / "nobinnest_episode.mp4"
SRT_FILE = OUTPUT_DIR / "narration.srt"

WIDTH = 1280
HEIGHT = 720
FPS = 24

# Internal animation canvas.
# Rendering at 1280x720 keeps GitHub Actions reasonably fast.
BG_GROUND_Y = 525


# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=False):
    candidates = []

    if bold:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ])
    else:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ])

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


TITLE_FONT = get_font(38, True)
LESSON_FONT = get_font(22, True)
SUBTITLE_FONT = get_font(25, True)
SMALL_FONT = get_font(20, False)


# ============================================================
# HELPERS
# ============================================================

def clamp(value, low, high):
    return max(low, min(high, value))


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def alpha_composite(base, overlay):
    return Image.alpha_composite(base.convert("RGBA"), overlay.convert("RGBA")).convert("RGB")


def draw_text_center(draw, text, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(draw, text, font, max_width):
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else current + " " + word
        bbox = draw.textbbox((0, 0), candidate, font=font)

        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


# ============================================================
# CHARACTER DRAWING
# ============================================================

def draw_bobo(draw, x, y, scale=1.0, bounce=0.0, arm_wave=0.0):
    """
    Bobo:
    small friendly brown bear, fluffy brown fur,
    round face, small ears, expressive eyes,
    short limbs and bright yellow scarf.
    """

    s = scale
    y += bounce

    fur = (156, 98, 58)
    fur_light = (181, 119, 72)
    dark = (105, 65, 40)
    muzzle = (218, 165, 111)
    yellow = (248, 207, 45)

    # Body
    draw.ellipse(
        [x - 64*s, y + 72*s, x + 64*s, y + 230*s],
        fill=fur,
    )

    # Ears
    draw.ellipse(
        [x - 68*s, y - 2*s, x - 5*s, y + 62*s],
        fill=fur,
    )
    draw.ellipse(
        [x + 5*s, y - 2*s, x + 68*s, y + 62*s],
        fill=fur,
    )

    draw.ellipse(
        [x - 55*s, y + 8*s, x - 18*s, y + 45*s],
        fill=fur_light,
    )
    draw.ellipse(
        [x + 18*s, y + 8*s, x + 55*s, y + 45*s],
        fill=fur_light,
    )

    # Head
    draw.ellipse(
        [x - 78*s, y + 15*s, x + 78*s, y + 155*s],
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
            fill="white",
        )

    # Muzzle and nose
    draw.ellipse(
        [x - 32*s, y + 94*s, x + 32*s, y + 134*s],
        fill=muzzle,
    )
    draw.ellipse(
        [x - 10*s, y + 101*s, x + 10*s, y + 116*s],
        fill=dark,
    )

    # Smile
    draw.arc(
        [x - 20*s, y + 105*s, x + 20*s, y + 137*s],
        15,
        165,
        fill=dark,
        width=max(1, int(3*s)),
    )

    # Arms. Right arm waves.
    wave_angle = math.sin(arm_wave) * 28
    draw.ellipse(
        [x - 97*s, y + 115*s, x - 50*s, y + 177*s],
        fill=fur,
    )

    # Right arm is represented as a rotated-ish polygon.
    hand_x = x + (80 + 15*math.sin(arm_wave))*s
    hand_y = y + (110 - 30*math.cos(arm_wave))*s

    draw.line(
        [(x + 52*s, y + 130*s), (hand_x, hand_y)],
        fill=fur,
        width=max(10, int(34*s)),
    )
    draw.ellipse(
        [hand_x - 19*s, hand_y - 19*s, hand_x + 19*s, hand_y + 19*s],
        fill=fur,
    )

    # Scarf
    draw.rectangle(
        [x - 66*s, y + 145*s, x + 66*s, y + 176*s],
        fill=yellow,
    )
    draw.polygon(
        [
            (x + 28*s, y + 168*s),
            (x + 80*s, y + (210 + 8*math.sin(arm_wave))*s),
            (x + 55*s, y + 174*s),
        ],
        fill=yellow,
    )

    # Feet
    draw.ellipse(
        [x - 67*s, y + 205*s, x - 4*s, y + 248*s],
        fill=dark,
    )
    draw.ellipse(
        [x + 4*s, y + 205*s, x + 67*s, y + 248*s],
        fill=dark,
    )


def draw_mimi(draw, x, y, scale=1.0, bounce=0.0, arm_wave=0.0):
    """
    Mimi:
    small white rabbit with long pink-inner ears
    and purple backpack.
    """

    s = scale
    y += bounce

    white = (250, 250, 250)
    outline = (215, 215, 215)
    pink = (250, 165, 185)
    purple = (128, 78, 175)
    dark = (40, 40, 40)

    # Backpack behind body
    rounded(
        draw,
        [x + 38*s, y + 112*s, x + 94*s, y + 193*s],
        int(15*s),
        purple,
    )

    # Ears
    draw.ellipse(
        [x - 58*s, y - 102*s, x - 5*s, y + 48*s],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )
    draw.ellipse(
        [x + 5*s, y - 102*s, x + 58*s, y + 48*s],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    draw.ellipse(
        [x - 43*s, y - 80*s, x - 19*s, y + 27*s],
        fill=pink,
    )
    draw.ellipse(
        [x + 19*s, y - 80*s, x + 43*s, y + 27*s],
        fill=pink,
    )

    # Body
    draw.ellipse(
        [x - 62*s, y + 88*s, x + 62*s, y + 238*s],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    # Head
    draw.ellipse(
        [x - 72*s, y - 2*s, x + 72*s, y + 140*s],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    # Eyes
    eye_y = y + 65*s
    for eye_x in (-29, 29):
        draw.ellipse(
            [
                x + (eye_x - 8)*s,
                eye_y - 8*s,
                x + (eye_x + 8)*s,
                eye_y + 8*s,
            ],
            fill=dark,
        )

    # Nose
    draw.ellipse(
        [x - 9*s, y + 80*s, x + 9*s, y + 95*s],
        fill=pink,
    )

    # Smile
    draw.arc(
        [x - 19*s, y + 86*s, x + 19*s, y + 120*s],
        10,
        170,
        fill=dark,
        width=max(1, int(2*s)),
    )

    # Arms
    left_y = y + (125 + 10*math.sin(arm_wave))*s
    right_y = y + (125 - 10*math.sin(arm_wave))*s

    draw.line(
        [(x - 48*s, y + 130*s), (x - 85*s, left_y)],
        fill=white,
        width=max(10, int(30*s)),
    )
    draw.line(
        [(x + 48*s, y + 130*s), (x + 85*s, right_y)],
        fill=white,
        width=max(10, int(30*s)),
    )

    # Feet
    draw.ellipse(
        [x - 63*s, y + 215*s, x - 5*s, y + 250*s],
        fill=white,
        outline=outline,
    )
    draw.ellipse(
        [x + 5*s, y + 215*s, x + 63*s, y + 250*s],
        fill=white,
        outline=outline,
    )


def draw_kiki(draw, x, y, scale=1.0, bounce=0.0, flap=0.0):
    """
    Kiki:
    small yellow bird with bright blue wings and orange beak.
    """

    s = scale
    y += bounce

    yellow = (252, 221, 50)
    yellow_light = (255, 231, 75)
    blue = (55, 145, 220)
    orange = (242, 132, 35)
    dark = (35, 35, 35)

    # Body
    draw.ellipse(
        [x - 60*s, y + 45*s, x + 60*s, y + 205*s],
        fill=yellow,
    )

    # Head
    draw.ellipse(
        [x - 70*s, y - 20*s, x + 70*s, y + 112*s],
        fill=yellow_light,
    )

    # Wing positions change with flap.
    flap_amount = math.sin(flap)
    wing_y = y + (105 - 35*flap_amount)*s

    draw.ellipse(
        [x - 105*s, wing_y - 35*s, x - 28*s, wing_y + 55*s],
        fill=blue,
    )
    draw.ellipse(
        [x + 28*s, wing_y - 35*s, x + 105*s, wing_y + 55*s],
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
        [x - 46*s, y + 183*s, x - 5*s, y + 210*s],
        fill=orange,
    )
    draw.ellipse(
        [x + 5*s, y + 183*s, x + 46*s, y + 210*s],
        fill=orange,
    )


# ============================================================
# BACKGROUND
# ============================================================

PALE_SKIES = [
    (188, 225, 250),
    (205, 238, 198),
    (252, 226, 177),
    (226, 213, 246),
]


def draw_cloud(draw, x, y, scale=1.0):
    s = scale
    white = (255, 255, 255)

    draw.ellipse(
        [x, y + 18*s, x + 100*s, y + 62*s],
        fill=white,
    )
    draw.ellipse(
        [x + 25*s, y, x + 88*s, y + 62*s],
        fill=white,
    )
    draw.ellipse(
        [x + 60*s, y + 12*s, x + 135*s, y + 64*s],
        fill=white,
    )


def draw_background(draw, scene_number, time_s, camera_x=0):
    sky = PALE_SKIES[(scene_number - 1) % len(PALE_SKIES)]

    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=sky)

    # Sun gently pulses.
    pulse = 1.0 + 0.025 * math.sin(time_s * 1.2)
    sun_size = 105 * pulse
    sun_x = 1080 - camera_x * 0.15
    sun_y = 82

    draw.ellipse(
        [
            sun_x - sun_size/2,
            sun_y - sun_size/2,
            sun_x + sun_size/2,
            sun_y + sun_size/2,
        ],
        fill=(255, 220, 78),
    )

    # Moving clouds create parallax.
    cloud_speed = 12
    for base_x, base_y, scale in [
        (110, 105, 0.85),
        (410, 75, 1.05),
        (780, 125, 0.72),
    ]:
        x = (base_x + time_s * cloud_speed * scale) % (WIDTH + 180) - 150
        draw_cloud(draw, x - camera_x * 0.05, base_y, scale)

    # Distant hills.
    hill_offset = camera_x * 0.08
    draw.polygon(
        [
            (-100 - hill_offset, 525),
            (180 - hill_offset, 350),
            (400 - hill_offset, 525),
            (680 - hill_offset, 335),
            (950 - hill_offset, 525),
            (1200 - hill_offset, 365),
            (1450 - hill_offset, 525),
        ],
        fill=(155, 205, 145),
    )

    # Ground.
    draw.rectangle(
        [0, BG_GROUND_Y, WIDTH, HEIGHT],
        fill=(123, 190, 103),
    )

    # Moving grass strokes.
    for i in range(0, WIDTH + 50, 35):
        sway = 5 * math.sin(time_s * 2.2 + i * 0.08)
        x = i - (camera_x * 0.18) % 35

        draw.line(
            [
                (x, BG_GROUND_Y + 22),
                (x + sway, BG_GROUND_Y + 5),
            ],
            fill=(83, 158, 75),
            width=2,
        )

    # Flowers gently sway.
    for i in range(9):
        fx = 70 + i * 145 - (camera_x * 0.25) % 145
        fy = BG_GROUND_Y + 25 + (i % 3) * 12
        sway = 3 * math.sin(time_s * 2 + i)

        draw.line(
            [(fx, fy + 30), (fx + sway, fy)],
            fill=(70, 140, 70),
            width=3,
        )
        draw.ellipse(
            [fx - 8 + sway, fy - 8, fx + 8 + sway, fy + 8],
            fill=(255, 210, 80) if i % 2 == 0 else (245, 130, 160),
    )


# ============================================================
# PARTICLES / EDUCATIONAL OBJECT
# ============================================================

def draw_sparkles(draw, time_s, scene_number):
    for i in range(12):
        phase = i * 0.73 + scene_number
        x = 80 + ((i * 103) % 1120)
        y = 170 + ((i * 67) % 270)

        twinkle = 0.5 + 0.5 * math.sin(time_s * 3.0 + phase)

        if twinkle > 0.65:
            r = 3 + 4 * twinkle
            draw.ellipse(
                [x-r, y-r, x+r, y+r],
                fill=(255, 255, 245),
            )


def draw_lesson_object(draw, lesson, scene_number, time_s):
    """
    A simple animated educational object.
    The exact lesson can vary. The renderer chooses a visual
    object that matches common preschool concepts.
    """

    lesson_text = str(lesson).lower()

    if any(word in lesson_text for word in ["color", "colour", "red", "blue", "green", "yellow"]):
        colors = [
            (235, 70, 70),
            (70, 120, 235),
            (70, 180, 100),
            (250, 210, 50),
        ]

        for i, color in enumerate(colors):
            x = 425 + i * 115
            bounce = 10 * math.sin(time_s * 2.2 + i)
            draw.ellipse(
                [
                    x - 35,
                    405 + bounce - 35,
                    x + 35,
                    405 + bounce + 35,
                ],
                fill=color,
            )

    elif any(word in lesson_text for word in ["count", "number", "numbers", "one", "two", "three"]):
        for i in range(3):
            x = 485 + i * 130
            bounce = 12 * math.sin(time_s * 2.0 + i * 0.8)
            draw.ellipse(
                [x-42, 390+bounce-42, x+42, 390+bounce+42],
                fill=(245, 180, 70),
            )
            draw_text_center_local(
                draw,
                str(i + 1),
                x,
                372 + bounce,
                get_font(34, True),
                (70, 70, 90),
            )

    elif any(word in lesson_text for word in ["shape", "circle", "square", "triangle"]):
        shapes = ["circle", "square", "triangle"]

        for i, shape in enumerate(shapes):
            x = 470 + i * 150
            y = 400 + 12 * math.sin(time_s * 2 + i)

            if shape == "circle":
                draw.ellipse([x-38, y-38, x+38, y+38], fill=(90, 160, 230))
            elif shape == "square":
                draw.rectangle([x-38, y-38, x+38, y+38], fill=(245, 170, 70))
            else:
                draw.polygon(
                    [(x, y-45), (x-45, y+38), (x+45, y+38)],
                    fill=(100, 190, 110),
                )

    else:
        # Generic friendly learning stars.
        for i in range(5):
            x = 430 + i * 105
            y = 410 + 14 * math.sin(time_s * 1.8 + i)
            r = 28
            draw_star(draw, x, y, r, (248, 204, 70))


def draw_text_center_local(draw, text, center_x, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = center_x - (bbox[2] - bbox[0]) / 2
    draw.text((x, y), text, font=font, fill=fill)


def draw_star(draw, cx, cy, radius, fill):
    points = []

    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.45
        points.append(
            (
                cx + math.cos(angle) * r,
                cy + math.sin(angle) * r,
            )
        )

    draw.polygon(points, fill=fill)


# ============================================================
# SCENE TIMING
# ============================================================

def get_scene_duration(total_duration, scene_number):
    # Give the final scene slightly more time if possible.
    base = total_duration / 4.0

    if scene_number == 4:
        return base * 1.05

    return base * 0.9833333333


def scene_start(total_duration, scene_number):
    base = total_duration / 4.0
    return (scene_number - 1) * base


# ============================================================
# CHARACTER ANIMATION
# ============================================================

def character_positions(scene_number, local_t, scene_duration):
    """
    Returns positions in logical scene coordinates.

    The characters are deliberately animated differently
    in each scene so the episode does not feel repetitive.
    """

    progress = clamp(local_t / max(scene_duration, 0.001), 0, 1)

    if scene_number == 1:
        # Bobo enters from left.
        bobo_x = lerp(-160, 350, ease_in_out(clamp(local_t / 4.0, 0, 1)))
        bobo_y = 275

        # Mimi gently hops.
        mimi_x = 650
        mimi_y = 285

        # Kiki floats.
        kiki_x = 950
        kiki_y = 300

    elif scene_number == 2:
        # Group moves gradually toward the learning object.
        bobo_x = lerp(310, 455, ease_in_out(progress))
        bobo_y = 290

        mimi_x = lerp(650, 610, ease_in_out(progress))
        mimi_y = 285

        kiki_x = lerp(970, 820, ease_in_out(progress))
        kiki_y = 300

    elif scene_number == 3:
        # Characters spread out, creating a more dynamic composition.
        bobo_x = 400
        bobo_y = 285

        mimi_x = 700
        mimi_y = 285

        kiki_x = lerp(980, 900, ease_in_out(progress))
        kiki_y = 270

    else:
        # Closing scene: characters come together.
        bobo_x = lerp(310, 410, ease_in_out(progress))
        bobo_y = 280

        mimi_x = lerp(650, 640, ease_in_out(progress))
        mimi_y = 285

        kiki_x = lerp(970, 850, ease_in_out(progress))
        kiki_y = 275

    return {
        "Bobo": (bobo_x, bobo_y),
        "Mimi": (mimi_x, mimi_y),
        "Kiki": (kiki_x, kiki_y),
    }


# ============================================================
# SCENE FRAME
# ============================================================

def render_frame(story, scene_number, local_t, scene_duration, total_duration):
    image = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Camera movement.
    camera_zoom = 1.0 + 0.025 * math.sin(local_t * 0.55 + scene_number)

    if scene_number == 1:
        camera_x = -18 * math.sin(local_t * 0.35)
    elif scene_number == 2:
        camera_x = 24 * math.sin(local_t * 0.30)
    elif scene_number == 3:
        camera_x = -28 * math.sin(local_t * 0.28)
    else:
        camera_x = 16 * math.sin(local_t * 0.25)

    draw_background(draw, scene_number, local_t, camera_x)

    # Scene title.
    title = str(story.get("title", "NobiNest Adventure"))
    if len(title) > 45:
        title = title[:42] + "..."

    draw_text_center(
        draw,
        title,
        20,
        TITLE_FONT,
        (55, 70, 90),
    )

    # Educational object appears and gently animates.
    lesson = story.get("lesson", "")
    draw_lesson_object(draw, lesson, scene_number, local_t)

    # Sparkles.
    draw_sparkles(draw, local_t, scene_number)

    positions = character_positions(
        scene_number,
        local_t,
        scene_duration,
    )

    bobo_x, bobo_y = positions["Bobo"]
    mimi_x, mimi_y = positions["Mimi"]
    kiki_x, kiki_y = positions["Kiki"]

    # Walking bounce.
    bobo_walk = 7 * math.sin(local_t * 7.0)
    mimi_hop = -10 * max(0, math.sin(local_t * 4.2))
    kiki_float = 13 * math.sin(local_t * 2.6)

    # Character-specific movement.
    draw_bobo(
        draw,
        bobo_x - camera_x * 0.30,
        bobo_y,
        scale=1.08,
        bounce=bobo_walk,
        arm_wave=local_t * 2.8 if scene_number in (1, 4) else local_t * 0.8,
    )

    draw_mimi(
        draw,
        mimi_x - camera_x * 0.35,
        mimi_y,
        scale=1.04,
        bounce=mimi_hop,
        arm_wave=local_t * 2.0 if scene_number in (2, 3) else local_t,
    )

    draw_kiki(
        draw,
        kiki_x - camera_x * 0.42,
        kiki_y,
        scale=0.92,
        bounce=kiki_float,
        flap=local_t * 7.0,
    )

    # Lesson card.
    card_y = 570
    card_alpha = int(
        225 * clamp((local_t - 0.6) / 1.2, 0, 1)
    )

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    rounded(
        odraw,
        [70, card_y, WIDTH - 70, 690],
        24,
        fill=(255, 255, 255, card_alpha),
        outline=(80, 100, 120, min(255, card_alpha)),
        width=2,
    )

    lesson_lines = wrap_text(
        odraw,
        "Lesson: " + str(lesson),
        LESSON_FONT,
        WIDTH - 190,
    )

    text_y = card_y + 18

    for line in lesson_lines[:3]:
        bbox = odraw.textbbox((0, 0), line, font=LESSON_FONT)
        x = (WIDTH - (bbox[2] - bbox[0])) / 2
        odraw.text(
            (x, text_y),
            line,
            font=LESSON_FONT,
            fill=(40, 50, 65, card_alpha),
        )
        text_y += 29

    image = alpha_composite(image, overlay)

    return image


# ============================================================
# AUDIO / SUBTITLES
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
        raise RuntimeError("Could not determine narration duration.")

    return float(value)


def format_timestamp(seconds):
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    total_seconds = int(seconds)

    if milliseconds >= 1000:
        milliseconds = 0
        total_seconds += 1

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return (
        f"{hours:02d}:{minutes:02d}:{secs:02d},"
        f"{milliseconds:03d}"
    )


def create_subtitles(story, duration):
    parts = []

    for scene in story.get("scenes", []):
        narration = str(scene.get("narration", "")).strip()
        if narration:
            parts.append(narration)

    song = story.get("song", {})
    if isinstance(song, dict):
        lyrics = str(song.get("lyrics", "")).strip()
        if lyrics:
            parts.append(lyrics)

    ending = str(story.get("ending", "")).strip()
    if ending:
        parts.append(ending)

    full_text = " ".join(parts).strip()
    words = full_text.split()

    if not words:
        return

    # Short subtitle chunks suitable for children.
    chunk_size = 6

    chunks = [
        words[i:i + chunk_size]
        for i in range(0, len(words), chunk_size)
    ]

    chunk_duration = duration / len(chunks)

    with open(SRT_FILE, "w", encoding="utf-8") as file:
        for index, chunk in enumerate(chunks, 1):
            start = (index - 1) * chunk_duration
            end = min(duration, index * chunk_duration)

            file.write(f"{index}\n")
            file.write(
                f"{format_timestamp(start)} --> "
                f"{format_timestamp(end)}\n"
            )
            file.write(" ".join(chunk))
            file.write("\n\n")


# ============================================================
# VIDEO RENDER
# ============================================================

def render_video(story, duration):
    print("==============================================")
    print("NOBINEST 2D MOTION RENDERER")
    print("==============================================")
    print(f"Resolution: {WIDTH}x{HEIGHT}")
    print(f"Frame rate: {FPS} FPS")
    print(f"Duration: {duration:.2f} seconds")
    print("")

    # FFmpeg receives raw RGB frames through stdin.
    command = [
        "ffmpeg",
        "-y",
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
        "-i",
        str(AUDIO_FILE),
        "-vf",
        (
            "subtitles="
            + str(SRT_FILE).replace("\\", "/").replace(":", "\\:")
            + ":force_style="
            "'FontName=DejaVu Sans,"
            "FontSize=21,"
            "Bold=1,"
            "Alignment=2,"
            "MarginV=34,"
            "Outline=2,"
            "Shadow=1'"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-t",
        f"{duration:.3f}",
        "-shortest",
        str(VIDEO_FILE),
    ]

    print("Starting FFmpeg...")
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    total_frames = max(1, int(math.ceil(duration * FPS)))
    last_scene = None

    try:
        for frame_index in range(total_frames):
            current_time = frame_index / FPS

            # Four scene structure.
            scene_number = min(
                4,
                int((current_time / duration) * 4) + 1,
            )

            scene_duration = duration / 4.0
            local_t = current_time - (scene_number - 1) * scene_duration
            local_t = clamp(local_t, 0, scene_duration)

            if scene_number != last_scene:
                print(
                    f"Animating scene {scene_number}/4..."
                )
                last_scene = scene_number

            frame = render_frame(
                story,
                scene_number,
                local_t,
                scene_duration,
                duration,
            )

            process.stdin.write(frame.tobytes())

            if frame_index % FPS == 0:
                percent = (frame_index / total_frames) * 100
                print(
                    f"Rendered {current_time:6.1f}s / "
                    f"{duration:6.1f}s "
                    f"({percent:5.1f}%)"
                )

        process.stdin.close()

        stderr = process.stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        return_code = process.wait()

        if return_code != 0:
            print(stderr)
            raise RuntimeError(
                f"FFmpeg failed with exit code {return_code}"
            )

    except BrokenPipeError:
        stderr = process.stderr.read().decode(
            "utf-8",
            errors="replace",
        )
        process.wait()
        print(stderr)
        raise RuntimeError(
            "FFmpeg closed the video pipe unexpectedly."
        )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 55)
    print("NOBINEST KIDS 2D MOTION VIDEO RENDERER")
    print("=" * 55)

    if not STORY_FILE.exists():
        raise FileNotFoundError(
            f"Missing story file: {STORY_FILE}"
        )

    if not AUDIO_FILE.exists():
        raise FileNotFoundError(
            f"Missing narration file: {AUDIO_FILE}"
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

    duration = get_audio_duration()

    if duration <= 0:
        raise RuntimeError(
            "Narration duration is zero."
        )

    print(f"Story: {story.get('title', 'Untitled')}")
    print(f"Lesson: {story.get('lesson', '')}")
    print(f"Audio duration: {duration:.2f} seconds")

    print("Creating subtitles...")
    create_subtitles(
        story,
        duration,
    )

    print("Rendering moving characters...")
    print("Rendering camera movement...")
    print("Rendering environmental motion...")
    print("Rendering educational objects...")

    render_video(
        story,
        duration,
    )

    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "Renderer finished but the MP4 was not created."
        )

    size_mb = VIDEO_FILE.stat().st_size / (1024 * 1024)

    print("")
    print("=" * 55)
    print("ANIMATED VIDEO CREATED SUCCESSFULLY")
    print("=" * 55)
    print(f"Video: {VIDEO_FILE}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Subtitles: {SRT_FILE}")
    print("")
    print("Animation features enabled:")
    print("  Character walking")
    print("  Character bouncing")
    print("  Character waving")
    print("  Bird wing flapping")
    print("  Bird floating")
    print("  Moving clouds")
    print("  Swaying grass")
    print("  Swaying flowers")
    print("  Floating sparkles")
    print("  Animated educational objects")
    print("  Camera motion")
    print("  Smooth scene transitions")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print("RENDERER ERROR")
        print(str(exc))
        sys.exit(1)
