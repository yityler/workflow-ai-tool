"""
Step 2: Product Image Generation
Takes the image_prompt produced by concept.py and generates a product image
using gemini-3.1-flash-image (Nano Banana 2) with Google Search grounding —
this is the cheapest image model that supports grounding (RAG).
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

IMAGE_MODEL = "gemini-3.1-flash-image"


def generate_image(image_prompt: str, output_path: str = "product_image.png") -> dict:
    """
    Calls Gemini 3.1 Flash Image (with Google Search grounding) to generate
    a product image from a text prompt. Saves the image to output_path and
    returns metadata about the result.
    """
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=image_prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    image_saved = False
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            image_saved = True
            break

    if not image_saved:
        raise RuntimeError("No image data returned — check the prompt or model response for a text-only reply.")

    usage = response.usage_metadata
    return {
        "image_path": output_path,
        "token_usage": {
            "prompt_tokens": usage.prompt_token_count,
            "response_tokens": usage.candidates_token_count,
            "total_tokens": usage.total_token_count,
        },
    }


if __name__ == "__main__":
    test_prompt = (
        "A sleek smart water bottle with a small LED hydration display, "
        "matte navy finish, studio product photography, white background, soft shadows"
    )
    result = generate_image(test_prompt)
    print(result)
