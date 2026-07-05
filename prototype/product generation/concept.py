"""
Step 1: Product Concept Generation
Takes a raw user prompt, sends it to Gemini,
and returns a structured product concept.
"""

import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

CONCEPT_MODEL = "gemini-3.5-flash"

CONCEPT_SYSTEM_PROMPT = """You are a product concept generator for a B2B product page prototyping tool.
Given a short user prompt describing a product idea, invent a plausible, well-formed product concept
(no need to ground this in real current market data — creativity is fine here),
then return ONLY a JSON object with these exact fields and nothing else — no markdown fences,
no preamble:

{
  "product_name": string,
  "tagline": string,
  "category": string,
  "target_audience": string,
  "core_concept": string (2-3 sentences describing what the product is and does),
  "key_features": [string, string, string],
  "image_prompt": string (a detailed, visual description suitable for feeding directly
                           into an image generation model to create a product hero image)
}
"""


def generate_concept(user_prompt: str) -> dict:
    """
    Calls Gemini to produce a structured product concept.
    Returns a dict matching the schema in CONCEPT_SYSTEM_PROMPT.
    """
    response = client.models.generate_content(
        model=CONCEPT_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=CONCEPT_SYSTEM_PROMPT,
        ),
    )

    raw_text = response.text.strip()

    
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    concept = json.loads(raw_text)

    # Token usage tracking 
    usage = response.usage_metadata
    concept["_token_usage"] = {
        "prompt_tokens": usage.prompt_token_count,
        "response_tokens": usage.candidates_token_count,
        "total_tokens": usage.total_token_count,
    }

    return concept


if __name__ == "__main__":
    # test
    test_prompt = "A smart water bottle that tracks hydration for busy professionals"
    result = generate_concept(test_prompt)
    print(json.dumps(result, indent=2))
