"""
Product Generation Module — FastAPI infrastructure
Combines concept.py (text + grounding) and image_gen.py (image) into a
single endpoint that the rest of the pipeline (Product Understanding, Layout)
can call.
"""

import os
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from concept import generate_concept
from image_gen import generate_image

app = FastAPI(title="Product Generation Module")

OUTPUT_DIR = "generated_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    product_name: str
    tagline: str
    category: str
    target_audience: str
    core_concept: str
    key_features: list[str]
    image_path: str
    token_usage: dict


@app.post("/generate", response_model=GenerateResponse)
def generate_product(request: GenerateRequest):
    try:
        concept = generate_concept(request.prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Concept generation failed: {e}")

    concept_tokens = concept.pop("_token_usage")
    image_prompt = concept.pop("image_prompt")

    output_filename = f"{OUTPUT_DIR}/{uuid.uuid4().hex}.png"

    try:
        image_result = generate_image(image_prompt, output_path=output_filename)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {e}")

    combined_tokens = {
        "concept": concept_tokens,
        "image": image_result["token_usage"],
        "total_tokens": concept_tokens["total_tokens"] + image_result["token_usage"]["total_tokens"],
    }

    return GenerateResponse(
        **concept,
        image_path=image_result["image_path"],
        token_usage=combined_tokens,
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
