import base64
import json
import os
import time

from google import genai


OUTPUT_DIR = "output"

SCENE_FILE = os.path.join(
    OUTPUT_DIR,
    "scenes.json"
)

IMAGE_DIR = os.path.join(
    OUTPUT_DIR,
    "images"
)

MODEL = "gemini-3.1-flash-image"


def get_api_key():

    key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not key:

        raise RuntimeError(
            "GEMINI_API_KEY is not available."
        )

    return key


def load_scenes():

    if not os.path.exists(
        SCENE_FILE
    ):

        raise FileNotFoundError(
            f"Missing {SCENE_FILE}"
        )

    with open(
        SCENE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_image(
    data,
    filename
):

    path = os.path.join(
        IMAGE_DIR,
        filename
    )

    with open(
        path,
        "wb"
    ) as file:

        file.write(data)

    return path


def generate_image(
    client,
    prompt
):

    response = client.interactions.create(
        model=MODEL,
        input=prompt,
        response_format={
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": "16:9",
            "image_size": "1K"
        }
    )

    if not response.output_image:

        raise RuntimeError(
            "Gemini did not return an image."
        )

    image_data = response.output_image.data

    if isinstance(
        image_data,
        str
    ):

        image_data = base64.b64decode(
            image_data
        )

    return image_data


def main():

    print(
        "======================================"
    )

    print(
        "NOBINEST IMAGE GENERATOR"
    )

    print(
        "======================================"
    )

    os.makedirs(
        IMAGE_DIR,
        exist_ok=True
    )

    scenes = load_scenes()

    client = genai.Client(
        api_key=get_api_key()
    )

    generated = 0

    for scene in scenes:

        number = scene[
            "scene_number"
        ]

        filename = (
            f"scene_{number:02d}.png"
        )

        output_path = os.path.join(
            IMAGE_DIR,
            filename
        )

        print()
        print(
            f"Generating scene {number}..."
        )

        if os.path.exists(
            output_path
        ):

            print(
                "Image already exists. Skipping."
            )

            generated += 1

            continue

        prompt = scene[
            "image_prompt"
        ]

        image_data = generate_image(
            client,
            prompt
        )

        path = save_image(
            image_data,
            filename
        )

        generated += 1

        print(
            f"Saved: {path}"
        )

        # Small delay between requests.
        time.sleep(2)

    print()
    print(
        "======================================"
    )

    print(
        "IMAGE GENERATION COMPLETE"
    )

    print(
        f"Images generated: {generated}"
    )

    print(
        f"Output directory: {IMAGE_DIR}"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    main()
