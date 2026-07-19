# Cornerstone Layout JSON Specification

Defines the JSON object produced by `get_template()` /
`export_cornerstone_layout()` (`cornerstone_page_generator.py`) and consumed
by `render_html()` (`cornerstone_renderer.py`). 

## 1. Top-level object

| Field | Type | Required | Notes |
|---|---|---|---|
| `page_type` | `"product_information"` | yes | Only value currently supported |
| `theme` | `"modern"` \| `"minimal"` \| `"premium"` \| `"bold"` | yes | Maps to an accent color |
| `font` | `"modern"` \| `"classic"` \| `"friendly"` \| `"premium"` | yes | Not currently used |
| `tagline` | string | yes | Rendered in the page header |
| `primary_cta` | string | yes | Page-level default CTA label |
| `components` | array of Components | yes | Render order = array order |



## 2. Component object

Every entry in `components` uses the same envelope:

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | enum (§3) | yes | Determines which `content` shape applies (§6) |
| `id` | string | yes | Unique per page. Also used as the DOM id, drag-and-drop key, and diff-edit target |
| `heading` | string | yes | Rendered as `<h2>` |
| `body` | string | no (default `""`) | Optional paragraph under the heading |
| `style` | string | no (default `""`) | Free-text visual direction |
| `content` | object | no (default `{}`) | Type-specific payload |

## 3. Component types

`hero` | `product_visual` | `feature_grid` | `benefits` | `specifications` | `comparison` | `testimonial` | `faq` | `cta` | `footer`

## 4. Reserved `content` keys


| Key | Rendered as | Notes |
|---|---|---|
| `image` | `<img>` | Local file path or `http(s)` URL |
| `image_ref` | — | Model-output only. Resolved to `image` by `resolve_image_refs()` before the renderer runs; must match an id from the image inventory |
| `primary_cta` | Filled button | |
| `secondary_cta` | Outlined button | |
| `icon` | *unused* | No icon library is wired up so the value is shown as text|


## 5. Theme → accent color

| `theme` | Accent |
|---|---|
| `modern` | `#2563eb` |
| `minimal` | `#111827` |
| `premium` | `#7c3aed` |
| `bold` | `#dc2626` |

## 6. `content` shape by component type

### 6.1 List-item components (`feature_grid`, `benefits`, `comparison`, `testimonial`, `faq`)

`content` holds a list under a type-specific key (`features`, `benefits`,
`testimonials`, `faq`, `rows`). Each item is matched against this priority
order:

1. Heading — `title`, else `question`
2. Body text — first present of `body`, `description`, `answer`, `text`
3. Key/value row — `key` + `value` (only if step 2 found nothing)
4. `icon` — dropped
5. Any remaining fields — rendered generically (§6.4); treat as fallback, not designed shape

| Type | List field | Item shape |
|---|---|---|
| `feature_grid` | `content.features` | `{title, description, icon}` |
| `benefits` | `content.benefits` | `{title, body}` or `{title, description}` |
| `testimonial` | `content.testimonials` | `{text}` or `{title, body}` |
| `faq` | `content.faq` | `{question, answer}` |
| `comparison` | `content.rows` | `{key, value}` |

### 6.2 `hero`

```jsonc
"content": {
  "image": "path/or/url",     
  "primary_cta": "string",    
  "secondary_cta": "string"     
}
```

### 6.3 `product_visual`

```jsonc
"content": {
  "image": "path/or/url"      
}
```

### 6.4 `specifications`

```jsonc
"content": {
  "<spec name>": "<value>",
  "...": "..."
}
```

### 6.5 `cta`

```jsonc
"content": {
  "primary_cta": "string",      
  "secondary_cta": "string"    
```
