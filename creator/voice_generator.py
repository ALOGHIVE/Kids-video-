import asyncio
import json
import os
import edge_tts


# =========================================================
# KIDS VOICE GENERATOR
# =========================================================

VOICE = "en-US-AriaNeural"

RATE = "-5%"
PITCH = "+2Hz"
VOLUME = "+0%"


def load_story():
    with open(
        "output/story.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def build_narration(story):
    parts = []

    for scene in story["scenes"]:
        narration = scene.get("narration", "").strip()

        if narration:
            parts.append(narration)

    song = story.get("song", {}).get("lyrics", "").strip()

    if song:
        parts.append(song)

    ending = story.get("ending", "").strip()

    if ending:
        parts.append(ending)

    return "\n\n".join(parts)


async def generate_voice(text):

    os.makedirs("output", exist_ok=True)

    audio_path = "output/narration.mp3"
    subtitle_path = "output/narration.srt"

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME
    )

    await communicate.save(
        audio_path,
        subtitle_path
    )

    return audio_path, subtitle_path


async def main():

    print("======================================")
    print("KIDS VOICE GENERATOR")
    print("======================================")

    story = load_story()

    print(f"Story: {story['title']}")

    narration = build_narration(story)

    if not narration:
        raise RuntimeError(
            "No narration was found in story.json."
        )

    print(
        f"Narration characters: {len(narration)}"
    )

    audio_path, subtitle_path = await generate_voice(
        narration
    )

    print()
    print("Voice generated successfully.")
    print(f"Audio: {audio_path}")
    print(f"Subtitles: {subtitle_path}")


if __name__ == "__main__":
    asyncio.run(main())
