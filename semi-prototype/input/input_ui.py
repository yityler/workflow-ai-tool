# Gradio UI for the User Prompt module.
# Collects user inputs, and then formats them into a prompt to send to AI
# Currently uses Gradio for ease, we can switch to other UI later if needed

import gradio as gr
from .input_build_prompt import build_prompt
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

def _default_generate_fn(
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
        return f"error: {err}", "", "", "", None
    return prompt, "", "", "No pipeline function was wired in — showing the formatted prompt only.", None


def _default_reorder_fn(order_json, template):
    return "", "", "No pipeline function was wired in — reordering can't be applied.", template


REORDER_BRIDGE_HEAD = """
<script>
window.addEventListener('message', function (event) {
  var data = event.data;
  if (!data || data.source !== 'cornerstone-preview' || data.type !== 'reorder') return;
  var box = document.querySelector('#cornerstone_reorder_box textarea')
         || document.querySelector('#cornerstone_reorder_box input');
  if (!box) return;
  box.value = JSON.stringify(data.order);
  box.dispatchEvent(new Event('input', { bubbles: true }));
});
</script>
"""


def build_submit_fn(generate_fn):

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
        return generate_fn(
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
        )

    return submit_AI

def build_ui(generate_fn=None, reorder_fn=None):
    submit_AI = build_submit_fn(generate_fn or _default_generate_fn)
    reorder = reorder_fn or _default_reorder_fn

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
                prompt_preview = gr.Textbox(label="prompt", lines=20, interactive=False)
            with gr.Column():
                gr.Markdown("#### Generated Page Layout (Cornerstone JSON)")
                layout_out = gr.Code(label="layout", language="json", lines=20)

        gr.Markdown("#### Live Preview")
        preview_link_out = gr.HTML()

        gr.Markdown("#### Pipeline Report")
        report_out = gr.Markdown()

        template_state = gr.State()

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
            outputs=[prompt_preview, layout_out, preview_link_out, report_out, template_state],
        )

        gr.Markdown("### Reorder Sections\nDrag any section directly in the Live Preview above")
        reorder_box = gr.Textbox(elem_id="cornerstone_reorder_box", visible=False)

        reorder_box.input(
            fn=reorder,
            inputs=[reorder_box, template_state],
            outputs=[layout_out, preview_link_out, report_out, template_state],
        )

    return app