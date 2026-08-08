import json
import math
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ============================================================
# NOBINEST 2D MOTION RENDERER v6 v6
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

def draw_story_objects(draw, story, scene, t):
    """Interpret common preschool nouns from the generated visual descriptions."""
    descriptions = " ".join(
        str(s.get("visual_description",""))
        for s in story.get("scenes", [])
    ).lower()
    lesson = str(story.get("lesson","")).lower()
    all_text = descriptions + " " + lesson

    # Keep the important object visible in the same visual world as the characters.
    if "tree" in all_text:
        draw_tree(draw, 1080, 245, 0.82)

    if "apple" in all_text:
        # Three apples are introduced on the branch in scene 1 and collected afterward.
        branch_y = 265
        apple_xs = [1010, 1080, 1150]
        visible = 3
        if scene == 2:
            visible = 2 if t > 1.0 else 3
        elif scene >= 3:
            visible = 1 if scene == 3 and t < 2.0 else 0

        # Branch
        draw.line([(960, branch_y+20),(1190,branch_y+20)],
                  fill=(105,70,42), width=10)

        for i, x in enumerate(apple_xs):
            if i < visible:
                draw_apple(draw, x, branch_y-15, 0.58,
                           5*math.sin(t*2+i))

    if "basket" in all_text:
        apples = 0
        if scene >= 2:
            if scene == 2:
                apples = 1 if t < 3.5 else 2
            else:
                apples = 3
        draw_basket(draw, 565, 465, 0.72, apples)

    # Simple number badges only when the lesson is actually about counting.
    if any(w in lesson for w in ("count", "number", "one", "two", "three")):
        count = 3 if scene >= 3 else (1 if scene == 2 else 0)
        for i in range(count):
            x = 430 + i*65
            y = 445 + 7*math.sin(t*2+i)
            draw.ellipse([x-20,y-20,x+20,y+20], fill=(245,180,70))
            text_center(draw, str(i+1), x, y-13,
                        get_font(21, True), (70,70,90))

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
        bobo_x = lerp(-170, 350, ease_out(clamp(t/3.5, 0, 1)))
        mimi_x = 670
        kiki_x = 970
        kiki_y = 285 + 25*math.sin(t*2.0)

    elif scene == 2:
        bobo_x = lerp(350, 455, smoothstep(p))
        mimi_x = lerp(670, 620, smoothstep(p))
        kiki_x = lerp(970, 820, smoothstep(p))
        kiki_y = 285 + 30*math.sin(t*2.5)

    elif scene == 3:
        bobo_x = lerp(455, 390, smoothstep(p))
        mimi_x = lerp(620, 700, smoothstep(p))
        kiki_x = 900 + 80*math.sin(t*.9)
        kiki_y = 235 + 50*math.sin(t*1.7)

    else:
        bobo_x = lerp(390, 450, smoothstep(p))
        mimi_x = lerp(700, 650, smoothstep(p))
        kiki_x = lerp(900, 820, smoothstep(p))
        kiki_y = 255 + 35*math.sin(t*1.8)

    return {
        "Bobo": (bobo_x, 275),
        "Mimi": (mimi_x, 280),
        "Kiki": (kiki_x, kiki_y),
    }



# ============================================================
# EXPLICIT CHARACTER / OBJECT INTERACTIONS
# ============================================================

def draw_story_interactions(draw, story, scene, t, positions, camera_x, zoom):
    """Make the generated story visible through concrete actions."""
    text = " ".join(
        str(s.get("visual_description", "")) + " " + str(s.get("narration", ""))
        for s in story.get("scenes", [])
    ).lower()

    def wp(x, y):
        return (
            WIDTH/2 + (x - WIDTH/2 - camera_x) * zoom,
            GROUND_Y + (y - GROUND_Y) * zoom,
        )

    bx, by = positions["Bobo"]
    mx, my = positions["Mimi"]
    kx, ky = positions["Kiki"]

    # Scene 2: Bobo reaches toward the basket and carries the first apple.
    if scene == 2 and "apple" in text:
        progress = clamp((t - 0.8) / 3.0, 0, 1)
        hand_x = bx + 72
        hand_y = by + 145
        basket_x, basket_y = 565, 430

        # Apple travels from the tree area to Bobo's hand, then toward basket.
        if progress < 0.55:
            q = ease_in_out(progress / 0.55)
            sx, sy = 1035, 245
            ex, ey = hand_x, hand_y
        else:
            q = ease_in_out((progress - 0.55) / 0.45)
            sx, sy = hand_x, hand_y
            ex, ey = basket_x - 20, basket_y + 8

        ax = lerp(sx, ex, q)
        ay = lerp(sy, ey, q) - 35 * math.sin(q * math.pi)
        px, py = wp(ax, ay)
        draw_apple(draw, px, py, 0.34 * zoom)

        # Reach lines make the action readable.
        if 0.05 < progress < 0.7:
            hx, hy = wp(hand_x, hand_y)
            draw.line([(hx-18*zoom, hy-10*zoom), (px,py)],
                      fill=(105,65,40), width=max(3,int(7*zoom)))

    # Scene 3: Mimi holds the basket while Bobo adds apples.
    if scene == 3 and "basket" in text:
        bxw, byw = wp(565, 430)
        # A small handle highlight and gentle lift make the basket feel held.
        lift = 5 * math.sin(t * 2.5)
        draw.arc(
            [bxw-48*zoom, byw-55*zoom+lift,
             bxw+48*zoom, byw+15*zoom+lift],
            180, 360,
            fill=(125,80,45),
            width=max(2,int(5*zoom))
        )

        # Bobo presents an apple toward the basket.
        if t > 0.7:
            axw, ayw = wp(bx + 58, by + 125)
            draw_apple(draw, axw, ayw, 0.31*zoom, 2*math.sin(t*4))

    # Scene 3: Kiki flies down with the final apple.
    if scene == 3 and "kiki" in text and "apple" in text:
        q = clamp((t - 1.2) / 3.0, 0, 1)
        # Kiki's position is already animated. Put the final apple at its beak.
        if q > 0.15:
            kxp, kyp = wp(kx + 45, ky + 55)
            draw_apple(draw, kxp, kyp, 0.28*zoom, 2*math.sin(t*5))

    # Scene 4: the completed basket is the focus of the celebration.
    if scene == 4 and "three" in text and "apple" in text:
        cx, cy = wp(565, 430)
        pulse = 1.0 + 0.08*math.sin(t*4)
        # Number 3 above the basket.
        r = 25 * zoom * pulse
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(245,180,70))
        text_center(draw, "3", cx, cy-r*0.72,
                    get_font(max(14,int(24*zoom)), True), (70,70,90))

        # Celebration arcs.
        for i in range(5):
            a = t*2 + i*1.2
            sx = cx + math.cos(a)*70*zoom
            sy = cy - 30*zoom + math.sin(a)*35*zoom
            draw.ellipse([sx-3*zoom,sy-3*zoom,sx+3*zoom,sy+3*zoom],
                         fill=(255,215,70))


# ============================================================
# SCENE FRAME
# ============================================================

def render_frame(story, scene, t, scene_duration, total_duration):
    frame = Image.new("RGB", (WIDTH, HEIGHT), (255,255,255))
    draw = ImageDraw.Draw(frame)

    camera_x, zoom = camera_state(scene, t)

    draw_background(draw, scene, t, camera_x)

    # Story-specific props are drawn first so characters can interact with them.
    draw_story_objects(draw, story, scene, t)
    lesson = str(story.get("lesson", "")).lower()
    concrete_story = any(
        w in (" ".join(str(s.get("visual_description","")) for s in story.get("scenes", []))).lower()
        for w in ("apple", "basket", "tree", "ball", "flower", "book", "toy", "cup", "leaf")
    )
    if not concrete_story:
        draw_lesson_object(
            draw,
            story.get("lesson", ""),
            scene,
            t,
            focus=int(t*1.2),
        )
    draw_action_effects(draw, story, scene, t)
    draw_particles(draw, t, scene)

    positions = character_positions(scene, t, scene_duration)

    # Scene-specific gestures.
    bobo_gesture = 0.0
    mimi_gesture = 0.0

    if scene == 1:
        bobo_gesture = .45 + .12*math.sin(t*2)
    elif scene == 2:
        bobo_gesture = .18
        mimi_gesture = -.35
    elif scene == 3:
        bobo_gesture = -.15
        mimi_gesture = -.5
    else:
        bobo_gesture = .35
        mimi_gesture = .25

    # Draw characters into a transparent world layer.
    world = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    wd = ImageDraw.Draw(world)

    bx, by = positions["Bobo"]
    mx, my = positions["Mimi"]
    kx, ky = positions["Kiki"]

    # Apply actual camera zoom and pan.
    def world_point(x, y):
        return (
            WIDTH/2 + (x - WIDTH/2 - camera_x)*zoom,
            GROUND_Y + (y - GROUND_Y)*zoom,
        )

    bxp, byp = world_point(bx, by)
    mxp, myp = world_point(mx, my)
    kxp, kyp = world_point(kx, ky)

    bobo_bounce = 6*math.sin(t*7)
    mimi_bounce = 4*math.sin(t*5.5)

    draw_bobo(
        wd,
        bxp,
        byp + bobo_bounce*zoom,
        scale=1.05*zoom,
        phase=t*6.8,
        wave=t*3.0,
        gesture=bobo_gesture,
    )

    draw_mimi(
        wd,
        mxp,
        myp + mimi_bounce*zoom,
        scale=1.02*zoom,
        phase=t*4.2,
        wave=t*2.2,
        gesture=mimi_gesture,
    )

    draw_kiki(
        wd,
        kxp,
        kyp,
        scale=.92*zoom,
        phase=t*7.0,
        flight=t,
    )

    # Draw interaction details over the characters/world so objects visibly
    # connect to the actions being narrated.
    draw_story_interactions(
        wd,
        story,
        scene,
        t,
        positions,
        camera_x,
        zoom,
    )

    frame = Image.alpha_composite(frame.convert("RGBA"), world).convert("RGB")

    # Scene title.
    title = str(story.get("title", "NobiNest Adventure"))
    if len(title) > 48:
        title = title[:45] + "..."

    text_center(
        ImageDraw.Draw(frame),
        title,
        WIDTH/2,
        18,
        TITLE_FONT,
        (55,70,90),
    )

    # Avoid a large lesson card behind subtitles. For concrete stories,
    # keep the frame clean and let the narration/subtitles carry the lesson.
    concrete_story = any(
        w in (" ".join(
            str(s.get("visual_description","")) for s in story.get("scenes", [])
        )).lower()
        for w in ("apple","basket","tree","ball","flower","book","toy","cup","leaf")
    )

    if not concrete_story:
        badge = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        bd = ImageDraw.Draw(badge)
        rounded(
            bd,
            [55, 575, WIDTH-55, 660],
            18,
            (255,255,255,220),
            (70,90,110,220),
            2,
        )
        lines = wrap_text(
            bd,
            "Lesson: " + str(story.get("lesson","")),
            LESSON_FONT,
            WIDTH-150,
        )
        y = 590
        for line in lines[:2]:
            text_center(bd, line, WIDTH/2, y, LESSON_FONT, (40,50,65,220))
            y += 27
        frame = Image.alpha_composite(frame.convert("RGBA"), badge).convert("RGB")

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
    print("NOBINEST 2D MOTION RENDERER v6")
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
