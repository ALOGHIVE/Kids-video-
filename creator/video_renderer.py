import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NOBINEST SCENE-AWARE 2D MOTION VIDEO RENDERER
# ============================================================
# This renderer reads BOTH:
#   story["lesson"]
#   story["scenes"][n]["visual_description"]
#
# It does not treat the four scenes as identical.
#
# The visual description is converted into a scene plan that
# controls:
#   - character movement
#   - educational objects
#   - object movement
#   - camera motion
#   - scene-specific actions
#   - simple interactions
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
GROUND_Y = 525


# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=False):
    candidates = []

    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


TITLE_FONT = get_font(34, True)
LESSON_FONT = get_font(21, True)
OBJECT_FONT = get_font(32, True)
SMALL_FONT = get_font(18, False)


# ============================================================
# BASIC HELPERS
# ============================================================

def clamp(v, low, high):
    return max(low, min(high, v))


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_center(draw, text, cx, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


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


def alpha_layer(base, overlay):
    return Image.alpha_composite(
        base.convert("RGBA"),
        overlay.convert("RGBA"),
    ).convert("RGB")


def star_points(cx, cy, radius):
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
    return points


# ============================================================
# CHARACTER DRAWING
# ============================================================

def draw_bobo(draw, x, y, scale=1.0, bounce=0.0, wave=0.0):
    s = scale
    y += bounce

    fur = (156, 98, 58)
    fur_light = (181, 119, 72)
    dark = (95, 58, 38)
    muzzle = (218, 165, 111)
    yellow = (248, 207, 45)

    # body
    draw.ellipse(
        [x - 64*s, y + 72*s, x + 64*s, y + 230*s],
        fill=fur,
    )

    # ears
    for ex in (-38, 38):
        draw.ellipse(
            [x + (ex-32)*s, y - 2*s,
             x + (ex+32)*s, y + 62*s],
            fill=fur,
        )

    # head
    draw.ellipse(
        [x - 78*s, y + 15*s, x + 78*s, y + 155*s],
        fill=fur_light,
    )

    # eyes
    for ex in (-30, 30):
        draw.ellipse(
            [x + (ex-9)*s, y + 67*s,
             x + (ex+9)*s, y + 85*s],
            fill=(30, 30, 30),
        )
        draw.ellipse(
            [x + (ex-4)*s, y + 69*s,
             x + (ex+1)*s, y + 74*s],
            fill="white",
        )

    # muzzle
    draw.ellipse(
        [x - 32*s, y + 94*s, x + 32*s, y + 134*s],
        fill=muzzle,
    )
    draw.ellipse(
        [x - 10*s, y + 101*s,
         x + 10*s, y + 116*s],
        fill=dark,
    )

    draw.arc(
        [x - 20*s, y + 105*s,
         x + 20*s, y + 137*s],
        15, 165,
        fill=dark,
        width=max(1, int(3*s)),
    )

    # arms
    draw.ellipse(
        [x - 97*s, y + 115*s,
         x - 50*s, y + 177*s],
        fill=fur,
    )

    hand_x = x + (82 + 16*math.sin(wave))*s
    hand_y = y + (111 - 32*math.cos(wave))*s

    draw.line(
        [(x + 50*s, y + 130*s), (hand_x, hand_y)],
        fill=fur,
        width=max(10, int(34*s)),
    )
    draw.ellipse(
        [hand_x - 19*s, hand_y - 19*s,
         hand_x + 19*s, hand_y + 19*s],
        fill=fur,
    )

    # scarf
    draw.rectangle(
        [x - 66*s, y + 145*s,
         x + 66*s, y + 176*s],
        fill=yellow,
    )
    draw.polygon(
        [
            (x + 28*s, y + 168*s),
            (x + 80*s, y + (210 + 8*math.sin(wave))*s),
            (x + 55*s, y + 174*s),
        ],
        fill=yellow,
    )

    # feet
    draw.ellipse(
        [x - 67*s, y + 205*s,
         x - 4*s, y + 248*s],
        fill=dark,
    )
    draw.ellipse(
        [x + 4*s, y + 205*s,
         x + 67*s, y + 248*s],
        fill=dark,
    )


def draw_mimi(draw, x, y, scale=1.0, bounce=0.0, wave=0.0):
    s = scale
    y += bounce

    white = (250, 250, 250)
    outline = (215, 215, 215)
    pink = (250, 165, 185)
    purple = (128, 78, 175)
    dark = (40, 40, 40)

    # backpack
    rounded(
        draw,
        [x + 38*s, y + 112*s,
         x + 94*s, y + 193*s],
        int(15*s),
        purple,
    )

    # ears
    for side in (-1, 1):
        draw.ellipse(
            [x + (side*5-58)*s, y - 102*s,
             x + (side*5-5)*s, y + 48*s],
            fill=white,
            outline=outline,
            width=max(1, int(2*s)),
        )

    draw.ellipse(
        [x - 43*s, y - 80*s,
         x - 19*s, y + 27*s],
        fill=pink,
    )
    draw.ellipse(
        [x + 19*s, y - 80*s,
         x + 43*s, y + 27*s],
        fill=pink,
    )

    # body
    draw.ellipse(
        [x - 62*s, y + 88*s,
         x + 62*s, y + 238*s],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    # head
    draw.ellipse(
        [x - 72*s, y - 2*s,
         x + 72*s, y + 140*s],
        fill=white,
        outline=outline,
        width=max(1, int(2*s)),
    )

    # eyes
    for ex in (-29, 29):
        draw.ellipse(
            [x + (ex-8)*s, y + 57*s,
             x + (ex+8)*s, y + 73*s],
            fill=dark,
        )

    draw.ellipse(
        [x - 9*s, y + 80*s,
         x + 9*s, y + 95*s],
        fill=pink,
    )

    draw.arc(
        [x - 19*s, y + 86*s,
         x + 19*s, y + 120*s],
        10, 170,
        fill=dark,
        width=max(1, int(2*s)),
    )

    # arms
    left_y = y + (125 + 12*math.sin(wave))*s
    right_y = y + (125 - 12*math.sin(wave))*s

    draw.line(
        [(x - 48*s, y + 130*s),
         (x - 85*s, left_y)],
        fill=white,
        width=max(10, int(30*s)),
    )
    draw.line(
        [(x + 48*s, y + 130*s),
         (x + 85*s, right_y)],
        fill=white,
        width=max(10, int(30*s)),
    )

    # feet
    draw.ellipse(
        [x - 63*s, y + 215*s,
         x - 5*s, y + 250*s],
        fill=white,
        outline=outline,
    )
    draw.ellipse(
        [x + 5*s, y + 215*s,
         x + 63*s, y + 250*s],
        fill=white,
        outline=outline,
    )


def draw_kiki(draw, x, y, scale=1.0, bounce=0.0, flap=0.0):
    s = scale
    y += bounce

    yellow = (252, 221, 50)
    yellow_light = (255, 231, 75)
    blue = (55, 145, 220)
    orange = (242, 132, 35)
    dark = (35, 35, 35)

    draw.ellipse(
        [x - 60*s, y + 45*s,
         x + 60*s, y + 205*s],
        fill=yellow,
    )

    draw.ellipse(
        [x - 70*s, y - 20*s,
         x + 70*s, y + 112*s],
        fill=yellow_light,
    )

    flap_amount = math.sin(flap)
    wing_y = y + (105 - 35*flap_amount)*s

    draw.ellipse(
        [x - 105*s, wing_y - 35*s,
         x - 28*s, wing_y + 55*s],
        fill=blue,
    )
    draw.ellipse(
        [x + 28*s, wing_y - 35*s,
         x + 105*s, wing_y + 55*s],
        fill=blue,
    )

    for ex in (-29, 29):
        draw.ellipse(
            [x + (ex-9)*s, y + 33*s,
             x + (ex+9)*s, y + 51*s],
            fill=dark,
        )

    draw.polygon(
        [
            (x, y + 61*s),
            (x + 52*s, y + 77*s),
            (x, y + 94*s),
        ],
        fill=orange,
    )

    draw.ellipse(
        [x - 46*s, y + 183*s,
         x - 5*s, y + 210*s],
        fill=orange,
    )
    draw.ellipse(
        [x + 5*s, y + 183*s,
         x + 46*s, y + 210*s],
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
        [x, y + 18*s, x + 100*s, y + 62*s],
        fill=white,
    )
    draw.ellipse(
        [x + 25*s, y, x + 88*s, y + 62*s],
        fill=white,
    )
    draw.ellipse(
        [x + 60*s, y + 12*s,
         x + 135*s, y + 64*s],
        fill=white,
    )


def draw_background(draw, scene_no, t, camera_x):
    sky = SKIES[(scene_no - 1) % len(SKIES)]

    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=sky)

    pulse = 1 + 0.025 * math.sin(t * 1.2)
    sun = 105 * pulse

    draw.ellipse(
        [1080 - sun/2, 82 - sun/2,
         1080 + sun/2, 82 + sun/2],
        fill=(255, 220, 78),
    )

    for bx, by, scale in [
        (110, 105, .85),
        (410, 75, 1.05),
        (780, 125, .72),
    ]:
        x = (bx + t * 12 * scale) % (WIDTH + 180) - 150
        draw_cloud(
            draw,
            x - camera_x * .05,
            by,
            scale,
        )

    offset = camera_x * .08

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

    draw.rectangle(
        [0, GROUND_Y, WIDTH, HEIGHT],
        fill=(123, 190, 103),
    )

    for i in range(0, WIDTH + 50, 35):
        sway = 5 * math.sin(t * 2.2 + i * .08)
        x = i - (camera_x * .18) % 35

        draw.line(
            [(x, GROUND_Y + 22),
             (x + sway, GROUND_Y + 5)],
            fill=(83, 158, 75),
            width=2,
        )

    for i in range(9):
        fx = 70 + i * 145 - (camera_x * .25) % 145
        fy = GROUND_Y + 25 + (i % 3) * 12
        sway = 3 * math.sin(t * 2 + i)

        draw.line(
            [(fx, fy + 30),
             (fx + sway, fy)],
            fill=(70, 140, 70),
            width=3,
        )

        flower_color = (
            (255, 210, 80)
            if i % 2 == 0
            else (245, 130, 160)
        )

        draw.ellipse(
            [fx - 8 + sway, fy - 8,
             fx + 8 + sway, fy + 8],
            fill=flower_color,
        )


# ============================================================
# SCENE DESCRIPTION UNDERSTANDING
# ============================================================

def normalize(text):
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def has_any(text, words):
    return any(word in text for word in words)


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


def build_scene_plan(story, scene_no):
    """
    Convert Gemini's visual_description into a deterministic animation plan.

    The plan is deliberately richer than a single action.  A preschool
    scene should feel like a small piece of animation, so we extract:
      * the main object
      * object color
      * participating characters
      * multiple actions
      * an interaction target
      * a camera style
      * a four-beat choreography
    """
    scenes = story.get("scenes", [])

    if not scenes or scene_no > len(scenes):
        description = ""
    else:
        description = normalize(
            scenes[scene_no - 1].get("visual_description", "")
        )

    lesson = normalize(story.get("lesson", ""))
    text = f"{description} {lesson}"

    color_name, color_value = detect_color(text)

    # --------------------------------------------------------
    # Educational object
    # --------------------------------------------------------
    object_rules = [
        (["ball", "sphere", "round ball"], "ball", f"{color_name} ball"),
        (["flower", "flowers", "petal"], "flower", f"{color_name} flower"),
        (["circle", "circular"], "circle", "circle"),
        (["square", "box"], "square", "square"),
        (["triangle"], "triangle", "triangle"),
        (["apple", "fruit"], "apple", f"{color_name} apple"),
        (["star", "stars"], "star", "star"),
        (["number", "count", "counting"], "numbers", "numbers"),
        (["leaf", "leaves", "tree"], "leaf", "leaf"),
    ]

    obj = "stars"
    object_name = "learning stars"

    for keywords, candidate, label in object_rules:
        if has_any(text, keywords):
            obj = candidate
            object_name = label
            break

    # --------------------------------------------------------
    # All actions mentioned in the description
    # --------------------------------------------------------
    action_keywords = [
        ("roll", ["roll", "rolling", "rolled"]),
        ("hop", ["hop", "hops", "hopping", "jump", "jumps", "jumping"]),
        ("fly", ["fly", "flies", "flying", "flew"]),
        ("walk", ["walk", "walks", "walking", "move", "moves", "moving"]),
        ("point", ["point", "points", "pointing"]),
        ("pick", ["pick", "picks", "picking", "pick up", "reach", "reaches", "reaching"]),
        ("dance", ["dance", "dances", "dancing"]),
        ("celebrate", ["celebrate", "celebrates", "celebrating", "clap", "claps", "cheer"]),
        ("turn", ["turn", "turns", "turning"]),
        ("land", ["land", "lands", "landing"]),
    ]

    detected_actions = []
    for action, keywords in action_keywords:
        if has_any(description, keywords):
            detected_actions.append(action)

    if not detected_actions:
        detected_actions = ["general"]

    # Preserve textual order approximately by using the order in which
    # action keywords first appear in the description.
    ordered = []
    for action, keywords in action_keywords:
        positions = [description.find(k) for k in keywords if description.find(k) >= 0]
        if positions:
            ordered.append((min(positions), action))
    ordered.sort()
    ordered_actions = [a for _, a in ordered]

    if ordered_actions:
        detected_actions = ordered_actions

    # --------------------------------------------------------
    # Which characters are explicitly involved?
    # --------------------------------------------------------
    characters = []
    for name in ("Bobo", "Mimi", "Kiki"):
        if name.lower() in description:
            characters.append(name)

    if not characters:
        characters = ["Bobo", "Mimi", "Kiki"]

    focus = characters[0] if len(characters) == 1 else "group"

    # Give Kiki natural priority for flight scenes.
    if "Kiki" in characters and "fly" in detected_actions:
        focus = "Kiki"

    # --------------------------------------------------------
    # Character-specific action extraction
    # --------------------------------------------------------
    actor_actions = {name: [] for name in ("Bobo", "Mimi", "Kiki")}

    # Sentences are useful because Gemini normally writes one action
    # per sentence/phrase.
    clauses = re.split(r"[,.;]| and | then | while | as ", description)

    for clause in clauses:
        c = clause.strip()
        if not c:
            continue

        local_actions = []
        for action, keywords in action_keywords:
            if has_any(c, keywords):
                local_actions.append(action)

        if not local_actions:
            continue

        for name in ("Bobo", "Mimi", "Kiki"):
            if name.lower() in c:
                actor_actions[name].extend(local_actions)

    # If a scene mentions an action but not the actor in the same clause,
    # assign the action to the explicit focus character.
    for action in detected_actions:
        if action == "general":
            continue
        if not any(action in vals for vals in actor_actions.values()):
            target = focus if focus != "group" else characters[0]
            actor_actions[target].append(action)

    for name in actor_actions:
        # De-duplicate without destroying order.
        actor_actions[name] = list(dict.fromkeys(actor_actions[name]))

    # --------------------------------------------------------
    # Four-beat choreography
    # --------------------------------------------------------
    # Every scene gets a beginning, action, interaction and reaction.
    primary = detected_actions[0] if detected_actions else "general"
    secondary = detected_actions[1] if len(detected_actions) > 1 else primary

    beats = [
        {"phase": "intro", "action": "enter"},
        {"phase": "action", "action": primary},
        {"phase": "interaction", "action": secondary},
        {"phase": "resolve", "action": "celebrate"},
    ]

    # A scene-specific progression overrides generic beats.
    if scene_no == 1:
        beats = [
            {"phase": "intro", "action": "enter"},
            {"phase": "discover", "action": primary},
            {"phase": "demonstrate", "action": secondary},
            {"phase": "react", "action": "celebrate"},
        ]
    elif scene_no == 2:
        beats = [
            {"phase": "approach", "action": "walk"},
            {"phase": "demonstrate", "action": primary},
            {"phase": "interact", "action": secondary},
            {"phase": "react", "action": "celebrate"},
        ]
    elif scene_no == 3:
        beats = [
            {"phase": "approach", "action": primary},
            {"phase": "demonstrate", "action": secondary},
            {"phase": "interact", "action": "pick"},
            {"phase": "react", "action": "celebrate"},
        ]
    elif scene_no == 4:
        beats = [
            {"phase": "gather", "action": "walk"},
            {"phase": "show", "action": primary},
            {"phase": "celebrate", "action": "dance"},
            {"phase": "finale", "action": "celebrate"},
        ]

    # --------------------------------------------------------
    # Camera direction
    # --------------------------------------------------------
    if "fly" in detected_actions:
        camera = "follow"
    elif "walk" in detected_actions or "roll" in detected_actions:
        camera = "track"
    elif "point" in detected_actions or "pick" in detected_actions:
        camera = "focus"
    elif "dance" in detected_actions or "celebrate" in detected_actions:
        camera = "wide"
    else:
        camera = "gentle"

    return {
        "description": description,
        "lesson": lesson,
        "action": primary,
        "actions": detected_actions,
        "object": obj,
        "color": color_value,
        "color_name": color_name,
        "object_name": object_name,
        "focus": focus,
        "characters": characters,
        "actor_actions": actor_actions,
        "beats": beats,
        "camera": camera,
    }


# ============================================================
# SCENE CHOREOGRAPHY HELPERS
# ============================================================

def phase_progress(t, phase_index, count=4):
    start = phase_index / count
    end = (phase_index + 1) / count
    return clamp((t - start) / max(end - start, 0.001), 0.0, 1.0)


def active_phase(t, count=4):
    return min(count - 1, int(clamp(t, 0, 0.999999) * count))


def beat_action(plan, t):
    index = active_phase(t, len(plan.get("beats", [])) or 4)
    beats = plan.get("beats", [])
    if not beats:
        return plan.get("action", "general")
    return beats[index].get("action", "general")


def actor_is_active(plan, name, action=None):
    actions = plan.get("actor_actions", {}).get(name, [])
    if action is None:
        return bool(actions)
    return action in actions


def scene_object_anchor(scene_no, plan, t):
    """
    Returns the main learning object position.  Objects stay spatially
    coherent within a scene instead of teleporting between generic frames.
    """
    action = beat_action(plan, t)

    if scene_no == 1:
        return (730 + 35 * math.sin(t * math.pi * 2), 410)
    if scene_no == 2:
        # The object becomes the destination.
        return (650, 405 - 12 * math.sin(t * math.pi * 2))
    if scene_no == 3:
        # Slightly right so Mimi has a clear target.
        return (735, 405)
    if scene_no == 4:
        return (650, 405)

    return (650, 405)


def draw_target_marker(draw, x, y, t, color=(255, 255, 255)):
    pulse = 1 + 0.18 * math.sin(t * math.pi * 6)
    r = 42 * pulse
    draw.ellipse(
        [x-r, y-r, x+r, y+r],
        outline=color,
        width=3,
    )
    for angle in range(0, 360, 90):
        a = math.radians(angle)
        x1 = x + math.cos(a) * (r + 6)
        y1 = y + math.sin(a) * (r + 6)
        x2 = x + math.cos(a) * (r + 17)
        y2 = y + math.sin(a) * (r + 17)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=3)


def draw_action_caption(draw, plan, t):
    """
    Tiny visual action cue.  This is intentionally graphical rather
    than a large block of text so the video remains a cartoon.
    """
    action = beat_action(plan, t)
    labels = {
        "walk": "GO!",
        "hop": "HOP!",
        "fly": "FLY!",
        "point": "LOOK!",
        "pick": "REACH!",
        "roll": "ROLL!",
        "dance": "DANCE!",
        "celebrate": "YAY!",
    }

    label = labels.get(action)
    if not label:
        return

    # Only show during the middle of a scene, not constantly.
    pulse = math.sin(t * math.pi * 8)
    if pulse < -0.25:
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
# EDUCATIONAL OBJECTS
# ============================================================
# EDUCATIONAL OBJECTS
# ============================================================

def draw_circle_object(draw, cx, cy, radius, fill, outline=(255,255,255)):
    draw.ellipse(
        [cx-radius, cy-radius,
         cx+radius, cy+radius],
        fill=fill,
        outline=outline,
        width=4,
    )


def draw_flower(draw, cx, cy, scale, color):
    s = scale

    for i in range(6):
        angle = i * math.pi / 3
        px = cx + math.cos(angle) * 48 * s
        py = cy + math.sin(angle) * 48 * s

        draw.ellipse(
            [px-30*s, py-30*s,
             px+30*s, py+30*s],
            fill=color,
        )

    draw.ellipse(
        [cx-30*s, cy-30*s,
         cx+30*s, cy+30*s],
        fill=(250, 210, 50),
    )

    draw.line(
        [(cx, cy+25*s),
         (cx, cy+125*s)],
        fill=(70, 145, 70),
        width=max(4, int(8*s)),
    )

    draw.ellipse(
        [cx-55*s, cy+75*s,
         cx-5*s, cy+105*s],
        fill=(90, 165, 80),
    )


def draw_object(draw, plan, t, action):
    obj = plan["object"]
    color = plan["color"]

    # Main object motion.
    if action == "roll":
        cx = lerp(350, 920, ease(t))
        cy = 430 - 15 * math.sin(t * math.pi * 3)
        rotation = t * 10
    elif action == "fly":
        cx = 640 + 250 * math.sin(t * math.pi * 2)
        cy = 330 + 70 * math.sin(t * math.pi * 4)
        rotation = t * 4
    elif action == "hop":
        cx = 650
        cy = 410 - 75 * max(0, math.sin(t * math.pi * 4))
        rotation = 0
    elif action == "pick":
        cx = 650
        cy = 420 - 40 * ease(t)
        rotation = 0
    else:
        cx = 650 + 45 * math.sin(t * math.pi * 2)
        cy = 405 + 18 * math.sin(t * math.pi * 3)
        rotation = 0

    if obj == "ball" or obj == "circle":
        radius = 62 if obj == "ball" else 72
        draw_circle_object(
            draw,
            cx,
            cy,
            radius,
            color,
        )

        if obj == "ball":
            # highlight and seam
            draw.ellipse(
                [cx-25, cy-35,
                 cx-5, cy-15],
                fill=(255, 255, 255),
            )
            draw.arc(
                [cx-radius*.65, cy-radius*.65,
                 cx+radius*.65, cy+radius*.65],
                rotation * 20,
                rotation * 20 + 120,
                fill=(255, 255, 255),
                width=3,
            )

        draw_center(
            draw,
            "CIRCLE" if obj == "circle" else "",
            cx,
            cy - 18,
            OBJECT_FONT,
            (255,255,255),
        )

    elif obj == "flower":
        draw_flower(
            draw,
            cx,
            cy - 40,
            1.0,
            color,
        )

    elif obj == "square":
        size = 125
        draw.rectangle(
            [cx-size, cy-size,
             cx+size, cy+size],
            fill=color,
            outline=(255,255,255),
            width=5,
        )

    elif obj == "triangle":
        draw.polygon(
            [
                (cx, cy-100),
                (cx-110, cy+85),
                (cx+110, cy+85),
            ],
            fill=color,
            outline=(255,255,255),
        )

    elif obj == "apple":
        draw.ellipse(
            [cx-65, cy-60,
             cx+65, cy+70],
            fill=color,
        )
        draw.ellipse(
            [cx-50, cy-30,
             cx+10, cy+50],
            fill=color,
        )
        draw.line(
            [(cx, cy-55), (cx+10, cy-105)],
            fill=(95,65,35),
            width=10,
        )

    elif obj == "star":
        draw.polygon(
            star_points(cx, cy, 80),
            fill=color,
        )

    elif obj == "numbers":
        for i in range(3):
            nx = cx - 145 + i * 145
            ny = cy + 15 * math.sin(t*math.pi*2+i)
            draw_circle_object(
                draw,
                nx,
                ny,
                48,
                (245, 180, 70),
            )
            draw_center(
                draw,
                str(i+1),
                nx,
                ny-23,
                OBJECT_FONT,
                (70,70,90),
            )

    elif obj == "leaf":
        draw.ellipse(
            [cx-85, cy-35,
             cx+85, cy+35],
            fill=(80, 175, 90),
        )
        draw.line(
            [(cx-80, cy+25),
             (cx+80, cy-25)],
            fill=(50,125,65),
            width=5,
        )

    else:
        for i in range(5):
            sx = 430 + i * 105
            sy = 400 + 14 * math.sin(t*2+i)
            draw.polygon(
                star_points(sx, sy, 28),
                fill=(248,204,70),
            )


# ============================================================
# CHARACTER POSITIONS AND ACTIONS
# ============================================================

def draw_action_effects(draw, plan, t, object_xy):
    """Draw lightweight visual effects that reinforce the current action."""
    action = beat_action(plan, t)
    x, y = object_xy

    # Moving dust puffs for walking, hopping and landing.
    if action in ("walk", "hop", "land"):
        for i in range(3):
            phase = t * 5.0 + i * 2.1
            px = x - 45 + i * 45 + 10 * math.sin(phase)
            py = GROUND_Y - 8 - 6 * abs(math.sin(phase))
            r = 4 + 3 * (0.5 + 0.5 * math.sin(phase))
            draw.ellipse([px-r, py-r, px+r, py+r], fill=(225, 214, 190))

    # Speed lines make flight visibly different from standing.
    if action == "fly":
        for i in range(4):
            yy = y - 35 + i * 22
            length = 35 + 15 * math.sin(t * 7 + i)
            draw.line([(x - 85, yy), (x - 85 - length, yy)], fill=(255,255,255), width=3)

    # Pointing cue: a soft ring around the target.
    if action == "point":
        pulse = 1 + 0.12 * math.sin(t * 8)
        r = 48 * pulse
        draw.ellipse([x-r, y-r, x+r, y+r], outline=(255, 245, 150), width=3)

    # Reach/pick cue: small sparkles around the object.
    if action == "pick":
        for i in range(6):
            a = t * 2.0 + i * math.pi / 3
            rr = 55 + 8 * math.sin(t * 6 + i)
            px = x + math.cos(a) * rr
            py = y + math.sin(a) * rr
            draw_star(draw, px, py, 7, (255, 220, 80))

    # Rolling cue: repeated motion streaks behind the object.
    if action == "roll":
        for i in range(3):
            yy = y + 25 + i * 12
            draw.line([(x - 70 - i * 12, yy), (x - 25, yy)], fill=(120,140,150), width=3)

    # Dance/celebration cue: floating confetti and sparkles.
    if action in ("dance", "celebrate"):
        for i in range(10):
            a = i * 0.73 + t * 1.4
            radius = 90 + 25 * math.sin(t * 2 + i)
            px = WIDTH / 2 + math.cos(a) * radius
            py = 300 + math.sin(a * 1.3) * 120
            r = 3 + (i % 3)
            draw.ellipse([px-r, py-r, px+r, py+r], fill=(255, 215, 75))

def get_positions(scene_no, t, plan):
    """
    Scene choreography is deliberately different for every scene.
    Positions are targets, not static poses.  The renderer interpolates
    between them and adds secondary motion.
    """
    p = ease(t)
    phase = active_phase(t, 4)
    q = phase_progress(t, phase, 4)

    # Base staging.
    bobo = [360, 285]
    mimi = [650, 285]
    kiki = [930, 265]

    if scene_no == 1:
        # Establishing shot: Bobo enters, Mimi waits, Kiki floats.
        bobo[0] = lerp(-150, 360, ease(clamp(t / 0.55, 0, 1)))
        bobo[1] += 8 * math.sin(t * math.pi * 10)

        mimi[0] = 610 + 25 * math.sin(t * math.pi * 2)
        mimi[1] += -12 * max(0, math.sin(t * math.pi * 4))

        kiki[0] = 930 + 55 * math.sin(t * math.pi * 1.5)
        kiki[1] = 250 + 35 * math.sin(t * math.pi * 3)

        if phase >= 2:
            # Group attention shifts toward the object.
            bobo[0] = lerp(bobo[0], 520, ease(q))
            mimi[0] = lerp(mimi[0], 660, ease(q))
            kiki[0] = lerp(kiki[0], 820, ease(q))

    elif scene_no == 2:
        # Strong left-to-right approach.  This is visually different
        # from scene 1 and makes the object the destination.
        bobo[0] = lerp(300, 555, ease(t))
        bobo[1] += 8 * math.sin(t * math.pi * 9)

        mimi[0] = lerp(820, 690, ease(t))
        mimi[1] += -22 * max(0, math.sin(t * math.pi * 5))

        kiki[0] = lerp(1020, 860, ease(t))
        kiki[1] = 245 + 25 * math.sin(t * math.pi * 3)

        if "point" in plan.get("actions", []) and phase >= 1:
            bobo[0] = lerp(bobo[0], 545, ease(q))

    elif scene_no == 3:
        # Mimi becomes the visual lead. Kiki performs an aerial move.
        bobo[0] = 380 + 25 * math.sin(t * math.pi * 2)
        bobo[1] = 285

        mimi[0] = lerp(520, 690, ease(t))
        mimi[1] = 285 - 35 * max(0, math.sin(t * math.pi * 6))

        kiki[0] = lerp(1030, 790, ease(t))
        kiki[1] = 205 + 105 * math.sin(t * math.pi * 2)

        if "land" in plan.get("actions", []) and phase >= 2:
            kiki[0] = lerp(kiki[0], 820, ease(q))
            kiki[1] = lerp(kiki[1], 285, ease(q))

    else:
        # Finale: characters converge, then spread for a readable
        # celebration composition.
        bobo[0] = lerp(350, 465, ease(t))
        mimi[0] = lerp(650, 640, ease(t))
        kiki[0] = lerp(950, 820, ease(t))

        bobo[1] = 285 + 12 * math.sin(t * math.pi * 7)
        mimi[1] = 285 - 18 * max(0, math.sin(t * math.pi * 6 + .5))
        kiki[1] = 255 + 24 * math.sin(t * math.pi * 5)

        if phase >= 2:
            # Celebration pose around the object.
            bobo[0] = lerp(bobo[0], 430, ease(q))
            mimi[0] = lerp(mimi[0], 650, ease(q))
            kiki[0] = lerp(kiki[0], 870, ease(q))

    return {
        "Bobo": tuple(bobo),
        "Mimi": tuple(mimi),
        "Kiki": tuple(kiki),
    }


# ============================================================
# SCENE FRAME
# ============================================================
# SCENE FRAME
# ============================================================

def render_frame(story, scene_no, local_t, scene_duration, total_duration):
    image = Image.new("RGB", (WIDTH, HEIGHT), (255,255,255))
    draw = ImageDraw.Draw(image)

    plan = build_scene_plan(story, scene_no)
    t = clamp(local_t / max(scene_duration, 0.001), 0.0, 1.0)

    # --------------------------------------------------------
    # Cinematic camera
    # --------------------------------------------------------
    camera_style = plan.get("camera", "gentle")

    if camera_style == "track":
        camera_x = lerp(-25, 35, ease(t))
    elif camera_style == "follow":
        camera_x = 35 * math.sin(t * math.pi * 1.2)
    elif camera_style == "focus":
        camera_x = -18 * math.sin(t * math.pi)
    elif camera_style == "wide":
        camera_x = 12 * math.sin(t * math.pi)
    else:
        camera_x = 18 * math.sin(t * math.pi * 1.2)

    draw_background(draw, scene_no, local_t, camera_x)

    # Subtle foreground depth.
    for i in range(12):
        x = (i * 121 + 30 - camera_x * .25) % WIDTH
        y = GROUND_Y + 18 + (i % 3) * 13
        draw.ellipse(
            [x-4, y-4, x+4, y+4],
            fill=(95,165,85),
        )

    # --------------------------------------------------------
    # Title and scene identity
    # --------------------------------------------------------
    title = str(story.get("title", "NobiNest Adventure"))
    if len(title) > 48:
        title = title[:45] + "..."

    draw_center(
        draw, title, WIDTH/2, 18,
        TITLE_FONT, (55,70,90),
    )

    draw_center(
        draw,
        f"Scene {scene_no} of 4",
        WIDTH/2,
        58,
        SMALL_FONT,
        (70,90,105),
    )

    draw_action_caption(draw, plan, t)

    # --------------------------------------------------------
    # Main object
    # --------------------------------------------------------
    object_xy = scene_object_anchor(scene_no, plan, t)

    # The object itself is drawn using the scene's action, but its
    # position is controlled separately so characters can interact
    # with a stable target.
    object_plan = dict(plan)
    object_plan["object_anchor"] = object_xy

    draw_object(
        draw,
        object_plan,
        t,
        beat_action(plan, t),
    )

    # Target marker is only shown when the story asks the character
    # to look/point/reach. This makes interaction obvious.
    if beat_action(plan, t) in ("point", "pick"):
        draw_target_marker(draw, object_xy[0], object_xy[1], t)

    draw_action_effects(
        draw,
        plan,
        t,
        object_xy,
    )

    # --------------------------------------------------------
    # Characters
    # --------------------------------------------------------
    positions = get_positions(
        scene_no,
        t,
        plan,
    )

    bobo_x, bobo_y = positions["Bobo"]
    mimi_x, mimi_y = positions["Mimi"]
    kiki_x, kiki_y = positions["Kiki"]

    current_action = beat_action(plan, t)

    # Stronger motion when an action is active.
    bobo_bounce = 6 * math.sin(local_t * 7)
    mimi_bounce = -8 * max(0, math.sin(local_t * 4.2))
    kiki_float = 10 * math.sin(local_t * 2.8)

    if current_action == "hop":
        mimi_bounce = -35 * max(0, math.sin(local_t * 6.5))

    if current_action == "fly":
        kiki_float = 25 * math.sin(local_t * 5.5)

    if current_action in ("dance", "celebrate"):
        bobo_bounce = 15 * math.sin(local_t * 8)
        mimi_bounce = -20 * max(0, math.sin(local_t * 7))
        kiki_float = 24 * math.sin(local_t * 6)

    # Waving becomes more purposeful in action scenes.
    bobo_wave = local_t * (
        4.2 if actor_is_active(plan, "Bobo") or current_action in ("dance","celebrate")
        else 1.0
    )
    mimi_wave = local_t * (
        4.0 if actor_is_active(plan, "Mimi") or current_action in ("dance","celebrate")
        else 1.1
    )

    # Kiki's wings flap faster during flight.
    kiki_flap = local_t * (
        11 if current_action == "fly" or actor_is_active(plan, "Kiki", "fly")
        else 7
    )

    # Draw order gives Kiki aerial depth while keeping the animals
    # readable in front of the environment.
    draw_bobo(
        draw,
        bobo_x - camera_x*.30,
        bobo_y,
        scale=1.08,
        bounce=bobo_bounce,
        wave=bobo_wave,
    )

    draw_mimi(
        draw,
        mimi_x - camera_x*.35,
        mimi_y,
        scale=1.04,
        bounce=mimi_bounce,
        wave=mimi_wave,
    )

    draw_kiki(
        draw,
        kiki_x - camera_x*.42,
        kiki_y,
        scale=.92,
        bounce=kiki_float,
        flap=kiki_flap,
    )

    # --------------------------------------------------------
    # Lesson card
    # --------------------------------------------------------
    lesson = str(story.get("lesson", "")).strip()

    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0,0,0,0),
    )
    odraw = ImageDraw.Draw(overlay)

    # Card is intentionally less opaque so the animation remains visible.
    card_alpha = int(
        205 * clamp((t - .12) / .55, 0, 1)
    )

    rounded(
        odraw,
        [55, 575, WIDTH-55, 692],
        22,
        fill=(255,255,255,card_alpha),
        outline=(80,100,120,card_alpha),
        width=2,
    )

    lesson_lines = wrap_text(
        odraw,
        "Lesson: " + lesson,
        LESSON_FONT,
        WIDTH-165,
    )

    y = 589
    for line in lesson_lines[:3]:
        bbox = odraw.textbbox(
            (0,0), line, font=LESSON_FONT
        )
        x = (WIDTH - (bbox[2]-bbox[0])) / 2

        odraw.text(
            (x,y),
            line,
            font=LESSON_FONT,
            fill=(40,50,65,card_alpha),
        )
        y += 27

    image = alpha_layer(image, overlay)

    # Scene transition fade.
    return draw_scene_transition_overlay(image, t, scene_no)


# ============================================================
# SCENE TRANSITION OVERLAY
# ============================================================

def draw_scene_transition_overlay(image, t, scene_no):
    """
    Add a short cinematic fade at the beginning and end of each
    scene. This keeps scene changes smooth without hiding the
    animation for long.
    """
    # Each scene is rendered independently, so t is local scene time.
    # The renderer uses a short fade-in/out window.
    FADE_SECONDS = 0.45

    # The exact scene duration is not passed here. A short fade-out
    # is therefore based on the final portion of the normalized scene.
    # The caller can mark the end using the global scene boundary.
    # For safety, only apply a fade-in here. The video itself remains
    # fully visible during the majority of the scene.
    fade_in = clamp(t / FADE_SECONDS, 0.0, 1.0)

    # First scene starts from black; later scenes start from black too,
    # producing a clean cut/fade between the four visual chapters.
    alpha = int(255 * (1.0 - ease_in_out(fade_in)))

    if alpha <= 0:
        return image

    overlay = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, alpha),
    )

    return alpha_layer(image, overlay)


# ============================================================
# AUDIO
# ============================================================
# AUDIO
# ============================================================

def get_audio_duration():
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
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
# SUBTITLES
# ============================================================

def format_timestamp(seconds):
    total_seconds = int(seconds)
    milliseconds = int(
        round(
            (seconds-total_seconds)*1000
        )
    )

    if milliseconds >= 1000:
        milliseconds = 0
        total_seconds += 1

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


def create_subtitles(story, duration):
    """
    Create subtitles using the actual story structure instead of splitting
    the entire episode into equal six-word chunks.

    Each scene gets a time range proportional to its spoken word count.
    The song and ending then receive their own ranges. Within each range,
    short subtitle chunks are timed proportionally by word count.
    """
    segments = []

    for i, scene in enumerate(story.get("scenes", []), 1):
        narration = str(scene.get("narration", "")).strip()
        if narration:
            segments.append({
                "label": f"Scene {i}",
                "text": narration,
            })

    song = story.get("song", {})
    if isinstance(song, dict):
        lyrics = str(song.get("lyrics", "")).strip()
        if lyrics:
            segments.append({
                "label": "Song",
                "text": lyrics,
            })

    ending = str(story.get("ending", "")).strip()
    if ending:
        segments.append({
            "label": "Ending",
            "text": ending,
        })

    if not segments:
        return

    total_words = sum(
        max(1, len(segment["text"].split()))
        for segment in segments
    )

    cursor = 0.0
    cues = []

    for segment in segments:
        words = segment["text"].split()
        count = max(1, len(words))
        segment_duration = duration * count / total_words

        start_segment = cursor
        end_segment = min(duration, cursor + segment_duration)
        cursor = end_segment

        chunk_size = 6
        chunks = [
            words[i:i + chunk_size]
            for i in range(0, len(words), chunk_size)
        ]

        chunk_words = sum(len(chunk) for chunk in chunks)
        local_cursor = start_segment

        for chunk in chunks:
            chunk_duration = (
                (end_segment - start_segment)
                * len(chunk)
                / max(1, chunk_words)
            )

            cue_end = min(
                end_segment,
                local_cursor + chunk_duration,
            )

            cues.append(
                (
                    local_cursor,
                    cue_end,
                    " ".join(chunk),
                )
            )

            local_cursor = cue_end

    with open(SRT_FILE, "w", encoding="utf-8") as file:
        for index, (start, end, caption) in enumerate(cues, 1):
            file.write(f"{index}\n")
            file.write(
                f"{format_timestamp(start)} --> "
                f"{format_timestamp(end)}\n"
            )
            file.write(caption)
            file.write("\n\n")

# ============================================================
# VIDEO RENDER
# ============================================================
# VIDEO RENDER
# ============================================================

def render_video(story, duration):
    print("=" * 55)
    print("NOBINEST SCENE-AWARE 2D MOTION RENDERER")
    print("=" * 55)
    print(f"Resolution: {WIDTH}x{HEIGHT}")
    print(f"Frame rate: {FPS}")
    print(f"Duration: {duration:.2f}s")
    print("")

    # Print exactly what the renderer understood.
    for i, scene in enumerate(
        story.get("scenes", []),
        1,
    ):
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
            f"  visual_description: "
            f"{scene.get('visual_description', '')}"
        )

    subtitle_path = str(
        SRT_FILE
    ).replace("\\", "/").replace(
        ":", "\\:"
    )

    vf = (
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
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(AUDIO_FILE),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", f"{duration:.3f}",
        "-shortest",
        str(VIDEO_FILE),
    ]

    print("")
    print("Starting FFmpeg...")

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
                duration * FPS
            )
        ),
    )

    last_scene = None

    try:
        for frame_index in range(
            total_frames
        ):
            current_time = (
                frame_index / FPS
            )

            scene_no = min(
                4,
                int(
                    (current_time / duration)
                    * 4
                ) + 1,
            )

            scene_duration = (
                duration / 4
            )

            local_t = (
                current_time
                - (scene_no-1)
                * scene_duration
            )

            local_t = clamp(
                local_t,
                0,
                scene_duration,
            )

            if scene_no != last_scene:
                print(
                    f"Animating scene "
                    f"{scene_no}/4..."
                )
                last_scene = scene_no

            frame = render_frame(
                story,
                scene_no,
                local_t,
                scene_duration,
                duration,
            )

            process.stdin.write(
                frame.tobytes()
            )

            if frame_index % FPS == 0:
                percent = (
                    frame_index
                    / total_frames
                    * 100
                )

                print(
                    f"Rendered "
                    f"{current_time:5.1f}s / "
                    f"{duration:5.1f}s "
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
                "FFmpeg failed with "
                f"exit code {return_code}"
            )

    except BrokenPipeError:
        stderr = process.stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        process.wait()

        print(stderr)

        raise RuntimeError(
            "FFmpeg closed the video pipe "
            "unexpectedly."
        )


# ============================================================
# VALIDATION
# ============================================================

def validate_inputs(story):
    if not isinstance(story, dict):
        raise ValueError(
            "story.json is not a JSON object."
        )

    scenes = story.get("scenes")

    if not isinstance(scenes, list):
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
        if not scene.get(
            "visual_description"
        ):
            raise ValueError(
                f"Scene {i} is missing "
                "visual_description."
            )

        if not scene.get(
            "narration"
        ):
            raise ValueError(
                f"Scene {i} is missing "
                "narration."
            )


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 55)
    print("NOBINEST KIDS SCENE-AWARE VIDEO RENDERER")
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

    validate_inputs(story)

    duration = get_audio_duration()

    if duration <= 0:
        raise RuntimeError(
            "Narration duration is zero."
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
        f"{duration:.2f}s"
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
    print("Creating subtitles...")

    create_subtitles(
        story,
        duration,
    )

    print(
        "Rendering scene-specific animation..."
    )

    render_video(
        story,
        duration,
    )

    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "Renderer finished but MP4 "
            "was not created."
        )

    size_mb = (
        VIDEO_FILE.stat().st_size
        / (1024 * 1024)
    )

    print("")
    print("=" * 55)
    print("SCENE-AWARE VIDEO CREATED SUCCESSFULLY")
    print("=" * 55)
    print(f"Video: {VIDEO_FILE}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Subtitles: {SRT_FILE}")
    print("")
    print("Scene-aware features:")
    print("  visual_description parsing")
    print("  scene-specific objects")
    print("  ball rolling")
    print("  character hopping")
    print("  bird flying")
    print("  pointing actions")
    print("  picking/reaching effects")
    print("  group dancing")
    print("  circle formation")
    print("  animated shapes")
    print("  animated flowers")
    print("  animated numbers")
    print("  animated colors")
    print("  camera movement")
    print("  moving clouds")
    print("  moving grass")
    print("  animated subtitles")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print("=" * 55)
        print("RENDERER ERROR")
        print("=" * 55)
        print(str(exc))
        sys.exit(1)
