import json
import os
from google import genai

OUTPUT_DIR = "output"
STORY_JSON = os.path.join(OUTPUT_DIR, "story.json")
STORY_TXT = os.path.join(OUTPUT_DIR, "story.txt")

MODEL = "gemini-3.6-flash"

SYSTEM_PROMPT = """
You are the head writer for NobiNest, an original preschool
children's educational story universe.

Audience: children approximately 3 to 7 years old.

Create one short, safe, educational episode.

HARD LENGTH REQUIREMENT:
- The finished video must be 60 to 90 seconds.
- Ideal finished duration is about 75 seconds.
- Write approximately 110 to 140 total spoken words.
- This includes scene narration, song lyrics, and ending.
- Never intentionally write a long story.
- Do not add filler dialogue or unnecessary descriptions.
- Keep the story easy to narrate naturally.

STRUCTURE:
- Exactly 4 visual scenes.
- Each scene should normally contain 20 to 30 spoken words.
- Include a very short educational song of about 10 to 15 seconds.
- Include a closing message of about 3 to 5 seconds.
- The story must have a clear beginning, middle, lesson demonstration, and ending.

STYLE:
- Simple spoken English.
- Warm, funny, positive and age appropriate.
- Teach exactly one simple preschool concept.
- No violence, frightening situations, dangerous behavior, romance,
  politics, religion, or mature themes.
- Use only Bobo, Mimi and Kiki.
- Keep character appearances exactly consistent.
- Return ONLY valid JSON.
- No markdown.
- No emojis.

CANONICAL CHARACTERS:

Bobo:
small friendly brown bear with soft fluffy brown fur,
round face, small rounded ears, large expressive brown eyes,
short arms and legs, and a bright yellow scarf.
Personality: curious, playful, kind and slightly funny.

Mimi:
small friendly white rabbit with soft white fur,
long rounded ears with pink inner ears, large expressive eyes,
tiny pink nose, and a small purple backpack.
Personality: clever, curious, patient and encouraging.

Kiki:
small cheerful yellow bird with bright yellow feathers,
bright blue wings, large expressive eyes, and a small orange beak.
Personality: energetic, musical, cheerful and playful.
"""

def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not available.")
    return key

def create_story():
    client = genai.Client(api_key=get_api_key())

    prompt = SYSTEM_PROMPT + """
Create a preschool episode teaching one simple concept.

Return exactly this JSON structure:

{
  "title": "Episode title",
  "lesson": "One sentence describing the lesson",
  "characters": ["Bobo", "Mimi", "Kiki"],
  "character_bible": {
    "Bobo": {
      "appearance": "exact canonical appearance",
      "personality": "exact personality"
    },
    "Mimi": {
      "appearance": "exact canonical appearance",
      "personality": "exact personality"
    },
    "Kiki": {
      "appearance": "exact canonical appearance",
      "personality": "exact personality"
    }
  },
  "scenes": [
    {
      "scene_number": 1,
      "visual_description": "Action-focused visual description for animation",
      "narration": "20 to 30 spoken words"
    },
    {
      "scene_number": 2,
      "visual_description": "Action-focused visual description for animation",
      "narration": "20 to 30 spoken words"
    },
    {
      "scene_number": 3,
      "visual_description": "Action-focused visual description for animation",
      "narration": "20 to 30 spoken words"
    },
    {
      "scene_number": 4,
      "visual_description": "Action-focused visual description for animation",
      "narration": "20 to 30 spoken words"
    }
  ],
  "song": {
    "lyrics": "10 to 15 seconds of simple educational lyrics"
  },
  "ending": "3 to 5 second friendly educational closing"
}

Make every visual_description describe actions that can actually be animated:
walking, hopping, flying, turning, pointing, reaching, picking up,
moving an object, reacting, celebrating, or interacting.

Do not invent characters.
Do not change canonical designs.
Do not include duration_seconds.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()

    story = json.loads(text)
    validate_story(story)
    return story

def validate_story(story):
    required = [
        "title", "lesson", "characters",
        "character_bible", "scenes", "song", "ending"
    ]

    for key in required:
        if key not in story:
            raise ValueError(f"Story is missing required field: {key}")

    if len(story["scenes"]) != 4:
        raise ValueError("Story must contain exactly 4 scenes.")

    if story["characters"] != ["Bobo", "Mimi", "Kiki"]:
        raise ValueError("Story must use the canonical character list.")

    for character in ("Bobo", "Mimi", "Kiki"):
        if character not in story["character_bible"]:
            raise ValueError(f"Missing character bible entry: {character}")

    total_words = 0

    for scene in story["scenes"]:
        if scene.get("scene_number") not in (1, 2, 3, 4):
            raise ValueError("Invalid scene number.")
        if not scene.get("visual_description"):
            raise ValueError("Scene is missing visual_description.")
        if not scene.get("narration"):
            raise ValueError("Scene is missing narration.")
        total_words += len(scene["narration"].split())

    total_words += len(story["song"]["lyrics"].split())
    total_words += len(story["ending"].split())

    if total_words < 95 or total_words > 160:
        raise ValueError(
            f"Story has {total_words} spoken words; target is approximately 110-140."
        )

def save_story(story):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(STORY_JSON, "w", encoding="utf-8") as f:
        json.dump(story, f, indent=2, ensure_ascii=False)

    parts = [
        story["title"],
        "",
        f"Lesson: {story['lesson']}",
        ""
    ]

    for scene in story["scenes"]:
        parts.extend([
            f"Scene {scene['scene_number']}",
            scene["narration"],
            ""
        ])

    parts.extend([
        "Song",
        story["song"]["lyrics"],
        "",
        "Ending",
        story["ending"]
    ])

    with open(STORY_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

def main():
    print("======================================")
    print("NOBINEST STORY GENERATOR")
    print("TARGET: 60-90 SECOND EPISODES")
    print("======================================")

    story = create_story()
    save_story(story)

    print("Story generated successfully.")
    print(f"Title: {story['title']}")
    print(f"Lesson: {story['lesson']}")
    print("Scenes: 4")
    print("Target duration: 60-90 seconds")
    print("Saved to output/story.json")
    print("Saved to output/story.txt")

if __name__ == "__main__":
    main()
