# Gradio UI for the User Prompt module.
# Collects user inputs, and then formats them into a prompt to send to AI
# Currently uses Gradio for ease, we can switch to other UI later if needed

import gradio as gr
from input_build_prompt import build_prompt

# Options - we can add more if needed

INDUSTRIES = [
    "Fashion & Apparel",
    "Consumer Electronics",
    "Home & Garden",
    "Health & Beauty",
    "Sports & Outdoors",
    "Food & Beverage",
    "Industrial / B2B",
    "Automotive",
    "Toys & Games",
    "Other",
]

TARGET_AUDIENCES = [
    "General Consumer",
    "Young Adults (18–30)",
    "Professionals / Enterprise",
    "Parents & Families",
    "Enthusiasts / Hobbyists",
    "Seniors",
    "Other",
]

PAGE_THEMES = [
    "Apple-style (clean, minimal, premium)",
    "Amazon-style (dense, feature-rich)",
    "Minimalist",
    "Modern",
    "Technical / Spec-heavy",
    "Luxury",
]

LAYOUT_STYLES = [
    "Single column",
    "Two column",
    "Magazine / editorial",
    "Hero image lead",
]

SPACING_OPTIONS = [
    "Tight",
    "Balanced",
    "Airy / lots of whitespace",
]

TONES = [
    "Professional",
    "Conversational",
    "Enthusiastic",
    "Technical / precise",
    "Luxury / aspirational",
    "Friendly",
]

COLOR_SCHEMES = [
    "Light / white",
    "Dark / black",
    "Brand colors (unspecified)",
    "Warm tones",
    "Cool tones",
    "High contrast",
]


# wraps inputs into AI prompt, then sends

def submit_AI(
    product_description,
    industry,
    target_audience,
    page_theme,
    layout_style,
    spacing,
    tone,
    color_scheme,
    extra_notes,
    product_files,
    theme_files,
):
    prompt, err = build_prompt(
        product_description=product_description,
        industry=industry,
        target_audience=target_audience,
        page_theme=page_theme,
        layout_style=layout_style,
        spacing=spacing,
        tone=tone,
        color_scheme=color_scheme,
        extra_notes=extra_notes,
        product_files=product_files,
        theme_files=theme_files,
    )

    if err:
        return f"error: {err}", ""

    # send prompt to AI and return response here
    # not to sure about the format of the response
    # should we output as files or as full text
    # what if we hosted the web UI on local so the user can view it
    response = ""

    return prompt, response


# ---- UI ----

# FOR FUTURE:
# Replace response textbox with a better version of the output
# Maybe a live preview of the web page, a downloadable bunch of files, and maybe the AI's thought process

# I just saw Rohan's product generation thingy - maybe try to integrate that into this UI so user can use both
# Or maybe just have the AI straight up generate graaphics into the web UI 

def build_ui():
    with gr.Blocks(title="Product Prompt Builder") as app:
        gr.Markdown("## Product Prompt Builder\nFill in what you know about the product and how you want the page to feel. Hit Generate when you're ready.")

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Product")
                product_description = gr.Textbox(
                    label="Product Description",
                    lines=5,
                    placeholder="Describe the product — what it is, what it does, anything notable about it...",
                )
                industry = gr.Dropdown(
                    label="Industry",
                    choices=INDUSTRIES,
                    value="Consumer Electronics",
                )
                target_audience = gr.Dropdown(
                    label="Target Audience",
                    choices=TARGET_AUDIENCES,
                    value="General Consumer",
                )
                extra_notes = gr.Textbox(
                    label="Extra Notes (optional)",
                    lines=3,
                    placeholder="Anything else the AI should know — competitors, key differentiators, things to avoid...",
                )

            with gr.Column(scale=1):
                gr.Markdown("### Page Style")
                page_theme = gr.Dropdown(
                    label="Theme",
                    choices=PAGE_THEMES,
                    value="Modern",
                )
                layout_style = gr.Dropdown(
                    label="Layout Style",
                    choices=LAYOUT_STYLES,
                    value="Two column",
                )
                spacing = gr.Dropdown(
                    label="Spacing",
                    choices=SPACING_OPTIONS,
                    value="Balanced",
                )
                tone = gr.Dropdown(
                    label="Copy Tone",
                    choices=TONES,
                    value="Professional",
                )
                color_scheme = gr.Dropdown(
                    label="Color Scheme",
                    choices=COLOR_SCHEMES,
                    value="Light / white",
                )
        gr.Markdown("### Reference Documents (optional)")
        gr.Markdown("Upload files to give the AI extra context via RAG. Product info docs go on the left, brand/theme guidelines on the right.")
        with gr.Row():
            with gr.Column():
                product_files = gr.File(
                    label="Product Info",
                    file_count="multiple",
                    file_types=[".txt", ".pdf", ".md", ".png", ".jpg", ".jpeg"],
                )
            with gr.Column():
                theme_files = gr.File(
                    label="Company Theme / Brand Guidelines",
                    file_count="multiple",
                    file_types=[".txt", ".pdf", ".md", ".png", ".jpg", ".jpeg"],
                )

        submit_btn = gr.Button("Generate", variant="primary")

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Formatted Prompt (what gets sent to the AI)")
                prompt_preview = gr.Textbox(label="prompt", lines=25, interactive=False)
            with gr.Column():
                gr.Markdown("#### Response")
                response_out = gr.Textbox(label="response", lines=25, interactive=False)

        submit_btn.click(
            fn=submit_AI,
            inputs=[
                product_description,
                industry,
                target_audience,
                page_theme,
                layout_style,
                spacing,
                tone,
                color_scheme,
                extra_notes,
                product_files,
                theme_files,
            ],
            outputs=[prompt_preview, response_out],
        )

    return app