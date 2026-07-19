

import hashlib
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


def _render_list_item(item):
    if not isinstance(item, dict):
        return f"<li>{_esc(item)}</li>"

    used_keys = set()
    inner = ""

    if "title" in item:
        inner += f"<strong>{_esc(item['title'])}</strong>"
        used_keys.add("title")
    elif "question" in item:
        inner += f"<strong>{_esc(item['question'])}</strong>"
        used_keys.add("question")

    for key in ("body", "description", "answer", "text"):
        if key in item:
            inner += f"<p>{_esc(item[key])}</p>"
            used_keys.add(key)
            break

    if not inner and "key" in item and "value" in item:
        inner += f"<strong>{_esc(item['key'])}</strong>: {_esc(item['value'])}"
        used_keys.update({"key", "value"})

    used_keys.add("icon")

    leftover = {k: v for k, v in item.items() if k not in used_keys}
    if leftover:
        inner += _render_content(leftover)

    if not inner:
        inner = _render_content(item)

    return f"<li>{inner}</li>"


def _render_content(content):
    if not content:
        return ""

    parts = []

    for k, v in content.items():

        if k == "icon":
            continue

        if isinstance(v, list):

            rendered_items = "".join(_render_list_item(item) for item in v)

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
    content = dict(component.content or {})
    img = content.pop("image", None)
    if img:
        src = img if str(img).startswith("http") else html.escape(os.path.basename(str(img)))
        image_html = f"<div class='visual'><img src='{src}' alt='{_esc(component.heading)}'/></div>"

    primary_cta = content.pop("primary_cta", None)
    secondary_cta = content.pop("secondary_cta", None)
    cta_html = ""
    if primary_cta or secondary_cta:
        cta_html = "<div class='cta-buttons'>"
        if primary_cta:
            cta_html += f"<button class='cta-primary'>{_esc(primary_cta)}</button>"
        if secondary_cta:
            cta_html += f"<button class='cta-secondary'>{_esc(secondary_cta)}</button>"
        cta_html += "</div>"

    return f"""
    <section class="component {_esc(component.type)}" id="{_esc(component.id)}" data-cid="{_esc(component.id)}" draggable="true">
        <span class="drag-handle" title="Drag to reorder this section">&#10021;</span>
        <h2>{_esc(component.heading)}</h2>
        {f"<p class='body'>{_esc(component.body)}</p>" if component.body else ""}
        {image_html}
        {_render_content(content)}
        {cta_html}
    </section>
    """


_DRAG_DROP_SCRIPT = """
<script>
(function () {
  var dragEl = null;

  function sections() {
    return Array.prototype.slice.call(document.querySelectorAll('section.component'));
  }

  function sendOrder() {
    var order = sections().map(function (s) { return s.dataset.cid; });
    try {
      window.parent.postMessage(
        { source: 'cornerstone-preview', type: 'reorder', pageId: document.body.dataset.pageId, order: order },
        '*'
      );
    } catch (e) { /* no host listening — fine, this is just a static preview */ }
  }

  sections().forEach(function (sec) {
    sec.addEventListener('dragstart', function (e) {
      dragEl = sec;
      sec.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', sec.dataset.cid);
    });

    sec.addEventListener('dragend', function () {
      sec.classList.remove('dragging');
      sections().forEach(function (s) { s.classList.remove('drag-over'); });
      sendOrder();
    });

    sec.addEventListener('dragover', function (e) {
      e.preventDefault();
      if (!dragEl || sec === dragEl) return;
      var rect = sec.getBoundingClientRect();
      var before = e.clientY < rect.top + rect.height / 2;
      sec.parentNode.insertBefore(dragEl, before ? sec : sec.nextSibling);
    });
  });
})();
</script>
"""


def render_html(template, page_id=""):
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
  section.component {{ position:relative; max-width:880px; margin:24px auto; padding:28px 32px 28px 56px; background:white;
                        border-radius:14px; box-shadow:0 1px 6px rgba(0,0,0,0.08); cursor:grab;
                        transition:opacity .15s ease, box-shadow .15s ease; }}
  section.component:active {{ cursor:grabbing; }}
  section.component.dragging {{ opacity:0.35; }}
  section.component .drag-handle {{ position:absolute; left:18px; top:28px; color:{accent}; opacity:0.45;
                                     font-size:1.1rem; line-height:1; user-select:none; }}
  section.component:hover .drag-handle {{ opacity:0.9; }}
  section.hero {{ text-align:center; }}
  section.cta {{ text-align:center; background:{accent}14; }}
  .cta-buttons {{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:16px; }}
  .cta-primary {{ background:{accent}; color:white; border:none; padding:14px 28px; border-radius:8px;
                   font-size:1rem; font-weight:600; cursor:pointer; }}
  .cta-secondary {{ background:transparent; color:{accent}; border:2px solid {accent}; padding:12px 26px;
                     border-radius:8px; font-size:1rem; font-weight:600; cursor:pointer; }}
  h2 {{ margin-top:0; }}
  p.body {{ color:#444; line-height:1.5; }}
  .visual img {{ max-width:100%; border-radius:10px; display:block; margin:0 auto; }}
  .content-block {{ margin:10px 0; color:#333; }}
  .content-block ul {{ margin:6px 0 0 20px; padding:0; }}
  footer.page-footer {{ text-align:center; padding:28px; color:#888; font-size:0.85rem; }}
</style>
</head>
<body data-page-id="{_esc(page_id)}">
<header class="tagline">{_esc(template.tagline)}</header>
{body}
<footer class="page-footer">Live local preview &middot; theme: {_esc(template.theme)} &middot; font: {_esc(template.font)} &middot; drag any section to reorder it</footer>
{_DRAG_DROP_SCRIPT}
</body>
</html>"""


def write_preview(template, out_dir, filename=None, page_id=""):
    """Renders the template to HTML and writes it (plus any locally-referenced
    product images) into out_dir so a simple static file server can serve it.

    `filename` should normally be a stable, caller-supplied name tied to a
    specific page (e.g. derived from a per-page id), so repeated edits to the
    SAME page keep updating the SAME hosted file/URL. If omitted, a filename
    is derived from the template's content so different pages still don't
    collide with each other.

    `page_id` is embedded in the page so the drag-and-drop script can tag
    postMessage events with the page they came from."""
    os.makedirs(out_dir, exist_ok=True)

    for component in template.components:
        img = (component.content or {}).get("image")
        if img and not str(img).startswith("http") and os.path.exists(img):
            dest = os.path.join(out_dir, os.path.basename(img))
            try:
                if os.path.abspath(img) != os.path.abspath(dest):
                    shutil.copyfile(img, dest)
            except Exception:
                pass

    if filename is None:
        digest = hashlib.md5(template.model_dump_json().encode("utf-8")).hexdigest()[:12]
        filename = f"cornerstone_preview_{digest}.html"

    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_html(template, page_id=page_id))
    return path
