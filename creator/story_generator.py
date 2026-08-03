import os
import json
from google import genai

# ---------------------------------------------------------
# KIDS VIDEO STORY GENERATOR
# ---------------------------------------------------------

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set.")

client = genai.Client(api_key=API_KEY)

MODEL = "gemini-3.6-flash"

CHARACTERS = """
Bobo: a curious little bear who loves discovering new things.
Mimi: a clever little rabbit who likes asking questions.
Kiki: a cheerful little bird who loves singing.
"""

PROMPT = f"""
You are the head writer for an ORIGINAL children's YouTube channel.

The channel is designed for children approximately 3 to 7 years old.

Our recurring characters are:

{CHARACTERS}

Create ONE completely original children's episode.

IMPORTANT:
- Do not copy any existing children's song, cartoon, nursery rhyme,
  character, storyline, lyrics, dialogue, or copyrighted material.
- Do not imitate the exact style of any existing children's channel.
- Make the story simple, memorable and educational.
- Use short sentences.
- Use repetition that children can easily follow.
- Keep the language suitable for ages 3 to 7.
- Include a small problem and a satisfying solution.
- Include opportunities for visual scenes.
- Include a simple original song or chant.
- The final narration should be approximately 180 to 300 words.
- The finished episode should work as a 1 to 3 minute video.

Choose an educational theme such as:
counting, colours, shapes, sharing, kindness, brushing teeth,
cleaning up, animals, fruits, vegetables, road safety or friendship.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "title": "Episode title",
  "lesson": "What children learn",
  "characters": ["character names"],
  "scenes": [
    {{
      "scene_number": 1,
      "visual_description": "Detailed description of what should appear on screen",
      "narration": "Narration/dialogue for this scene",
      "duration_seconds": 10
    }}
  ],
  "song": {{
    "lyrics": "Original simple lyrics",
    "duration_seconds": 20
  }},
  "ending": "Short ending narration"
}}

Make the visual descriptions detailed enough that another AI system
could later use them to generate images or animation.
"""

def generate_story():
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT
    )

    text = response.text.strip()

    # Remove accidental markdown code fences
    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    story = json.loads(text)

    os.makedirs("output", exist_ok=True)

    with open("output/story.json", "w", encoding="utf-8") as file:
        json.dump(story, file, indent=2, ensure_ascii=False)

    with open("output/story.txt", "w", encoding="utf-8") as file:
        file.write(f"TITLE: {story['title']}\n\n")
        file.write(f"LESSON: {story['lesson']}\n\n")

        for scene in story["scenes"]:
            file.write(
                f"SCENE {scene['scene_number']}\n"
                f"VISUAL: {scene['visual_description']}\n"
                f"NARRATION: {scene['narration']}\n"
                f"DURATION: {scene['duration_seconds']} seconds\n\n"
            )

        file.write("SONG\n")
        file.write(story["song"]["lyrics"])
        file.write("\n\n")

        file.write("ENDING\n")
        file.write(story["ending"])

    print("Story generated successfully.")
    print(f"Title: {story['title']}")
    print(f"Lesson: {story['lesson']}")
    print("Saved to output/story.json")
    print("Saved to output/story.txt")


if __name__ == "__main__":
    generate_story()
