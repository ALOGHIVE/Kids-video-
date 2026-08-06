import asyncio
import json
import os
import re

import edge_tts


OUTPUT_DIR = "output"

STORY_FILE = os.path.join(
    OUTPUT_DIR,
    "story.json"
)

AUDIO_FILE = os.path.join(
    OUTPUT_DIR,
    "narration.mp3"
)

SRT_FILE = os.path.join(
    OUTPUT_DIR,
    "narration.srt"
)

TIMING_FILE = os.path.join(
    OUTPUT_DIR,
    "timing.json"
)


VOICE = "en-US-AriaNeural"

RATE = "-5%"
PITCH = "+2Hz"
VOLUME = "+0%"


def load_story():

    with open(
        STORY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def build_narration_parts(story):

    parts = []

    for scene in story["scenes"]:

        parts.append({
            "type": "scene",
            "scene_number": scene["scene_number"],
            "text": clean_text(
                scene["narration"]
            )
        })

    parts.append({
        "type": "song",
        "text": clean_text(
            story["song"]["lyrics"]
        )
    })

    parts.append({
        "type": "ending",
        "text": clean_text(
            story["ending"]
        )
    })

    return parts


def combine_text(parts):

    return "\n\n".join(
        part["text"]
        for part in parts
        if part["text"]
    )


def format_timestamp(seconds):

    milliseconds = int(
        round(seconds * 1000)
    )

    hours = milliseconds // 3600000

    milliseconds %= 3600000

    minutes = milliseconds // 60000

    milliseconds %= 60000

    secs = milliseconds // 1000

    milliseconds %= 1000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


async def generate_audio(text):

    communicator = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME
    )

    boundaries = []

    async for item in communicator.stream():

        if item["type"] == "audio":

            with open(
                AUDIO_FILE,
                "ab"
            ) as file:

                file.write(
                    item["data"]
                )

        elif item["type"] == "WordBoundary":

            boundaries.append(item)

        elif item["type"] == "SentenceBoundary":

            boundaries.append(item)

    return boundaries


def build_sentence_timings(boundaries):

    sentences = []

    for item in boundaries:

        if item["type"] != "SentenceBoundary":
            continue

        start = item["offset"] / 10_000_000

        duration = item["duration"] / 10_000_000

        end = start + duration

        sentences.append({
            "start": start,
            "end": end,
            "text": item["text"].strip()
        })

    return sentences


def split_into_sentences(text):

    pieces = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    return [
        clean_text(piece)
        for piece in pieces
        if clean_text(piece)
    ]


def build_srt(sentences):

    lines = []

    for index, sentence in enumerate(
        sentences,
        start=1
    ):

        lines.append(
            str(index)
        )

        lines.append(
            f"{format_timestamp(sentence['start'])}"
            f" --> "
            f"{format_timestamp(sentence['end'])}"
        )

        lines.append(
            sentence["text"]
        )

        lines.append("")

    return "\n".join(lines)


def map_scenes_to_timing(
    story,
    sentence_timings
):

    timing = []

    sentence_index = 0

    for scene in story["scenes"]:

        scene_text = clean_text(
            scene["narration"]
        )

        scene_sentences = split_into_sentences(
            scene_text
        )

        count = len(scene_sentences)

        selected = sentence_timings[
            sentence_index:
            sentence_index + count
        ]

        if not selected:

            continue

        start = selected[0]["start"]

        end = selected[-1]["end"]

        timing.append({
            "type": "scene",
            "scene_number": scene["scene_number"],
            "start": start,
            "end": end,
            "duration": end - start
        })

        sentence_index += count

    remaining = sentence_timings[
        sentence_index:
    ]

    if remaining:

        song_text = clean_text(
            story["song"]["lyrics"]
        )

        song_sentences = split_into_sentences(
            song_text
        )

        count = len(song_sentences)

        selected = remaining[:count]

        if selected:

            timing.append({
                "type": "song",
                "start": selected[0]["start"],
                "end": selected[-1]["end"],
                "duration": (
                    selected[-1]["end"]
                    - selected[0]["start"]
                )
            )

            sentence_index += count

    remaining = sentence_timings[
        sentence_index:
    ]

    if remaining:

        timing.append({
            "type": "ending",
            "start": remaining[0]["start"],
            "end": remaining[-1]["end"],
            "duration": (
                remaining[-1]["end"]
                - remaining[0]["start"]
            )
        })

    return timing


async def main():

    print("======================================")
    print("NOBINEST VOICE GENERATOR")
    print("======================================")

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    if os.path.exists(AUDIO_FILE):

        os.remove(
            AUDIO_FILE
        )

    story = load_story()

    parts = build_narration_parts(
        story
    )

    narration = combine_text(
        parts
    )

    if not narration:

        raise RuntimeError(
            "No narration text found."
        )

    print(
        f"Characters: {len(narration)}"
    )

    boundaries = await generate_audio(
        narration
    )

    sentence_timings = (
        build_sentence_timings(
            boundaries
        )
    )

    if not sentence_timings:

        raise RuntimeError(
            "No sentence timing data was returned."
        )

    srt = build_srt(
        sentence_timings
    )

    with open(
        SRT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            srt
        )

    scene_timing = map_scenes_to_timing(
        story,
        sentence_timings
    )

    with open(
        TIMING_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            scene_timing,
            file,
            indent=2
        )

    print()
    print("Voice generated successfully.")
    print(
        f"Audio: {AUDIO_FILE}"
    )
    print(
        f"Subtitles: {SRT_FILE}"
    )
    print(
        f"Timing: {TIMING_FILE}"
    )


if __name__ == "__main__":

    asyncio.run(
        main()
            )
