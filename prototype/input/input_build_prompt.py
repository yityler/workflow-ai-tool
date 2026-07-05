from input_rag import retrieve_context


def build_prompt(
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

    
    
    # I know we're using Corner Stone UI 
    # But I don't really know how that works - probably should ask Judah about this
    
    # Might have to add more to prompt to make it completely adhere workflow
    prompt = '''
            You are an AI that generates a product web page based on the following information.
            The product page should be structured with a clear hierarchy, engaging visuals, and persuasive copy that aligns with the provided style preferences.
            Please ensure that the generated content is original, relevant to the product, and adheres to the specified tone and style guidelines.                        
            Generate a HTML / CSS / Javascript product page that is responsive and visually appealing, with a focus on user experience and conversion optimization.
            
            -----------------------

            
            '''
    prompt = prompt + "\n\n".join(sections)
    return prompt, None  