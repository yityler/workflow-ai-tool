"""
AI Product Information Page Layout Generator for Cornerstone UI.
Returns JSON Layout Specifications for Cornerstone Frontend
"""

import json
import os
import re
import hashlib
import time

import litellm
import gradio as gr

from typing import Literal
from pydantic import BaseModel

import token_optimizer as topt

litellm.suppress_debug_info = True
litellm.drop_params = True

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_DIR = os.path.join(
    HERE,
    "cornerstone_templates"
)

os.makedirs(TEMPLATE_DIR, exist_ok=True)

TRACKER = topt.SavingsTracker()


# ============================================================
# Product Input
# ============================================================

def load_product_input():
    with open(
            os.path.join(HERE, "product.json"),
            encoding="utf-8"
    ) as f:
        return json.load(f)


# ============================================================
# RAG Knowledge Retrieval
# Product design + UX principles
# ============================================================

LAST_RETRIEVAL = {}

_DESIGN_QUERIES = {

    "product_information":
        """
        product page hierarchy
        ecommerce UX
        visual storytelling
        product benefits
        conversion design
        feature explanation
        """

}


def _knowledge_chunks():
    with open(
            os.path.join(HERE, "design_knowledge.txt"),
            encoding="utf-8"
    ) as f:
        text = f.read()

    return [
        block.strip()
        for block in re.split(
            r"\n\s*\n",
            text
        )
        if block.strip()
    ]


def retrieve_design_knowledge(
        page_type,
        k=5
):
    """
    Retrieves only relevant UX/design knowledge.
    """

    from rank_bm25 import BM25Okapi

    chunks = _knowledge_chunks()

    tokenize = lambda x: re.findall(
        r"[a-z0-9']+",
        x.lower()
    )

    bm25 = BM25Okapi(
        [
            tokenize(chunk)
            for chunk in chunks
        ]
    )

    query = _DESIGN_QUERIES.get(
        page_type,
        _DESIGN_QUERIES["product_information"]
    )

    scores = bm25.get_scores(
        tokenize(query)
    )

    ranked = sorted(
        range(len(chunks)),
        key=lambda i: scores[i],
        reverse=True
    )

    selected = [
        chunks[i]
        for i in ranked[:k]
    ]

    LAST_RETRIEVAL[page_type] = {

        "used": len(selected),

        "total": len(chunks),

        "tokens":
            topt.count_tokens(
                "\n".join(selected)
            )

    }

    return selected


# ============================================================
# Cornerstone Component Schema
# ============================================================

ComponentType = Literal[

    "hero",

    "product_visual",

    "feature_grid",

    "benefits",

    "specifications",

    "comparison",

    "testimonial",

    "faq",

    "cta",

    "footer"

]


class Component(BaseModel):
    type: ComponentType

    id: str

    heading: str

    body: str = ""

    style: str = ""

    content: dict = {}


class ProductPageTemplate(BaseModel):
    """
    JSON contract passed into Cornerstone UI.
    """

    page_type: Literal[
        "product_information"
    ]

    theme: Literal[
        "modern",
        "minimal",
        "premium",
        "bold"
    ]

    font: Literal[
        "modern",
        "classic",
        "friendly",
        "premium"
    ]

    tagline: str

    primary_cta: str

    components: list[Component]

    def model_post_init(self, _):

        component_types = [
            c.type
            for c in self.components
        ]

        required = {

            "hero",

            "product_visual",

            "cta"

        }

        missing = (
                required
                -
                set(component_types)
        )

        if missing:
            raise ValueError(
                f"Missing required components: {missing}"
            )

        if len(self.components) > 8:
            raise ValueError(
                "Too many components. "
                "Keep pages scannable."
            )


# ============================================================
# Model Routing
# ============================================================


MODELS = {

    "design": {

        "model":
            "mistral/mistral-small-latest",

        "env":
            "MISTRAL_API_KEY"

    },

    "edit": {

        "model":
            "mistral/ministral-8b-latest",

        "env":
            "MISTRAL_API_KEY"

    }

}


def call_structured(
        route,
        key,
        prompt,
        response_model
):
    import instructor

    client = instructor.from_litellm(
        litellm.completion
    )

    obj, response = (
        client.chat.completions
        .create_with_completion(
            response_model=response_model,

            messages=[
                {
                    "role":
                        "user",

                    "content":
                        prompt
                }
            ],

            model=
            MODELS[route]["model"],

            api_key=key,

            max_retries=2
        )
    )

    return obj


# ============================================================
# Template Cache
# ============================================================

def template_path(
        product_name,
        brand,
        page_type,
        layout_instructions=""
):
    key = (
        f"{product_name}|"
        f"{brand}|"
        f"{page_type}|"
        f"{layout_instructions.strip().lower()}"
    )

    hashed = hashlib.md5(
        key.encode()
    ).hexdigest()[:10]

    return os.path.join(
        TEMPLATE_DIR,
        f"{hashed}.json"
    )


# ============================================================
# Generate Cornerstone Layout Template
# ============================================================

def get_template(
        product,
        brand,
        brand_color,
        key,
        layout_instructions=""
):
    """
    Generates ONE reusable layout specification.

    This JSON is passed to Cornerstone UI.
    """

    path = template_path(
        product["name"],
        brand,
        "product_information",
        layout_instructions
    )

    # ----------------------------
    # Cache hit
    # ----------------------------

    if os.path.exists(path):
        with open(
                path,
                encoding="utf-8"
        ) as f:
            return (
                ProductPageTemplate(
                    **json.load(f)
                ),
                True
            )

    # ----------------------------
    # Retrieve UX knowledge
    # ----------------------------

    knowledge = "\n\n".join(
        retrieve_design_knowledge(
            "product_information"
        )
    )

    # ----------------------------
    # Cornerstone Prompt
    # ----------------------------

    prompt = f"""

You are an expert product page designer.

You are creating a frontend layout specification
for Cornerstone UI.

Cornerstone does NOT need HTML/CSS.

Return only a structured JSON layout.

The JSON will be rendered into React components.

========================

BRAND INFORMATION

Brand:
{brand}

Brand Color:
{brand_color}


========================

PRODUCT INFORMATION

Name:
{product.get("name")}

Description:
{product.get("description")}

Category:
{product.get("category")}

Features:
{product.get("features")}


========================

DESIGN KNOWLEDGE

{knowledge}


========================

USER LAYOUT PREFERENCES

{layout_instructions.strip() if layout_instructions and layout_instructions.strip() else "No specific preferences provided. Use best-practice UX ordering."}

IMPORTANT: The order of items in the `components` array
is the order they render top-to-bottom on the page.

If the user has requested specific placement
(e.g. "image on bottom", "put testimonials before the CTA",
"features before the hero"), reorder the `components`
array to match that request exactly, even if it
deviates from typical UX conventions. Only the
component TYPES marked as required must still be present
somewhere in the array — their position is flexible
unless the user says otherwise.


========================

CREATE A PRODUCT INFORMATION PAGE

The layout should contain:

- Hero section
- Product visual section
- Feature explanation
- Benefits
- Call-to-action

Prioritize:

- clear hierarchy
- conversion
- readability
- responsive design
- premium visual experience


Each component should contain:

type:
(the Cornerstone component)

id:
(unique identifier)

heading:
(customer-facing text)

body:
(optional supporting text)

style:
(visual direction)

content:
(component data)


Do NOT generate:

- HTML
- CSS
- Javascript

Only generate the layout JSON.
"""

    template = call_structured(
        "design",
        key,
        prompt,
        ProductPageTemplate
    )

    # ----------------------------
    # Save template
    # ----------------------------

    with open(
            path,
            "w",
            encoding="utf-8"
    ) as f:
        json.dump(
            template.model_dump(),
            f,
            indent=2
        )

    return template, False


# ============================================================
# Diff-Based Component Editing
# ============================================================

def edit_component(
        template,
        component_id,
        instruction,
        key
):
    """
    Only sends ONE component to the LLM.

    Instead of:

        entire page JSON

    sends:

        one component JSON

    """

    target = next(
        (
            c for c in template.components
            if c.id == component_id
        ),
        None
    )

    if target is None:
        raise ValueError(
            "Component not found"
        )

    prompt = f"""

Modify this Cornerstone UI component.

Instruction:

{instruction}


Current component:

{target.model_dump_json()}


Return only the updated component JSON.
"""

    updated = call_structured(
        "edit",
        key,
        prompt,
        Component
    )

    template.components = [

        updated
        if c.id == component_id
        else c

        for c in template.components

    ]

    return template


# ============================================================
# Cornerstone JSON Export
# ============================================================

def export_cornerstone_layout(
        template
):
    """
    This is the object sent to Cornerstone UI.
    """

    return template.model_dump_json(
        indent=2
    )


# ============================================================
# Full Generation Workflow
# ============================================================

def generate_cornerstone_page(
        brand,
        brand_color,
        api_key,
        product_description,
        product_name,
        category,
        features,
        layout_instructions=""
):
    key = (
        api_key.strip()
        if api_key
        else os.environ.get(
            "MISTRAL_API_KEY",
            ""
        )
    )

    if not key:
        return (
            "",
            "Missing API key"
        )

    product = {

        "name":
            product_name,

        "description":
            product_description,

        "category":
            category,

        "features":
            features.split(",")
            if features
            else []

    }

    start = time.time()

    template, cached = get_template(
        product,
        brand,
        brand_color,
        key,
        layout_instructions
    )

    elapsed = time.time() - start

    layout_json = (
        export_cornerstone_layout(
            template
        )
    )

    report = f"""

## Cornerstone UI Layout Generated


**Brand**
{brand}


**Product**
{product_name}


**Template**
{"Cache hit (0 tokens)" if cached else "New AI generation"}


**Layout preferences**
{layout_instructions.strip() if layout_instructions and layout_instructions.strip() else "None (default UX ordering)"}


**Generation time**
{elapsed:.2f}s


The output JSON can now be passed directly into
Cornerstone UI.


"""

    return (
        layout_json,
        report
    )


# ============================================================
# Example Hugging Face Image Integration
# ============================================================

def attach_product_image(
        layout,
        image_url
):
    """
    Adds generated product imagery
    into the Cornerstone JSON.
    """

    data = json.loads(layout)

    for component in data["components"]:

        if component["type"] == "product_visual":
            component["content"] = {

                "image":
                    image_url

            }

    return json.dumps(
        data,
        indent=2
    )


# ============================================================
# Gradio UI
# ============================================================


def build_ui():
    with gr.Blocks(
            title="Cornerstone AI Product Generator"
    ) as demo:
        gr.Markdown(
            """
            # Cornerstone AI Product Information Page Generator

            Input a product and brand.

            AI generates a structured frontend layout
            specification for Cornerstone UI.
            """
        )

        with gr.Row():
            brand = gr.Textbox(
                label="Brand Name",
                value="Demo Brand"
            )

            color = gr.Textbox(
                label="Brand Color",
                value="#2563EB"
            )

        api_key = gr.Textbox(
            label="Mistral API Key",
            type="password"
        )

        product_name = gr.Textbox(
            label="Product Name"
        )

        description = gr.Textbox(
            label="Product Description",
            lines=3
        )

        category = gr.Textbox(
            label="Category"
        )

        features = gr.Textbox(
            label="Features (comma separated)"
        )

        layout_instructions = gr.Textbox(
            label="Layout Preferences (optional)",
            placeholder=(
                "e.g. put the product image on the "
                "bottom, show testimonials before the CTA"
            ),
            lines=2
        )

        generate_btn = gr.Button(
            "Generate Cornerstone Layout"
        )

        output_json = gr.Code(
            language="json",
            label="Cornerstone UI JSON"
        )

        report = gr.Markdown()

        generate_btn.click(

            generate_cornerstone_page,

            inputs=[

                brand,

                color,

                api_key,

                description,

                product_name,

                category,

                features,

                layout_instructions

            ],

            outputs=[

                output_json,

                report

            ]

        )

    return demo


# ============================================================
# Run
# ============================================================


if __name__ == "__main__":
    build_ui().launch(
        server_port=7861
    )
