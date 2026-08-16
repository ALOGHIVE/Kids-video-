import json
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NOBINEST 2D MOTION RENDERER v8 FINAL
# ============================================================
# Fully procedural 2D animation.
#
# No paid image/video API is required.
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
MAX_DURATION = 90.0
MIN_DURATION = 60.0

# Current frame zoom, used by prop drawing helpers.
current_zoom = (1.0,)


# ============================================================
# FONTS
# ============================================================

def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


TITLE_FONT = get_font(34, True)
LESSON_FONT = get_font(22, True)
SMALL_FONT = get_font(18, True)


# ============================================================
# MATH / DRAW HELPERS
# ============================================================

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=int(radius),
        fill=fill,
        outline=outline,
        width=max(1, int(width)),
    )


def text_center(draw, text, cx, y, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (cx - (box[2] - box[0]) / 2, y),
        text,
        font=font,
        fill=fill,
    )


def wrap_text(draw, text, font, width):
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word
        box = draw.textbbox((0, 0), test, font=font)

        if box[2] - box[0] <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def rotate_point(px, py, cx, cy, angle):
    s = math.sin(angle)
    c = math.cos(angle)
    dx = px - cx
    dy = py - cy
    return (
        cx + dx * c - dy * s,
        cy + dx * s + dy * c,
    )


def draw_rotated_ellipse(draw, box, angle, fill):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    rx = (x2 - x1) / 2
    ry = (y2 - y1) / 2

    points = []
    for i in range(24):
        a = 2 * math.pi * i / 24
        px = cx + rx * math.cos(a)
        py = cy + ry * math.sin(a)
        points.append(rotate_point(px, py, cx, cy, angle))

    draw.polygon(points, fill=fill)


def draw_star(draw, cx, cy, radius, fill):
    points = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.42
        points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    draw.polygon(points, fill=fill)


# ============================================================
# CHARACTER DRAWING
# ============================================================

def draw_bobo(draw, x, y, scale=1.0, phase=0.0, wave=0.0,
              facing=1.0, gesture=0.0):
    s = scale
    fur = (154, 96, 57)
    fur_light = (184, 124, 76)
    dark = (92, 55, 35)
    muzzle = (222, 169, 113)
    yellow = (248, 207, 45)

    walk = math.sin(phase)
    body_y = y + 72 * s

    # shadow
    shadow_w = 62 * s * (1.0 - 0.08 * abs(walk))
    draw.ellipse(
        [x - shadow_w, GROUND_Y - 6, x + shadow_w, GROUND_Y + 12],
        fill=(86, 145, 78),
    )

    # legs
    leg_shift = 8 * walk * s
    draw.ellipse(
        [x - 62*s + leg_shift, y + 205*s,
         x - 5*s + leg_shift, y + 250*s],
        fill=dark,
    )
    draw.ellipse(
        [x + 5*s - leg_shift, y + 205*s,
         x + 62*s - leg_shift, y + 250*s],
        fill=dark,
    )

    # body
    draw.ellipse(
        [x - 64*s, body_y, x + 64*s, y + 230*s],
        fill=fur,
    )

    # ears
    draw.ellipse([x - 68*s, y - 2*s, x - 5*s, y + 62*s], fill=fur)
    draw.ellipse([x + 5*s, y - 2*s, x + 68*s, y + 62*s], fill=fur)
    draw.ellipse([x - 55*s, y + 8*s, x - 18*s, y + 45*s], fill=fur_light)
    draw.ellipse([x + 18*s, y + 8*s, x + 55*s, y + 45*s], fill=fur_light)

    # head
    draw.ellipse(
        [x - 78*s, y + 15*s, x + 78*s, y + 155*s],
        fill=fur_light,
    )

    # eyes
    eye_y = y + 76*s
    for ex in (-30, 30):
        draw.ellipse(
            [x + (ex-9)*s, eye_y-9*s,
             x + (ex+9)*s, eye_y+9*s],
            fill=(28, 28, 28),
        )
        draw.ellipse(
            [x + (ex-4)*s, eye_y-6*s,
             x + (ex+1)*s, eye_y-1*s],
            fill="white",
        )

    # muzzle / nose
    draw.ellipse(
        [x - 32*s, y + 94*s, x + 32*s, y + 134*s],
        fill=muzzle,
    )
    draw.ellipse(
        [x - 10*s, y + 101*s, x + 10*s, y + 116*s],
        fill=dark,
    )

    # smile
    draw.arc(
        [x - 20*s, y + 105*s, x + 20*s, y + 137*s],
        15, 165,
        fill=dark,
        width=max(2, int(3*s)),
    )

    # arms
    left_angle = -0.15 + 0.18 * math.sin(phase + 1)
    right_angle = -0.35 + 0.45 * math.sin(wave) + gesture

    draw_rotated_ellipse(
        draw,
        [x - 102*s, y + 112*s, x - 48*s, y + 182*s],
        left_angle,
        fur,
    )

    draw_rotated_ellipse(
        draw,
        [x + 42*s, y + 105*s, x + 104*s, y + 178*s],
        right_angle,
        fur,
    )

    # scarf
    draw.rectangle(
        [x - 66*s, y + 145*s, x + 66*s, y + 176*s],
        fill=yellow,
    )
    scarf_wave = 10 * math.sin(phase * 0.7)
    draw.polygon(
        [
            (x + 25*s, y + 168*s),
            (x + (78 + scarf_wave)*s, y + 205*s),
            (x + 55*s, y + 174*s),
        ],
        fill=yellow,
    )


def draw_mimi(draw, x, y, scale=1.0, phase=0.0, wave=0.0,
              gesture=0.0):
    s = scale
    white = (250, 250, 250)
    outline = (214, 214, 214)
    pink = (250, 165, 185)
    purple = (128, 78, 175)
    dark = (40, 40, 40)

    hop = max(0.0, math.sin(phase)) * 10 * s
    y -= hop

    # shadow
    shadow = 58 * s * (1.0 - hop / (20*s))
    draw.ellipse(
        [x-shadow, GROUND_Y-5, x+shadow, GROUND_Y+10],
        fill=(86, 145, 78),
    )

    # backpack
    rounded(
        draw,
        [x + 38*s, y + 112*s, x + 94*s, y + 193*s],
        15*s,
        purple,
    )

    # ears
    draw.ellipse(
        [x - 58*s, y - 102*s, x - 5*s, y + 48*s],
        fill=white, outline=outline, width=max(1, int(2*s)),
    )
    draw.ellipse(
        [x + 5*s, y - 102*s, x + 58*s, y + 48*s],
        fill=white, outline=outline, width=max(1, int(2*s)),
    )
    draw.ellipse(
        [x - 43*s, y - 80*s, x - 19*s, y + 27*s],
        fill=pink,
    )
    draw.ellipse(
        [x + 19*s, y - 80*s, x + 43*s, y + 27*s],
        fill=pink,
    )

    # body
    draw.ellipse(
        [x - 62*s, y + 88*s, x + 62*s, y + 238*s],
        fill=white, outline=outline, width=max(1, int(2*s)),
    )

    # head
    draw.ellipse(
        [x - 72*s, y - 2*s, x + 72*s, y + 140*s],
        fill=white, outline=outline, width=max(1, int(2*s)),
    )

    # eyes
    eye_y = y + 65*s
    for ex in (-29, 29):
        draw.ellipse(
            [x+(ex-8)*s, eye_y-8*s,
             x+(ex+8)*s, eye_y+8*s],
            fill=dark,
        )

    # nose
    draw.ellipse(
        [x-9*s, y+80*s, x+9*s, y+95*s],
        fill=pink,
    )

    # smile
    draw.arc(
        [x-19*s, y+86*s, x+19*s, y+120*s],
        10, 170,
        fill=dark,
        width=max(2, int(2*s)),
    )

    # arms
    arm = 0.2 * math.sin(wave) + gesture
    draw_rotated_ellipse(
        draw,
        [x-92*s, y+110*s, x-42*s, y+180*s],
        -0.25-arm,
        white,
    )
    draw_rotated_ellipse(
        draw,
        [x+42*s, y+105*s, x+92*s, y+180*s],
        0.25+arm,
        white,
    )

    # feet
    draw.ellipse(
        [x-63*s, y+215*s, x-5*s, y+250*s],
        fill=white, outline=outline,
    )
    draw.ellipse(
        [x+5*s, y+215*s, x+63*s, y+250*s],
        fill=white, outline=outline,
    )


def draw_kiki(draw, x, y, scale=1.0, phase=0.0, flight=0.0,
              gesture=0.0):
    s = scale
    yellow = (252, 221, 50)
    yellow_light = (255, 231, 75)
    blue = (55, 145, 220)
    orange = (242, 132, 35)
    dark = (35, 35, 35)

    flap = math.sin(phase)
    y += 10 * math.sin(phase * 0.5)

    # wings
    wing_y = y + (105 - 38*flap) * s

    draw.ellipse(
        [x-108*s, wing_y-35*s, x-28*s, wing_y+55*s],
        fill=blue,
    )
    draw.ellipse(
        [x+28*s, wing_y-35*s, x+108*s, wing_y+55*s],
        fill=blue,
    )

    # body
    draw.ellipse(
        [x-60*s, y+45*s, x+60*s, y+205*s],
        fill=yellow,
    )

    # head
    draw.ellipse(
        [x-70*s, y-20*s, x+70*s, y+112*s],
        fill=yellow_light,
    )

    # eyes
    for ex in (-29, 29):
        draw.ellipse(
            [x+(ex-9)*s, y+33*s,
             x+(ex+9)*s, y+51*s],
            fill=dark,
        )

    # beak
    draw.polygon(
        [
            (x, y+61*s),
            (x+52*s, y+77*s),
            (x, y+94*s),
        ],
        fill=orange,
    )

    # feet
    draw.ellipse(
        [x-46*s, y+183*s, x-5*s, y+210*s],
        fill=orange,
    )
    draw.ellipse(
        [x+5*s, y+183*s, x+46*s, y+210*s],
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
    white = (255, 255, 255)
    s = scale

    draw.ellipse([x, y+18*s, x+100*s, y+62*s], fill=white)
    draw.ellipse([x+25*s, y, x+88*s, y+62*s], fill=white)
    draw.ellipse([x+60*s, y+12*s, x+135*s, y+64*s], fill=white)


def draw_background(draw, scene, t, camera_x):
    sky = SKIES[(scene - 1) % len(SKIES)]
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=sky)

    # sun
    pulse = 1 + 0.03 * math.sin(t * 1.4)
    r = 52 * pulse
    sx = 1090 - camera_x * 0.12
    sy = 82
    draw.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(255, 220, 78))

    # clouds
    for bx, by, sc, speed in [
        (80, 95, .85, 10),
        (430, 70, 1.0, 7),
        (820, 125, .72, 13),
    ]:
        cx = (bx + t*speed) % (WIDTH+220) - 160
        draw_cloud(draw, cx - camera_x*0.04, by, sc)

    # far hills
    hx = camera_x * 0.08
    draw.polygon(
        [
            (-100-hx, GROUND_Y),
            (160-hx, 350),
            (400-hx, GROUND_Y),
            (680-hx, 335),
            (960-hx, GROUND_Y),
            (1220-hx, 360),
            (1450-hx, GROUND_Y),
        ],
        fill=(155, 205, 145),
    )

    # ground
    draw.rectangle([0, GROUND_Y, WIDTH, HEIGHT], fill=(123, 190, 103))

    # grass
    for i in range(-20, WIDTH+40, 35):
        sway = 5 * math.sin(t*2.3 + i*.08)
        x = i - (camera_x*.18) % 35
        draw.line(
            [(x, GROUND_Y+22), (x+sway, GROUND_Y+5)],
            fill=(83, 158, 75),
            width=2,
        )

    # flowers
    for i in range(10):
        fx = 65 + i*140 - (camera_x*.22) % 140
        fy = GROUND_Y + 28 + (i%3)*10
        sway = 3 * math.sin(t*2 + i)
        draw.line(
            [(fx, fy+30), (fx+sway, fy)],
            fill=(70, 140, 70),
            width=3,
        )
        petal = (255, 210, 80) if i % 2 == 0 else (245, 130, 160)
        draw.ellipse(
            [fx-8+sway, fy-8, fx+8+sway, fy+8],
            fill=petal,
        )



# ============================================================
# STORY-AWARE OBJECTS AND ACTION CHOREOGRAPHY
# ============================================================

def draw_apple(draw, x, y, scale=1.0, bob=0.0):
    s = scale
    y += bob
    red = (220, 55, 55)
    dark_red = (170, 40, 40)
    green = (72, 150, 72)
    draw.ellipse([x-30*s, y-25*s, x+30*s, y+27*s], fill=red)
    draw.ellipse([x-2*s, y-30*s, x+31*s, y+22*s], fill=red)
    draw.line([(x+2*s, y-27*s), (x+8*s, y-43*s)], fill=dark_red, width=max(2, int(5*s)))
    draw.ellipse([x+7*s, y-45*s, x+30*s, y-33*s], fill=green)

def draw_tree(draw, x, y, scale=1.0):
    s = scale
    trunk = (125, 82, 48)
    leaves = (78, 158, 80)
    draw.rectangle([x-28*s, y, x+28*s, y+180*s], fill=trunk)
    for dx, dy, r in [(-70,0,72),(0,-35,90),(72,0,72),(0,35,80)]:
        draw.ellipse([x+(dx-r)*s, y+(dy-r)*s,
                      x+(dx+r)*s, y+(dy+r)*s], fill=leaves)

def draw_basket(draw, x, y, scale=1.0, apples=0):
    s = scale
    brown = (165, 105, 55)
    light = (205, 145, 82)
    draw.rounded_rectangle([x-80*s,y-5*s,x+80*s,y+65*s],
                           radius=int(14*s), fill=light)
    draw.arc([x-65*s,y-55*s,x+65*s,y+35*s], 180, 360,
             fill=brown, width=max(3,int(7*s)))
    for i in range(apples):
        draw_apple(draw, x+(i-(apples-1)/2)*42*s, y+12*s, .42*s)


def scene_text(story, scene):
    scenes = story.get("scenes", [])
    if 1 <= scene <= len(scenes):
        s = scenes[scene-1]
        return (
            str(s.get("visual_description", "")) + " " +
            str(s.get("narration", ""))
        ).lower()
    return ""


def find_color(text, default):
    colors = {
        "red": (225, 55, 55),
        "blue": (65, 125, 235),
        "green": (75, 175, 85),
        "yellow": (248, 210, 55),
        "purple": (150, 85, 205),
        "pink": (245, 125, 175),
        "orange": (245, 135, 45),
        "white": (248, 248, 248),
        "brown": (145, 90, 50),
    }
    for name, value in colors.items():
        if name in text:
            return value
    return default


def draw_ball(draw, x, y, radius, color, shine=True):
    draw.ellipse(
        [x-radius, y-radius, x+radius, y+radius],
        fill=color,
        outline=(70, 70, 70),
        width=max(2, int(radius*0.035)),
    )
    if shine:
        r = max(3, int(radius*0.16))
        draw.ellipse(
            [x-radius*0.45, y-radius*0.48,
             x-radius*0.45+r*2, y-radius*0.48+r*2],
            fill=(255,255,255),
        )
    # simple curved seam
    draw.arc(
        [x-radius*0.7, y-radius*0.35,
         x+radius*0.7, y+radius*0.9],
        205, 340,
        fill=(255,255,255),
        width=max(2, int(radius*0.025)),
    )


def draw_hat(draw, x, y, scale, color, brim=True):
    s = scale
    # crown
    draw.rounded_rectangle(
        [x-42*s, y-62*s, x+42*s, y+5*s],
        radius=int(12*s),
        fill=color,
        outline=(75,75,75),
        width=max(2, int(3*s)),
    )
    if brim:
        draw.ellipse(
            [x-78*s, y-12*s, x+78*s, y+25*s],
            fill=color,
            outline=(75,75,75),
            width=max(2, int(3*s)),
        )
    draw.line(
        [(x-39*s, y-3*s), (x+39*s, y-3*s)],
        fill=(255,255,255),
        width=max(2, int(4*s)),
    )


def draw_flower(draw, x, y, scale=1.0, petal=(245,120,160), center=(248,205,55)):
    s = scale
    draw.line([(x,y+20*s),(x,y+95*s)], fill=(70,150,75), width=max(2,int(7*s)))
    for a in range(0,360,72):
        rad=math.radians(a)
        cx=x+math.cos(rad)*27*s
        cy=y+math.sin(rad)*27*s
        draw.ellipse([cx-18*s,cy-18*s,cx+18*s,cy+18*s], fill=petal)
    draw.ellipse([x-14*s,y-14*s,x+14*s,y+14*s], fill=center)


def draw_watermelon(draw, x, y, scale=1.0):
    s=scale
    draw.ellipse(
        [x-125*s,y-72*s,x+125*s,y+72*s],
        fill=(80,175,85), outline=(45,120,60), width=max(2,int(4*s))
    )
    # stripes
    for dx in (-75,-25,25,75):
        draw.arc(
            [x+(dx-45)*s,y-67*s,x+(dx+45)*s,y+67*s],
            70,110, fill=(35,115,55), width=max(2,int(5*s))
        )
    draw.ellipse([x-10*s,y-5*s,x+4*s,y+9*s], fill=(45,35,30))


def draw_strawberry(draw, x, y, scale=1.0):
    s=scale
    draw.polygon(
        [(x-35*s,y-10*s),(x+35*s,y-10*s),
         (x+20*s,y+48*s),(x,y+65*s),
         (x-20*s,y+48*s)],
        fill=(225,55,70)
    )
    draw.polygon(
        [(x,y-22*s),(x-25*s,y-5*s),(x-8*s,y+2*s),
         (x,y-10*s),(x+8*s,y+2*s),(x+25*s,y-5*s)],
        fill=(65,165,75)
    )
    for dx,dy in [(-14,8),(0,18),(14,8),(-8,35),(8,35)]:
        draw.ellipse([x+(dx-2)*s,y+(dy-2)*s,x+(dx+2)*s,y+(dy+2)*s], fill=(255,225,90))


def draw_leaf(draw, x, y, scale=1.0, color=(75,170,80)):
    s=scale
    draw.ellipse([x-75*s,y-25*s,x+75*s,y+25*s], fill=color, outline=(45,120,55))
    draw.line([(x-65*s,y+12*s),(x+65*s,y-12*s)], fill=(220,245,190), width=max(2,int(3*s)))


def draw_book(draw, x, y, scale=1.0):
    s=scale
    draw.rounded_rectangle([x-70*s,y-50*s,x-3*s,y+50*s], radius=int(8*s), fill=(235,90,90), outline=(80,60,60), width=max(2,int(3*s)))
    draw.rounded_rectangle([x+3*s,y-50*s,x+70*s,y+50*s], radius=int(8*s), fill=(75,145,225), outline=(60,60,80), width=max(2,int(3*s)))
    draw.line([(x,y-45*s),(x,y+45*s)], fill=(255,240,200), width=max(2,int(3*s)))


def draw_cup(draw, x, y, scale=1.0):
    s=scale
    draw.rounded_rectangle([x-45*s,y-45*s,x+45*s,y+45*s], radius=int(10*s), fill=(95,175,230), outline=(60,80,100), width=max(2,int(3*s)))
    draw.arc([x+25*s,y-20*s,x+75*s,y+35*s], 270, 90, fill=(60,80,100), width=max(2,int(5*s)))


def draw_scene_props(draw, story, scene, t, world_point, foreground=False):
    """Render the concrete objects described by the CURRENT scene.

    This version is deliberately scene-text driven. It does not assume that
    scene 1 is a ball story, scene 2 is a ball story, etc.
    """
    text = scene_text(story, scene)
    scenes = story.get("scenes", [])
    raw = scenes[scene-1].get("visual_description", "").lower() if 1 <= scene <= len(scenes) else ""

    def P(x, y):
        return world_point(x, y)

    # Current actor positions in world coordinates.
    positions = character_positions(scene, t, max(1.0, 15.0))
    bx, by = positions["Bobo"]
    mx, my = positions["Mimi"]
    kx, ky = positions["Kiki"]

    # --------------------------------------------------------
    # SCENE 1: baskets held by Bobo and Mimi
    # --------------------------------------------------------
    if scene == 1 and "basket" in text and foreground:
        pbx, pby = P(bx, by + 150)
        pmx, pmy = P(mx, my + 150)

        big_scale = 1.22
        small_scale = .62

        draw_basket(draw, pbx, pby, big_scale, 0)
        draw_basket(draw, pmx, pmy, small_scale, 0)

        # Strong visual labels through size contrast.
        draw.line(
            [(pbx-55*big_scale, pby-35*big_scale),
             (pbx+55*big_scale, pby-35*big_scale)],
            fill=(125,75,40), width=max(3, int(5*big_scale))
        )
        draw.line(
            [(pmx-28*small_scale, pmy-25*small_scale),
             (pmx+28*small_scale, pmy-25*small_scale)],
            fill=(125,75,40), width=max(2, int(4*small_scale))
        )

    # --------------------------------------------------------
    # SCENE 2: the same baskets + two apples with clear size contrast
    # --------------------------------------------------------
    if scene == 2 and "basket" in text and foreground:
        pbx, pby = P(bx, by + 150)
        pmx, pmy = P(mx, my + 150)
        draw_basket(draw, pbx, pby, 1.22, 1)
        draw_basket(draw, pmx, pmy, .62, 1)

    if scene == 2 and "apple" in text and foreground:
        # Big apple travels from Kiki to Bobo's basket.
        progress_big = smoothstep(clamp((t-2.0)/4.0, 0, 1))
        progress_small = smoothstep(clamp((t-5.0)/4.0, 0, 1))

        kstart = (kx, ky + 80)
        big_target = (bx, by + 165)
        small_target = (mx, my + 165)

        big_x = lerp(kstart[0], big_target[0], progress_big)
        big_y = lerp(kstart[1], big_target[1], progress_big) - 80*math.sin(progress_big*math.pi)
        small_x = lerp(kstart[0]+25, small_target[0], progress_small)
        small_y = lerp(kstart[1]+15, small_target[1], progress_small) - 60*math.sin(progress_small*math.pi)

        draw_apple(*(
            draw, *P(big_x, big_y)
        ), .92 * current_zoom[0], 0)
        draw_apple(*(
            draw, *P(small_x, small_y)
        ), .48 * current_zoom[0], 0)

        # Front rims make the apples read as being inside the baskets.
        for x, y, scale in ((bx, by+150, 1.22), (mx, my+150, .62)):
            px, py = P(x, y)
            s = scale * current_zoom[0]
            draw.arc([px-80*s, py-25*s, px+80*s, py+35*s],
                     0, 180, fill=(125,75,40), width=max(3,int(5*s)))

    # --------------------------------------------------------
    # SCENE 3: Bobo and Mimi wear the two hats.
    # --------------------------------------------------------
    if scene == 3 and "hat" in text and foreground:
        # Bobo's very large yellow hat.
        bhx, bhy = P(bx, by - 10)
        draw_hat(draw, bhx, bhy, .82 * current_zoom[0], (248,205,70), True)

        # Mimi's small purple hat.
        mhx, mhy = P(mx, my - 10)
        draw_hat(draw, mhx, mhy, .43 * current_zoom[0], (155,90,210), True)

    # --------------------------------------------------------
    # Other described objects: handled generically for scenes that mention them.
    # --------------------------------------------------------
    if "watermelon" in text:
        px, py = P(700, 430)
        scale = 1.0 if any(w in text for w in ("big", "large", "very big", "giant")) else .7
        draw_watermelon(draw, px, py, scale * current_zoom[0])

    if "strawberry" in text:
        px, py = P(680, 440)
        scale = .55 if any(w in text for w in ("small", "tiny")) else .8
        draw_strawberry(draw, px, py, scale * current_zoom[0])

    if "leaf" in text:
        px, py = P(760, 430)
        draw_leaf(draw, px, py, .9 * current_zoom[0])

    if "flower" in text:
        px, py = P(760, 430)
        draw_flower(draw, px, py, .9 * current_zoom[0])

    if "book" in text:
        px, py = P(650, 445)
        draw_book(draw, px, py, .8 * current_zoom[0])

    if "cup" in text:
        px, py = P(650, 450)
        draw_cup(draw, px, py, .8 * current_zoom[0])

    # Generic basket fallback for future stories outside scenes 1/2.
    if scene not in (1, 2) and "basket" in text and foreground:
        px, py = P(650, 455)
        draw_basket(draw, px, py, .8 * current_zoom[0], 0)

    # Generic apple fallback for future stories.
    if scene not in (2,) and "apple" in text:
        px, py = P(760, 390)
        draw_apple(draw, px, py, .65 * current_zoom[0], 0)

    # Picnic blanket for scene descriptions that explicitly call for one.
    if "blanket" in text and not foreground:
        px, py = P(640, 500)
        w = 390 * current_zoom[0]
        h = 85 * current_zoom[0]
        draw.rounded_rectangle(
            [px-w, py-h, px+w, py+h],
            radius=max(8, int(18*current_zoom[0])),
            fill=(236,185,205),
            outline=(170,105,140),
            width=max(2, int(4*current_zoom[0])),
        )
        for xx in range(-2, 3):
            x = px + xx * 120 * current_zoom[0]
            draw.line(
                [(x, py-h), (x, py+h)],
                fill=(255,225,235),
                width=max(2, int(3*current_zoom[0]))
            )

def draw_action_effects(draw, story, scene, t):
    """Action effects that reinforce what the characters are doing."""
    descriptions = scene_text(story, scene)

    if any(w in descriptions for w in ("reach", "reaches", "hug", "hugs", "hold", "holding")):
        for i in range(4):
            a = t * 4 + i * 1.57
            x = 500 + math.cos(a) * 30
            y = 335 + math.sin(a) * 18
            draw.ellipse([x-3, y-3, x+3, y+3], fill=(255,235,100))

    if any(w in descriptions for w in ("flies", "fly", "flying", "flies down", "lands")):
        for i in range(3):
            x = 850 + i*18 + 10*math.sin(t*3+i)
            y = 310 + i*15
            draw.arc([x-12,y-8,x+12,y+8], 190, 350, fill=(255,255,255), width=2)


def draw_lesson_object(draw, lesson, scene, t, focus=0):
    text = str(lesson).lower()
    if any(w in text for w in ("count", "number", "numbers", "one", "two", "three")):
        for i in range(3):
            x = 510 + i*130
            y = 400 + 10*math.sin(t*2+i)
            draw.ellipse([x-38, y-38, x+38, y+38], fill=(245,180,70))
            text_center(draw, str(i+1), x, y-23, get_font(32, True), (70,70,90))
    elif any(w in text for w in ("shape", "circle", "square", "triangle")):
        x1, x2, x3 = 485, 640, 795
        ys = [400+10*math.sin(t*2+i) for i in range(3)]
        draw.ellipse([x1-38,ys[0]-38,x1+38,ys[0]+38],fill=(90,160,230))
        draw.rectangle([x2-38,ys[1]-38,x2+38,ys[1]+38],fill=(245,170,70))
        draw.polygon([(x3,ys[2]-45),(x3-45,ys[2]+38),(x3+45,ys[2]+38)],fill=(100,190,110))
    elif any(w in text for w in ("color", "colour", "red", "blue", "green", "yellow")):
        colors=[(235,70,70),(70,120,235),(70,180,100),(250,210,50)]
        for i,color in enumerate(colors):
            x=430+i*115; y=405+9*math.sin(t*2.1+i)
            draw.ellipse([x-32,y-32,x+32,y+32],fill=color)
    else:
        for i in range(5):
            x=440+i*105; y=405+12*math.sin(t*1.8+i)
            r=28; fill=(248,204,70)
            if i==int(focus)%5: r=35+4*math.sin(t*4); fill=(255,235,90)
            draw_star(draw,x,y,r,fill)


def draw_action_effects(draw, story, scene, t):
    """Small effects tied to actions rather than random decoration."""
    descriptions = str(
        story.get("scenes", [])[scene-1].get("visual_description","")
    ).lower() if story.get("scenes") else ""

    if any(w in descriptions for w in ("pick", "picks", "picking", "reach", "reaches")):
        for i in range(4):
            a = t*4 + i*1.57
            x = 540 + math.cos(a)*34
            y = 355 + math.sin(a)*22
            draw.ellipse([x-3,y-3,x+3,y+3], fill=(255,235,100))

    if any(w in descriptions for w in ("flies", "flies up", "flying", "flies down")):
        for i in range(3):
            x = 875 + i*16 + 10*math.sin(t*3+i)
            y = 315 + i*15
            draw.arc([x-12,y-8,x+12,y+8], 190, 350,
                     fill=(255,255,255), width=2)


# ============================================================
# EDUCATIONAL OBJECTS
# ============================================================

def draw_lesson_object(draw, lesson, scene, t, focus=0):
    text = str(lesson).lower()

    if any(w in text for w in ("count", "number", "numbers", "one", "two", "three")):
        for i in range(3):
            x = 510 + i*130
            y = 400 + 10*math.sin(t*2+i)
            draw.ellipse([x-38, y-38, x+38, y+38], fill=(245, 180, 70))
            text_center(draw, str(i+1), x, y-23, get_font(32, True), (70,70,90))

    elif any(w in text for w in ("shape", "circle", "square", "triangle")):
        x1, x2, x3 = 485, 640, 795
        ys = [
            400 + 10*math.sin(t*2),
            400 + 10*math.sin(t*2+1),
            400 + 10*math.sin(t*2+2),
        ]

        draw.ellipse([x1-38, ys[0]-38, x1+38, ys[0]+38], fill=(90,160,230))
        draw.rectangle([x2-38, ys[1]-38, x2+38, ys[1]+38], fill=(245,170,70))
        draw.polygon(
            [(x3, ys[2]-45), (x3-45, ys[2]+38), (x3+45, ys[2]+38)],
            fill=(100,190,110),
        )

    elif any(w in text for w in ("color", "colour", "red", "blue", "green", "yellow")):
        colors = [
            (235,70,70), (70,120,235),
            (70,180,100), (250,210,50),
        ]
        for i, color in enumerate(colors):
            x = 430 + i*115
            y = 405 + 9*math.sin(t*2.1+i)
            draw.ellipse([x-32, y-32, x+32, y+32], fill=color)

    else:
        # Generic concept: five stars with one highlighted.
        for i in range(5):
            x = 440 + i*105
            y = 405 + 12*math.sin(t*1.8+i)
            r = 28
            fill = (248,204,70)
            if i == int(focus) % 5:
                r = 35 + 4*math.sin(t*4)
                fill = (255,235,90)
            draw_star(draw, x, y, r, fill)


# ============================================================
# PARTICLES
# ============================================================

def draw_particles(draw, t, scene):
    for i in range(18):
        phase = i*.73 + scene
        x = 70 + (i*97) % 1140
        y = 145 + (i*61) % 300
        pulse = .5 + .5*math.sin(t*3 + phase)

        if pulse > .62:
            r = 2 + 4*pulse
            draw.ellipse(
                [x-r, y-r, x+r, y+r],
                fill=(255,255,245),
            )


# ============================================================
# CAMERA / CHARACTER STAGING
# ============================================================

def camera_state(scene, t):
    if scene == 1:
        x = 22*math.sin(t*.45)
        zoom = 1.0 + .018*math.sin(t*.55)
    elif scene == 2:
        x = 55*math.sin(t*.28)
        zoom = 1.0 + .028*math.sin(t*.42)
    elif scene == 3:
        x = -70*math.sin(t*.24)
        zoom = 1.0 + .035*math.sin(t*.38)
    else:
        x = 30*math.sin(t*.22)
        zoom = 1.0 + .045*math.sin(t*.32)

    return x, zoom


def character_positions(scene, t, duration):
    p = clamp(t / max(duration, .001), 0, 1)

    if scene == 1:
        # Bobo and Mimi are staged apart so the two baskets are unmistakable.
        bobo_x = lerp(180, 400, ease_out(clamp(t/2.5, 0, 1)))
        mimi_x = 735
        kiki_x = 1030
        kiki_y = 300 + 20*math.sin(t*2.0)
    elif scene == 2:
        # Kiki carries the apples from the right toward the two baskets.
        bobo_x = 400 + 12*math.sin(t*1.2)
        mimi_x = 735 + 10*math.sin(t*1.0 + 1)
        kiki_x = lerp(1030, 910, smoothstep(clamp(t/5.0, 0, 1)))
        kiki_y = lerp(245, 285, smoothstep(clamp(t/5.0, 0, 1))) + 24*math.sin(t*3)
    elif scene == 3:
        # The hats belong to Bobo and Mimi. Kiki stays in the background.
        bobo_x = 400 + 10*math.sin(t*.8)
        mimi_x = 735 + 10*math.sin(t*.7)
        kiki_x = 1030
        kiki_y = 300 + 18*math.sin(t*2.0)
    else:
        # Full group stays together for the picnic.
        sway = 28 * math.sin(t*1.4)
        bobo_x = 420 + sway
        mimi_x = 650 - sway*0.35
        kiki_x = 850 + sway*0.55
        kiki_y = 190 + 24*math.sin(t*3.5)

    return {
        "Bobo": (bobo_x, 275),
        "Mimi": (mimi_x, 280),
        "Kiki": (kiki_x, kiki_y),
    }

def draw_story_interactions(draw, story, scene, t, positions, world_point, zoom):
    """Foreground interaction cues matched to the actual scene description."""
    text = scene_text(story, scene)
    bx, by = positions["Bobo"]
    mx, my = positions["Mimi"]
    kx, ky = positions["Kiki"]

    def P(x, y):
        return world_point(x, y)

    if scene == 1 and "basket" in text:
        # Arms visually point toward the baskets.
        for x, y, side in ((bx, by, -1), (mx, my, 1)):
            px, py = P(x + side*55, y + 145)
            tx, ty = P(x + side*20, y + 155)
            draw.line(
                [(px,py),(tx,ty)],
                fill=(150,100,70) if x == bx else (245,245,245),
                width=max(6, int(12*zoom))
            )

    elif scene == 2 and "apple" in text:
        # A short wing-to-apple cue makes Kiki's carrying action readable.
        ax, ay = P(kx, ky + 80)
        draw.line(
            [P(kx+42,ky+78), (ax, ay)],
            fill=(55,145,220),
            width=max(4,int(7*zoom))
        )

    elif scene == 3 and "hat" in text:
        # Tiny sparkle cues around both hats reinforce that they are being worn.
        for x, y in ((bx,by-5),(mx,my-5)):
            px, py = P(x, y-55)
            r = 6*zoom
            draw.line([(px-r,py),(px+r,py)], fill=(255,240,120), width=max(2,int(3*zoom)))
            draw.line([(px,py-r),(px,py+r)], fill=(255,240,120), width=max(2,int(3*zoom)))

    elif scene == 4:
        # Kiki's happy flight circle above the group.
        cx, cy = P(650, 250)
        rx, ry = 250*zoom, 85*zoom
        draw.arc([cx-rx,cy-ry,cx+rx,cy+ry], 190, 350,
                 fill=(90,160,230), width=max(2,int(4*zoom)))


def render_frame(story, scene, t, scene_duration, total_duration):
    global current_zoom

    frame = Image.new("RGB", (WIDTH, HEIGHT), (255,255,255))
    draw = ImageDraw.Draw(frame)

    camera_x, zoom = camera_state(scene, t)
    current_zoom = (zoom,)

    draw_background(draw, scene, t, camera_x)

    # One coordinate system for everything. This prevents the old bug where
    # props stayed fixed while characters moved with the camera.
    def world_point(x, y):
        return (
            WIDTH/2 + (x - WIDTH/2 - camera_x)*zoom,
            GROUND_Y + (y - GROUND_Y)*zoom,
        )

    positions = character_positions(scene, t, scene_duration)

    # Concrete scene props behind characters.
    prop_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    pd = ImageDraw.Draw(prop_layer)
    draw_scene_props(pd, story, scene, t, world_point, foreground=False)
    frame = Image.alpha_composite(frame.convert("RGBA"), prop_layer).convert("RGB")

    # Effects behind the characters.
    fx = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    fd = ImageDraw.Draw(fx)
    draw_action_effects(fd, story, scene, t)
    draw_particles(fd, t, scene)
    frame = Image.alpha_composite(frame.convert("RGBA"), fx).convert("RGB")

    # Character gestures.
    bobo_gesture = .0
    mimi_gesture = .0
    if scene == 1:
        bobo_gesture = .55 + .12*math.sin(t*2)
        mimi_gesture = .35 + .12*math.sin(t*2 + 1.0)
    elif scene == 2:
        mimi_gesture = -.35 + .15*math.sin(t*3)
    elif scene == 3:
        bobo_gesture = .10 + .12*math.sin(t*2)
        mimi_gesture = -.10 + .12*math.sin(t*2 + 1.0)
    else:
        bobo_gesture = .35 + .55*math.sin(t*5)
        mimi_gesture = .25 + .55*math.sin(t*5+1.5)

    world = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    wd = ImageDraw.Draw(world)

    bx, by = positions["Bobo"]
    mx, my = positions["Mimi"]
    kx, ky = positions["Kiki"]

    def wp(x,y):
        return world_point(x,y)

    bxp,byp=wp(bx,by)
    mxp,myp=wp(mx,my)
    kxp,kyp=wp(kx,ky)

    if scene == 4:
        bobo_bounce=20*abs(math.sin(t*5.0))
        mimi_bounce=18*abs(math.sin(t*5.0+1.2))
    else:
        bobo_bounce=5*math.sin(t*6.5)
        mimi_bounce=4*math.sin(t*5.5)

    draw_bobo(wd,bxp,byp+bobo_bounce*zoom,scale=1.05*zoom,phase=t*6.8,wave=t*3.0,gesture=bobo_gesture)
    draw_mimi(wd,mxp,myp+mimi_bounce*zoom,scale=1.02*zoom,phase=t*4.2,wave=t*2.2,gesture=mimi_gesture)
    draw_kiki(wd,kxp,kyp,scale=.92*zoom,phase=t*7.0,flight=t)

    frame=Image.alpha_composite(frame.convert("RGBA"),world).convert("RGB")

    # Foreground props and interaction cues. These are deliberately after the
    # characters so held/worn props appear attached to them.
    fg=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
    fgd=ImageDraw.Draw(fg)
    draw_scene_props(fgd,story,scene,t,world_point,foreground=True)
    draw_story_interactions(fgd,story,scene,t,positions,world_point,zoom)
    frame=Image.alpha_composite(frame.convert("RGBA"),fg).convert("RGB")

    # Title.
    title=str(story.get("title","NobiNest Adventure"))
    if len(title)>48: title=title[:45]+"..."
    text_center(ImageDraw.Draw(frame),title,WIDTH/2,18,TITLE_FONT,(55,70,90))

    # Keep the actual scene unobstructed. Concrete stories do not need a lesson card.
    return frame


# ============================================================
# AUDIO / SUBTITLES
# ============================================================

def audio_duration():
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(AUDIO_FILE),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    value = result.stdout.strip()

    if not value:
        raise RuntimeError("Could not determine narration duration.")

    return float(value)


def timestamp(seconds):
    ms = int(round((seconds - int(seconds))*1000))
    total = int(seconds)

    if ms >= 1000:
        total += 1
        ms = 0

    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60

    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def create_subtitles(story, duration):
    chunks = []

    for scene in story.get("scenes", []):
        text = str(scene.get("narration","")).strip()
        if text:
            chunks.append(text)

    song = story.get("song", {})
    if isinstance(song, dict):
        text = str(song.get("lyrics","")).strip()
        if text:
            chunks.append(text)

    ending = str(story.get("ending","")).strip()
    if ending:
        chunks.append(ending)

    words = " ".join(chunks).split()

    if not words:
        return

    # Short readable chunks for preschool viewers.
    chunk_size = 5
    groups = [
        words[i:i+chunk_size]
        for i in range(0, len(words), chunk_size)
    ]

    # Estimate timing from word count rather than making every
    # subtitle the same length.
    weights = [max(1, len(g)) for g in groups]
    total_weight = sum(weights)

    with open(SRT_FILE, "w", encoding="utf-8") as f:
        current = 0.0

        for index, group in enumerate(groups, 1):
            span = duration * weights[index-1] / total_weight
            start = current
            end = min(duration, current + span)
            current = end

            f.write(f"{index}\n")
            f.write(f"{timestamp(start)} --> {timestamp(end)}\n")
            f.write(" ".join(group))
            f.write("\n\n")


# ============================================================
# FFMPEG
# ============================================================

def render_video(story, duration):
    print("==============================================")
    print("NOBINEST 2D MOTION RENDERER v8 FINAL")
    print("==============================================")
    print(f"Resolution : {WIDTH}x{HEIGHT}")
    print(f"FPS        : {FPS}")
    print(f"Duration   : {duration:.2f}s")

    # Escape subtitle path for FFmpeg filter syntax.
    subtitle_path = (
        str(SRT_FILE)
        .replace("\\", "/")
        .replace(":", r"\:")
        .replace("'", r"\'")
    )

    subtitle_filter = (
        f"subtitles='{subtitle_path}':force_style="
        "'FontName=DejaVu Sans,"
        "FontSize=18,"
        "Bold=1,"
        "Alignment=2,"
        "MarginV=28,"
        "Outline=2,"
        "Shadow=1'"
    )

    command = [
        "ffmpeg",
        "-y",

        # Video from Python.
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",

        # Narration.
        "-i", str(AUDIO_FILE),

        "-vf", subtitle_filter,

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "128k",

        "-t", f"{duration:.3f}",
        "-shortest",

        str(VIDEO_FILE),
    ]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    total_frames = max(1, int(math.ceil(duration*FPS)))

    try:
        for i in range(total_frames):
            current = i/FPS

            scene = min(
                4,
                int((current/duration)*4)+1,
            )

            scene_duration = duration/4
            local_t = current - (scene-1)*scene_duration

            frame = render_frame(
                story,
                scene,
                local_t,
                scene_duration,
                duration,
            )

            process.stdin.write(frame.tobytes())

            if i % FPS == 0:
                pct = 100*i/total_frames
                print(
                    f"Rendered {current:6.1f}s / "
                    f"{duration:6.1f}s "
                    f"({pct:5.1f}%)"
                )

        process.stdin.close()

        stderr = process.stderr.read().decode(
            "utf-8", errors="replace"
        )

        code = process.wait()

        if code != 0:
            print(stderr)
            raise RuntimeError(
                f"FFmpeg failed with exit code {code}"
            )

    except BrokenPipeError:
        stderr = process.stderr.read().decode(
            "utf-8", errors="replace"
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
    print("="*60)
    print("NOBINEST KIDS ANIMATED VIDEO RENDERER")
    print("="*60)

    if not STORY_FILE.exists():
        raise FileNotFoundError(f"Missing {STORY_FILE}")

    if not AUDIO_FILE.exists():
        raise FileNotFoundError(f"Missing {AUDIO_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(STORY_FILE, "r", encoding="utf-8") as f:
        story = json.load(f)

    duration = audio_duration()

    print(f"Story    : {story.get('title','Untitled')}")
    print(f"Lesson   : {story.get('lesson','')}")
    print(f"Audio    : {duration:.2f}s")

    # The workflow separately verifies 60-90 seconds.
    # Fail here too, so a bad episode never gets silently rendered.
    if duration < MIN_DURATION:
        raise RuntimeError(
            f"Audio is only {duration:.2f}s. "
            f"NobiNest episodes must be at least {MIN_DURATION:.0f}s."
        )

    if duration > MAX_DURATION:
        raise RuntimeError(
            f"Audio is {duration:.2f}s. "
            f"NobiNest episodes must not exceed {MAX_DURATION:.0f}s."
        )

    print("Creating subtitles...")
    create_subtitles(story, duration)

    print("Rendering:")
    print("  walking cycles")
    print("  hopping cycles")
    print("  wing flapping")
    print("  flying movement")
    print("  arm gestures")
    print("  object animation")
    print("  camera pan")
    print("  camera zoom")
    print("  parallax background")
    print("  moving clouds")
    print("  swaying grass")
    print("  swaying flowers")
    print("  particles")
    print("  animated lesson objects")

    render_video(story, duration)

    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "Renderer finished but MP4 was not created."
        )

    size_mb = VIDEO_FILE.stat().st_size/(1024*1024)

    print("")
    print("="*60)
    print("NOBINEST EPISODE CREATED")
    print("="*60)
    print(f"Video     : {VIDEO_FILE}")
    print(f"Subtitles : {SRT_FILE}")
    print(f"Size      : {size_mb:.2f} MB")
    print(f"Duration  : {duration:.2f}s")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print("RENDERER ERROR")
        print(str(exc))
        sys.exit(1)
