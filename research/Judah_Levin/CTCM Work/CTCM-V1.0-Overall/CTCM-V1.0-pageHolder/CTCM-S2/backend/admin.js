let fields = [];
let fieldMap = new Map();
let selectedImageFieldId = null;
const IMAGE_OUTPUT_TYPE = "image/webp";
const IMAGE_OUTPUT_QUALITY = 0.92;

function byId(id) {
  return fieldMap.get(id) || { id, value: "", path: [] };
}

function html(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function money(value) {
  const raw = String(value || "").trim();
  if (raw.startsWith("$")) return html(raw);
  const number = Number(raw);
  if (Number.isNaN(number)) return html(raw);
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(number);
}

function parsePrice(value, fallback = 0) {
  const cleaned = String(value || "").replace(/[$,]/g, "").trim();
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizePrice(value, fallback = "0.00") {
  return parsePrice(value, Number(fallback || 0)).toFixed(2);
}

function normalizeMultiplier(value, fallback = "1") {
  const parsed = parsePrice(value, Number(fallback || 1));
  return Number.isFinite(parsed) && parsed > 0 ? String(parsed) : fallback;
}

function editable(id, tag, className = "") {
  const field = byId(id);
  return `<${tag} class="${className}" contenteditable="true" data-edit-text="${field.id}">${html(field.value)}</${tag}>`;
}

function editablePrice(id, tag, className = "") {
  const field = byId(id);
  return `<${tag} class="${className}" contenteditable="true" data-edit-price="${field.id}">${money(field.value)}</${tag}>`;
}

function imageSlot(id, className, altText) {
  const field = byId(id);
  const value = String(field.value || "").trim();
  const image = value
    ? `<img src="${html(value)}" alt="${html(altText || "Image")}">`
    : `<div class="${className.includes("ctcm-media") ? "ctcm-media-placeholder" : "ctcm-option-image-placeholder"}">Image</div>`;
  return `<div class="${className} admin-image-edit" data-edit-image="${field.id}" data-image-output-type="${IMAGE_OUTPUT_TYPE}">${image}<span class="admin-image-help">Drop image here</span></div>`;
}

function linkInput(id, label) {
  const field = byId(id);
  return `<div class="admin-link-edit">
    <label>${html(label)}</label>
    <input type="url" value="${html(field.value)}" data-edit-link="${field.id}">
  </div>`;
}

function pricingInput(id, label, kind = "price") {
  const field = byId(id);
  const value = kind === "multiplier" ? normalizeMultiplier(field.value) : normalizePrice(field.value);
  return `<div class="admin-link-edit">
    <label>${html(label)}</label>
    <input type="number" step="${kind === "multiplier" ? "0.01" : "0.01"}" min="${kind === "multiplier" ? "0.01" : "0"}" value="${html(value)}" data-edit-pricing="${field.id}" data-pricing-kind="${kind}">
  </div>`;
}

function getItems(prefix) {
  return fields
    .filter((field) => field.id.startsWith(prefix))
    .sort((a, b) => a.id.localeCompare(b.id));
}

function tabIndexes() {
  return [...new Set(getItems("tabs.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function categoryIndexes() {
  return [...new Set(getItems("configurator_categories.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function categoryItemIndexes(categoryIndex) {
  const prefix = `configurator_categories.${categoryIndex}.items.`;
  return [...new Set(getItems(prefix).map((field) => field.path[3]))].sort((a, b) => a - b);
}

function baseMetafieldIndexes() {
  return [...new Set(getItems("base_metafields.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function variantIndexes() {
  return [...new Set(getItems("variant_metafields.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function variantFieldIndexes(variantIndex) {
  const prefix = `variant_metafields.${variantIndex}.fields.`;
  return [...new Set(getItems(prefix).map((field) => field.path[3]))].sort((a, b) => a - b);
}

function renderHero() {
  return `<section class="ctcm-product">
    ${imageSlot("product_image", "ctcm-media", byId("product_name").value)}
    <div class="ctcm-product-info">
      ${editable("product_name", "h1", "ctcm-title")}
      ${editable("product_price", "p", "ctcm-price")}
      ${editable("product_description", "p", "ctcm-description")}
      <span class="ctcm-button" contenteditable="true" data-edit-text="primary_cta_text">${html(byId("primary_cta_text").value || "Add Base Product")}</span>
      ${linkInput("primary_cta_url", "Primary button link")}
    </div>
  </section>`;
}

function renderTabs() {
  const indexes = tabIndexes();
  if (!indexes.length) return "";
  const buttons = indexes.map((index, i) => {
    const active = i === 0 ? " is-active" : "";
    return `<li><button class="ctcm-tab-button${active}" type="button" data-ctcm-tab="admin-tab-${index}">
      <span contenteditable="true" data-edit-text="tabs.${index}.title">${html(byId(`tabs.${index}.title`).value)}</span>
    </button></li>`;
  }).join("");
  const panels = indexes.map((index, i) => {
    const active = i === 0 ? " is-active" : "";
    return `<div class="ctcm-tab-panel${active}" id="admin-tab-${index}" data-ctcm-tab-panel contenteditable="true" data-edit-text="tabs.${index}.content">${html(byId(`tabs.${index}.content`).value)}</div>`;
  }).join("");
  return `<section class="ctcm-section" data-ctcm-tabs>
    ${editable("product_info_heading", "h2")}
    <ul class="ctcm-tabs-list">${buttons}</ul>
    ${panels}
  </section>`;
}

function renderConfigurator() {
  const cats = categoryIndexes();
  if (!cats.length) return "";
  const baseCost = parsePrice(byId("configurator_base_cost").value);
  const categories = cats.map((categoryIndex, i) => {
    const itemIndexes = categoryItemIndexes(categoryIndex);
    const items = itemIndexes.map((itemIndex) => {
      const prefix = `configurator_categories.${categoryIndex}.items.${itemIndex}`;
      const name = byId(`${prefix}.name`).value;
      return `<div class="ctcm-option">
        ${imageSlot(`${prefix}.image`, "ctcm-option-image", name)}
        <div>
          <span class="ctcm-option-name" contenteditable="true" data-edit-text="${prefix}.name">${html(name)}</span>
          <span class="ctcm-option-meta">
            <span contenteditable="true" data-edit-text="${prefix}.variant">${html(byId(`${prefix}.variant`).value)}</span>
            ·
            ${editablePrice(`${prefix}.price`, "span")}
          </span>
        </div>
        <div class="ctcm-qty">
          <button type="button" disabled>-</button>
          <input type="number" value="0" disabled>
          <button type="button" disabled>+</button>
        </div>
      </div>`;
    }).join("");
    return `<div class="ctcm-category${i === 0 ? " is-open" : ""}">
      <button class="ctcm-category-toggle" type="button" data-ctcm-category-toggle>
        <span contenteditable="true" data-edit-text="configurator_categories.${categoryIndex}.name">${html(byId(`configurator_categories.${categoryIndex}.name`).value)}</span>
        <span>${itemIndexes.length} options</span>
      </button>
      <div class="ctcm-category-body">${items}</div>
    </div>`;
  }).join("");
  return `<section class="ctcm-section" data-ctcm-configurator>
    ${editable("configurator_heading", "h2")}
    <div class="ctcm-configurator-grid">
      <div>${categories}</div>
      <aside class="ctcm-summary">
        ${editable("summary_heading", "h3")}
        <div><p contenteditable="true" data-edit-text="empty_summary_text">${html(byId("empty_summary_text").value)}</p></div>
        <div class="ctcm-summary-total"><span>Total</span><span>${money(baseCost)}</span></div>
        ${pricingInput("configurator_base_cost", "Base item cost before configurations", "price")}
        ${pricingInput("configurator_price_multiplier", "Configuration price multiplier", "multiplier")}
        <span class="ctcm-button" contenteditable="true" data-edit-text="add_selected_text">${html(byId("add_selected_text").value)}</span>
      </aside>
    </div>
  </section>`;
}

function renderMetafields() {
  const base = baseMetafieldIndexes();
  const variants = variantIndexes();
  if (!base.length && !variants.length) return "";
  const baseRows = base.map((index) => `<dt contenteditable="true" data-edit-text="base_metafields.${index}.key">${html(byId(`base_metafields.${index}.key`).value)}</dt><dd contenteditable="true" data-edit-text="base_metafields.${index}.value">${html(byId(`base_metafields.${index}.value`).value)}</dd>`).join("");
  const variantOptions = variants.map((index) => `<option>${html(byId(`variant_metafields.${index}.variant`).value)}</option>`).join("");
  const variantRows = variants.map((variantIndex) => {
    const rows = variantFieldIndexes(variantIndex).map((fieldIndex) => `<dt contenteditable="true" data-edit-text="variant_metafields.${variantIndex}.fields.${fieldIndex}.key">${html(byId(`variant_metafields.${variantIndex}.fields.${fieldIndex}.key`).value)}</dt><dd contenteditable="true" data-edit-text="variant_metafields.${variantIndex}.fields.${fieldIndex}.value">${html(byId(`variant_metafields.${variantIndex}.fields.${fieldIndex}.value`).value)}</dd>`).join("");
    return `<dl>${rows}</dl>`;
  }).join("");
  const variantBlock = variants.length ? `<label><span contenteditable="true" data-edit-text="variant_metafields_label">${html(byId("variant_metafields_label").value)}</span><select>${variantOptions}</select></label>${variantRows}` : "";
  return `<section class="ctcm-section ctcm-metafields">
    ${editable("metafields_heading", "h2")}
    <dl>${baseRows}</dl>
    ${variantBlock}
  </section>`;
}

function renderEditor() {
  document.title = `${byId("site_title").value || "CTCM"} - Visual Backend`;
  document.getElementById("visual-editor").innerHTML = [
    renderHero(),
    renderTabs(),
    renderConfigurator(),
    renderMetafields()
  ].join("");
  bindEditorEvents();
}

function updateField(id, value) {
  const field = byId(id);
  field.value = value;
}

function bindEditorEvents() {
  document.querySelectorAll("[data-edit-text]").forEach((node) => {
    node.addEventListener("input", () => updateField(node.dataset.editText, node.textContent.trim()));
  });

  document.querySelectorAll("[data-edit-price]").forEach((node) => {
    node.addEventListener("input", () => updateField(node.dataset.editPrice, normalizePrice(node.textContent)));
    node.addEventListener("blur", () => {
      node.textContent = money(byId(node.dataset.editPrice).value);
    });
  });

  document.querySelectorAll("[data-edit-link]").forEach((node) => {
    node.addEventListener("input", () => updateField(node.dataset.editLink, node.value.trim()));
  });

  document.querySelectorAll("[data-edit-pricing]").forEach((node) => {
    node.addEventListener("input", () => {
      const kind = node.dataset.pricingKind;
      updateField(node.dataset.editPricing, kind === "multiplier" ? normalizeMultiplier(node.value) : normalizePrice(node.value));
    });
  });

  document.querySelectorAll("[data-edit-image]").forEach((slot) => {
    slot.addEventListener("click", () => selectImageSlot(slot));
    slot.addEventListener("dragenter", (event) => {
      event.preventDefault();
      slot.classList.add("is-drag-over");
    });
    slot.addEventListener("dragover", (event) => {
      event.preventDefault();
      slot.classList.add("is-drag-over");
    });
    slot.addEventListener("dragleave", () => slot.classList.remove("is-drag-over"));
    slot.addEventListener("drop", (event) => handleImageDrop(event, event.currentTarget));
  });
}

function selectImageSlot(slot) {
  document.querySelectorAll(".admin-image-edit").forEach((el) => el.classList.remove("is-selected"));
  slot.classList.add("is-selected");
  selectedImageFieldId = slot.dataset.editImage;
}

function setImageValue(fieldId, value) {
  updateField(fieldId, value);
  renderEditor();
  const slot = document.querySelector(`[data-edit-image="${fieldId}"]`);
  if (slot) selectImageSlot(slot);
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Unable to read image file."));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("Unable to load image file."));
      image.onload = () => resolve(image);
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

function slotSize(slot) {
  const rect = slot.getBoundingClientRect();
  const style = window.getComputedStyle(slot);
  const cssWidth = Number.parseFloat(style.width);
  const cssHeight = Number.parseFloat(style.height);
  const width = Math.max(1, Math.round(rect.width || slot.clientWidth || cssWidth || 800));
  const fallbackHeight = slot.classList.contains("ctcm-option-image") ? width : width;
  const height = Math.max(1, Math.round(rect.height || slot.clientHeight || cssHeight || fallbackHeight));
  return { width, height };
}

async function convertImageForSlot(file, slot) {
  const image = await loadImageFromFile(file);
  const target = slotSize(slot);
  const canvas = document.createElement("canvas");
  canvas.width = target.width;
  canvas.height = target.height;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
  const drawWidth = Math.round(image.naturalWidth * scale);
  const drawHeight = Math.round(image.naturalHeight * scale);
  const dx = Math.round((canvas.width - drawWidth) / 2);
  const dy = Math.round((canvas.height - drawHeight) / 2);
  ctx.drawImage(image, dx, dy, drawWidth, drawHeight);

  return canvas.toDataURL(slot.dataset.imageOutputType || IMAGE_OUTPUT_TYPE, IMAGE_OUTPUT_QUALITY);
}

function handleImageDrop(event, slot = null) {
  event.preventDefault();
  const droppedSlot = event.target.closest ? event.target.closest("[data-edit-image]") : null;
  const target = slot || droppedSlot || (selectedImageFieldId ? document.querySelector(`[data-edit-image="${selectedImageFieldId}"]`) : null);
  if (!target) return;
  target.classList.remove("is-drag-over");
  selectImageSlot(target);
  const fieldId = target.dataset.editImage;
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) {
    convertImageForSlot(file, target)
      .then((dataUrl) => setImageValue(fieldId, dataUrl))
      .catch(() => {
        const reader = new FileReader();
        reader.onload = () => setImageValue(fieldId, reader.result);
        reader.readAsDataURL(file);
      });
    return;
  }
  const url = event.dataTransfer.getData("text/uri-list") || event.dataTransfer.getData("text/plain");
  if (url) setImageValue(fieldId, url.trim());
}

document.addEventListener("dragover", (event) => {
  if (selectedImageFieldId) event.preventDefault();
});

document.addEventListener("drop", (event) => {
  if (!event.target.closest("[data-edit-image]") && selectedImageFieldId) {
    handleImageDrop(event);
  }
});

async function loadContent() {
  const response = await fetch("/api/content");
  const model = await response.json();
  fields = model.fields || [];
  fieldMap = new Map(fields.map((field) => [field.id, field]));
  renderEditor();
}

async function saveContent() {
  const status = document.getElementById("status");
  status.textContent = "Saving...";
  const response = await fetch("/api/content", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields })
  });
  if (!response.ok) {
    status.textContent = "Save failed.";
    return;
  }
  const payload = await response.json();
  fields = payload.content.fields || fields;
  fieldMap = new Map(fields.map((field) => [field.id, field]));
  status.textContent = "Saved.";
}

document.getElementById("save-button").addEventListener("click", saveContent);
loadContent();
