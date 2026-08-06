import json
import math
import os
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT_DIR = Path("output")
STORY_FILE = OUTPUT_DIR / "story.json"
AUDIO_FILE = OUTPUT_DIR / "narration.mp3"

VIDEO_FILE = OUTPUT_DIR / "nobinnest_episode.mp4"
SRT_FILE = OUTPUT_DIR / "narration.srt"

SCENES_DIR = OUTPUT_DIR / "scenes"


WIDTH = 1280
HEIGHT = 720
FPS = 30


# ---------------------------------------------------------
# FONTS
# ---------------------------------------------------------

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def get_font(size, bold=True):
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


# ---------------------------------------------------------
# BASIC DRAWING
# ---------------------------------------------------------

def rounded_rectangle(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def draw_text_center(draw, text, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), text, font=font, fill=fill)


# ---------------------------------------------------------
# BOBO
# ---------------------------------------------------------

def draw_bobo(draw, x, y, scale=1.0):
    """
    Simple consistent cartoon representation of Bobo.
    Brown bear + yellow scarf.
    """

    s = scale

    # body
    body = [
        x - int(65 * s),
        y + int(75 * s),
        x + int(65 * s),
        y + int(230 * s),
    ]

    draw.ellipse(body, fill=(150, 95, 55))

    # ears
    draw.ellipse(
        [
            x - int(65 * s),
            y,
            x - int(5 * s),
            y + int(60 * s),
        ],
        fill=(150, 95, 55),
    )

    draw.ellipse(
        [
            x + int(5 * s),
            y,
            x + int(65 * s),
            y + int(60 * s),
        ],
        fill=(150, 95, 55),
    )

    # head
    draw.ellipse(
        [
            x - int(75 * s),
            y + int(20 * s),
            x + int(75 * s),
            y + int(150 * s),
        ],
        fill=(165, 105, 60),
    )

    # eyes
    eye_y = y + int(75 * s)

    draw.ellipse(
        [
            x - int(35 * s),
            eye_y - int(8 * s),
            x - int(19 * s),
            eye_y + int(8 * s),
        ],
        fill="black",
    )

    draw.ellipse(
        [
            x + int(19 * s),
            eye_y - int(8 * s),
            x + int(35 * s),
            eye_y + int(8 * s),
        ],
        fill="black",
    )

    # muzzle
    draw.ellipse(
        [
            x - int(30 * s),
            y + int(92 * s),
            x + int(30 * s),
            y + int(130 * s),
        ],
        fill=(210, 155, 100),
    )

    # nose
    draw.ellipse(
        [
            x - int(9 * s),
            y + int(100 * s),
            x + int(9 * s),
            y + int(114 * s),
        ],
        fill="black",
    )

    # yellow scarf
    draw.rectangle(
        [
            x - int(65 * s),
            y + int(145 * s),
            x + int(65 * s),
            y + int(175 * s),
        ],
        fill=(245, 205, 40),
    )

    # scarf tail
    draw.polygon(
        [
            (x + int(30 * s), y + int(170 * s)),
            (x + int(75 * s), y + int(215 * s)),
            (x + int(50 * s), y + int(175 * s)),
        ],
        fill=(245, 205, 40),
    )

    # arms
    draw.ellipse(
        [
            x - int(95 * s),
            y + int(110 * s),
            x - int(50 * s),
            y + int(170 * s),
        ],
        fill=(150, 95, 55),
    )

    draw.ellipse(
        [
            x + int(50 * s),
            y + int(110 * s),
            x + int(95 * s),
            y + int(170 * s),
        ],
        fill=(150, 95, 55),
    )

    # feet
    draw.ellipse(
        [
            x - int(65 * s),
            y + int(205 * s),
            x - int(5 * s),
            y + int(245 * s),
        ],
        fill=(120, 75, 45),
    )

    draw.ellipse(
        [
            x + int(5 * s),
            y + int(205 * s),
            x + int(65 * s),
            y + int(245 * s),
        ],
        fill=(120, 75, 45),
    )


# ---------------------------------------------------------
# MIMI
# ---------------------------------------------------------

def draw_mimi(draw, x, y, scale=1.0):
    """
    White rabbit + pink ears + purple backpack.
    """

    s = scale

    # backpack
    rounded_rectangle(
        draw,
        [
            x + int(35 * s),
            y + int(115 * s),
            x + int(90 * s),
            y + int(190 * s),
        ],
        int(15 * s),
        fill=(125, 75, 170),
    )

    # ears
    draw.ellipse(
        [
            x - int(55 * s),
            y - int(100 * s),
            x - int(5 * s),
            y + int(45 * s),
        ],
        fill="white",
        outline=(220, 220, 220),
    )

    draw.ellipse(
        [
            x + int(5 * s),
            y - int(100 * s),
            x + int(55 * s),
            y + int(45 * s),
        ],
        fill="white",
        outline=(220, 220, 220),
    )

    # pink inner ears
    draw.ellipse(
        [
            x - int(42 * s),
            y - int(80 * s),
            x - int(18 * s),
            y + int(25 * s),
        ],
        fill=(250, 170, 185),
    )

    draw.ellipse(
        [
            x + int(18 * s),
            y - int(80 * s),
            x + int(42 * s),
            y + int(25 * s),
        ],
        fill=(250, 170, 185),
    )

    # body
    draw.ellipse(
        [
            x - int(60 * s),
            y + int(90 * s),
            x + int(60 * s),
            y + int(235 * s),
        ],
        fill="white",
        outline=(220, 220, 220),
    )

    # head
    draw.ellipse(
        [
            x - int(70 * s),
            y,
            x + int(70 * s),
            y + int(135 * s),
        ],
        fill="white",
        outline=(220, 220, 220),
    )

    # eyes
    eye_y = y + int(65 * s)

    draw.ellipse(
        [
            x - int(32 * s),
            eye_y - int(8 * s),
            x - int(17 * s),
            eye_y + int(8 * s),
        ],
        fill="black",
    )

    draw.ellipse(
        [
            x + int(17 * s),
            eye_y - int(8 * s),
            x + int(32 * s),
            eye_y + int(8 * s),
        ],
        fill="black",
    )

    # nose
    draw.ellipse(
        [
            x - int(8 * s),
            y + int(80 * s),
            x + int(8 * s),
            y + int(94 * s),
        ],
        fill=(245, 150, 170),
    )

    # arms
    draw.ellipse(
        [
            x - int(88 * s),
            y + int(120 * s),
            x - int(45 * s),
            y + int(175 * s),
        ],
        fill="white",
        outline=(220, 220, 220),
    )

    draw.ellipse(
        [
            x + int(45 * s),
            y + int(120 * s),
            x + int(88 * s),
            y + int(175 * s),
        ],
        fill="white",
        outline=(220, 220, 220),
    )


# ---------------------------------------------------------
# KIKI
# ---------------------------------------------------------

def draw_kiki(draw, x, y, scale=1.0):
    """
    Yellow bird + blue wings + orange beak.
    """

    s = scale

    # body
    draw.ellipse(
        [
            x - int(60 * s),
            y + int(45 * s),
            x + int(60 * s),
            y + int(200 * s),
        ],
        fill=(250, 220, 45),
    )

    # head
    draw.ellipse(
        [
            x - int(70 * s),
            y - int(20 * s),
            x + int(70 * s),
            y + int(110 * s),
        ],
        fill=(255, 225, 55),
    )

    # blue wings
    draw.ellipse(
        [
            x - int(100 * s),
            y + int(75 * s),
            x - int(30 * s),
            y + int(155 * s),
        ],
        fill=(60, 150, 220),
    )

    draw.ellipse(
        [
            x + int(30 * s),
            y + int(75 * s),
            x + int(100 * s),
            y + int(155 * s),
        ],
        fill=(60, 150, 220),
    )

    # eyes
    draw.ellipse(
        [
            x - int(35 * s),
            y + int(35 * s),
            x - int(18 * s),
            y + int(52 * s),
        ],
        fill="black",
    )

    draw.ellipse(
        [
            x + int(18 * s),
            y + int(35 * s),
            x + int(35 * s),
            y + int(52 * s),
        ],
        fill="black",
    )

    # beak
    draw.polygon(
        [
            (x, y + int(60 * s)),
            (x + int(50 * s), y + int(75 * s)),
            (x, y + int(90 * s)),
        ],
        fill=(240, 130, 35),
    )

    # feet
    draw.ellipse(
        [
            x - int(45 * s),
            y + int(180 * s),
            x - int(5 * s),
            y + int(205 * s),
        ],
        fill=(240, 130, 35),
    )

    draw.ellipse(
        [
            x + int(5 * s),
            y + int(180 * s),
            x + int(45 * s),
            y + int(205 * s),
        ],
        fill=(240, 130, 35),
    )


# ---------------------------------------------------------
# SCENE BACKGROUNDS
# ---------------------------------------------------------

def draw_background(draw, scene_number):
    backgrounds = [
        (190, 225, 250),
        (205, 240, 195),
        (250, 225, 175),
        (225, 210, 245),
    ]

    sky = backgrounds[(scene_number - 1) % len(backgrounds)]

    draw.rectangle(
        [0, 0, WIDTH, HEIGHT],
        fill=sky,
    )

    # ground
    draw.rectangle(
        [0, 520, WIDTH, HEIGHT],
        fill=(135, 195, 110),
    )

    # sun
    draw.ellipse(
        [1050, 60, 1160, 170],
        fill=(255, 220, 80),
    )

    # clouds
    for cx, cy in [(180, 120), (420, 90), (780, 140)]:
        draw.ellipse(
            [cx, cy, cx + 100, cy + 55],
            fill="white",
        )
        draw.ellipse(
            [cx + 35, cy - 20, cx + 135, cy + 55],
            fill="white",
        )


# ---------------------------------------------------------
# SCENE GENERATION
# ---------------------------------------------------------

def create_scene(scene_number, story):
    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        "white",
    )

    draw = ImageDraw.Draw(image)

    draw_background(
        draw,
        scene_number,
    )

    title_font = get_font(42)
    small_font = get_font(28)

    title = story.get("title", "NobiNest Adventure")

    draw_text_center(
        draw,
        title,
        20,
        title_font,
        (45, 60, 80),
    )

    # Character placement changes slightly by scene
    if scene_number == 1:
        draw_bobo(draw, 350, 300, 1.15)
        draw_mimi(draw, 640, 330, 1.05)
        draw_kiki(draw, 900, 350, 1.0)

    elif scene_number == 2:
        draw_bobo(draw, 300, 330, 1.1)
        draw_mimi(draw, 650, 300, 1.1)
        draw_kiki(draw, 980, 320, 1.0)

    elif scene_number == 3:
        draw_bobo(draw, 420, 320, 1.1)
        draw_mimi(draw, 800, 320, 1.1)
        draw_kiki(draw, 1030, 360, 0.9)

    else:
        draw_bobo(draw, 350, 315, 1.1)
        draw_mimi(draw, 650, 310, 1.1)
        draw_kiki(draw, 950, 320, 1.0)

    scene = story["scenes"][scene_number - 1]

    # Educational lesson card
    lesson = story.get("lesson", "")

    card = [
        80,
        570,
        WIDTH - 80,
        690,
    ]

    rounded_rectangle(
        draw,
        card,
        25,
        fill=(255, 255, 255),
        outline=(80, 100, 120),
        width=2,
    )

    lesson_text = f"Lesson: {lesson}"

    wrapped = textwrap.fill(
        lesson_text,
        width=85,
    )

    draw.multiline_text(
        (110, 595),
        wrapped,
        font=small_font,
        fill=(40, 50, 60),
        spacing=5,
    )

    filename = SCENES_DIR / f"scene_{scene_number}.png"

    image.save(
        filename,
        quality=95,
    )

    return filename


# ---------------------------------------------------------
# AUDIO DURATION
# ---------------------------------------------------------

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

    return float(result.stdout.strip())


# ---------------------------------------------------------
# SRT
# ---------------------------------------------------------

def format_timestamp(seconds):
    milliseconds = int(
        round((seconds - int(seconds)) * 1000)
    )

    total_seconds = int(seconds)

    hours = total_seconds // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    secs = total_seconds % 60

    if milliseconds >= 1000:
        milliseconds = 0
        secs += 1

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


def create_subtitles(story, duration):
    all_text = []

    for scene in story["scenes"]:
        all_text.append(
            scene["narration"]
        )

    if story.get("song"):
        all_text.append(
            story["song"].get("lyrics", "")
        )

    if story.get("ending"):
        all_text.append(
            story["ending"]
        )

    full_text = " ".join(
        all_text
    ).strip()

    words = full_text.split()

    if not words:
        return

    # Around 7 words per subtitle
    chunk_size = 7

    chunks = [
        words[i:i + chunk_size]
        for i in range(
            0,
            len(words),
            chunk_size,
        )
    ]

    chunk_duration = duration / len(chunks)

    with open(
        SRT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        for index, chunk in enumerate(chunks, 1):

            start = index - 1
            start_time = start * chunk_duration
            end_time = min(
                duration,
                index * chunk_duration,
            )

            text = " ".join(chunk)

            file.write(
                f"{index}\n"
            )

            file.write(
                f"{format_timestamp(start_time)} --> "
                f"{format_timestamp(end_time)}\n"
            )

            file.write(
                f"{text}\n\n"
            )


# ---------------------------------------------------------
# CREATE VIDEO
# ---------------------------------------------------------

def create_video(duration):
    scene_duration = duration / 4

    concat_file = OUTPUT_DIR / "scenes.txt"

    with open(
        concat_file,
        "w",
        encoding="utf-8",
    ) as file:

        for number in range(1, 5):

            scene_path = (
                SCENES_DIR
                / f"scene_{number}.png"
            )

            file.write(
                f"file '{scene_path.resolve()}'\n"
            )

            file.write(
                f"duration {scene_duration:.3f}\n"
            )

        # Repeat last frame so ffmpeg respects
        # the final duration.
        last_scene = (
            SCENES_DIR / "scene_4.png"
        )

        file.write(
            f"file '{last_scene.resolve()}'\n"
        )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-i",
        str(AUDIO_FILE),

        "-vf",
        (
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "format=yuv420p,"
            "subtitles=output/narration.srt:"
            "force_style='FontName=DejaVu Sans,"
            "FontSize=22,"
            "Bold=1,"
            "Alignment=2,"
            "MarginV=35'"
        ),

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-shortest",

        str(VIDEO_FILE),
    ]

    print("Creating final MP4...")

    subprocess.run(
        command,
        check=True,
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 50)
    print("NOBINEST VIDEO RENDERER")
    print("=" * 50)

    if not STORY_FILE.exists():
        raise FileNotFoundError(
            f"Missing {STORY_FILE}"
        )

    if not AUDIO_FILE.exists():
        raise FileNotFoundError(
            f"Missing {AUDIO_FILE}"
        )

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    SCENES_DIR.mkdir(
        exist_ok=True
    )

    with open(
        STORY_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        story = json.load(file)

    print("Creating 4 illustrated scenes...")

    for scene_number in range(1, 5):

        create_scene(
            scene_number,
            story,
        )

        print(
            f"Created scene {scene_number}"
        )

    print("Reading narration duration...")

    duration = get_audio_duration()

    print(
        f"Audio duration: {duration:.2f} seconds"
    )

    print("Creating subtitles...")

    create_subtitles(
        story,
        duration,
    )

    print("Creating video...")

    create_video(
        duration,
    )

    print("=" * 50)
    print("VIDEO CREATED SUCCESSFULLY")
    print("=" * 50)

    print(
        f"Video: {VIDEO_FILE}"
    )

    print(
        f"Subtitles: {SRT_FILE}"
    )


if __name__ == "__main__":
    main()
