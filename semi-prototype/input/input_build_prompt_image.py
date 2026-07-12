from .input_rag import retrieve_context


def build_prompt_image(
    product_description,
    industry,
    target_audience,
    page_theme,
    layout_style,
    spacing,
    tone,
    color_scheme,
    extra_notes,
    product_files=None,
    theme_files=None,
):
    if not product_description or not product_description.strip():
        return None, "product description is required"

    sections = []

    sections.append(f"Product Description:\n{product_description.strip()}")

    if industry:
        sections.append(f"Industry: {industry}")

    if target_audience:
        sections.append(f"Target Audience: {target_audience}")

    if product_files:
        product_context = retrieve_context(
            query=product_description,
            files=product_files,
        )
        if product_context:
            sections.append(f"Additional Product Information (from uploaded docs):\n{product_context}")

    if theme_files:
        style_query = f"{page_theme} {tone} {color_scheme}"
        theme_context = retrieve_context(
            query=style_query,
            files=theme_files,
        )
        if theme_context:
            sections.append(f"Brand & Theme Guidelines (from uploaded docs):\n{theme_context}")

    style_lines = []
    if page_theme:
        style_lines.append(f"Theme: {page_theme}")
    if layout_style:
        style_lines.append(f"Layout Style: {layout_style}")
    if spacing:
        style_lines.append(f"Spacing: {spacing}")
    if color_scheme:
        style_lines.append(f"Color Scheme: {color_scheme}")
    if style_lines:
        sections.append("Visual Preferences:\n" + "\n".join(style_lines))

    if tone:
        sections.append(f"Copy Tone: {tone}")

    if extra_notes and extra_notes.strip():
        sections.append(f"Additional Notes:\n{extra_notes.strip()}")


    prompt = '''
            You are part of an AI Workflow that creates a product page to the website.
            You are a module that generates product images for the website.

            Output only a single image for the website.

            You are given the following information for the product and website website:            
            '''
    prompt = prompt + "\n\n".join(sections)

    prompt = prompt + '''
                    Generate a product image based on the above information. The image should be visually appealing, relevant to the product, and suitable for a website product page.
                    '''
    return prompt, None  