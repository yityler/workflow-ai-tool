

import html
import os
import shutil

THEME_ACCENT = {
    "modern": "#2563eb",
    "minimal": "#111827",
    "premium": "#7c3aed",
    "bold": "#dc2626",
}


def _esc(value):
    return html.escape(str(value)) if value is not None else ""


def _render_content(content):
    if not content:
        return ""

    parts = []

    for k, v in content.items():

        if isinstance(v, list):

            rendered_items = ""

            for item in v:

                if isinstance(item, dict):

                    rendered_items += "<li>"

                    if "title" in item:
                        rendered_items += (
                            f"<strong>{_esc(item['title'])}</strong>"
                        )

                    if "body" in item:
                        rendered_items += (
                            f"<p>{_esc(item['body'])}</p>"
                        )
                    elif "text" in item:
                        rendered_items += (
                            _esc(item["text"])
                        )

                    elif "key" in item and "value" in item:
                        rendered_items += (
                            f"<strong>{_esc(item['key'])}</strong>: "
                            f"{_esc(item['value'])}"
                        )

                    elif "question" in item:
                        rendered_items += (
                            f"<strong>{_esc(item['question'])}</strong>"
                            f"<p>{_esc(item.get('answer',''))}</p>"
                        )

                    else:
                        rendered_items += _render_content(item)

                    rendered_items += "</li>"

                else:
                    rendered_items += (
                        f"<li>{_esc(item)}</li>"
                    )

            parts.append(
                f"""
                <div class='content-block'>
                    <strong>{_esc(k)}</strong>
                    <ul>{rendered_items}</ul>
                </div>
                """
            )

        elif isinstance(v, dict):

            parts.append(
                f"""
                <div class='content-block'>
                    <strong>{_esc(k)}</strong>
                    {_render_content(v)}
                </div>
                """
            )


        else:

            parts.append(
                f"""
                <div class='content-block'>
                    <strong>{_esc(k)}:</strong>
                    {_esc(v)}
                </div>
                """
            )

    return "".join(parts)


def _render_component(component):
    image_html = ""
    if component.type == "product_visual":
        img = (component.content or {}).get("image")
        if img:
            src = img if str(img).startswith("http") else html.escape(os.path.basename(str(img)))
            image_html = f"<div class='visual'><img src='{src}' alt='{_esc(component.heading)}'/></div>"

    return f"""
    <section class="component {_esc(component.type)}" id="{_esc(component.id)}">
        <h2>{_esc(component.heading)}</h2>
        {f"<p class='body'>{_esc(component.body)}</p>" if component.body else ""}
        {image_html}
        {_render_content(component.content)}
    </section>
    """


def render_html(template):
    """template: a cornerstone_layout_generator.ProductPageTemplate instance."""
    accent = THEME_ACCENT.get(template.theme, "#2563eb")
    body = "".join(_render_component(c) for c in template.components)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="Cache-Control" content="no-store">
<title>{_esc(template.tagline) or "Product Page"}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; margin:0; background:#f5f5f7; color:#111; }}
  header.tagline {{ background:{accent}; color:white; padding:40px 24px; text-align:center; font-size:1.5rem; font-weight:600; }}
  section.component {{ max-width:880px; margin:24px auto; padding:28px 32px; background:white; border-radius:14px;
                        box-shadow:0 1px 6px rgba(0,0,0,0.08); }}
  section.hero {{ text-align:center; }}
  section.cta {{ text-align:center; background:{accent}14; }}
  section.cta button {{ background:{accent}; color:white; border:none; padding:14px 28px; border-radius:8px;
                          font-size:1rem; cursor:pointer; margin-top:12px; }}
  h2 {{ margin-top:0; }}
  p.body {{ color:#444; line-height:1.5; }}
  .visual img {{ max-width:100%; border-radius:10px; display:block; margin:0 auto; }}
  .content-block {{ margin:10px 0; color:#333; }}
  .content-block ul {{ margin:6px 0 0 20px; padding:0; }}
  footer.page-footer {{ text-align:center; padding:28px; color:#888; font-size:0.85rem; }}
</style>
</head>
<body>
<header class="tagline">{_esc(template.tagline)}</header>
{body}
<footer class="page-footer">Live local preview &middot; theme: {_esc(template.theme)} &middot; font: {_esc(template.font)}</footer>
</body>
</html>"""


def write_preview(template, out_dir, filename="cornerstone_preview.html"):
    """Renders the template to HTML and writes it (plus any locally-referenced
    product images) into out_dir so a simple static file server can serve it."""
    os.makedirs(out_dir, exist_ok=True)

    for component in template.components:
        if component.type == "product_visual":
            img = (component.content or {}).get("image")
            if img and not str(img).startswith("http") and os.path.exists(img):
                dest = os.path.join(out_dir, os.path.basename(img))
                try:
                    if os.path.abspath(img) != os.path.abspath(dest):
                        shutil.copyfile(img, dest)
                except Exception:
                    pass

    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_html(template))
    return path
