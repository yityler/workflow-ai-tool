const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const assetRoot = '../cornerstone-tabs-configurator-metafields/assets';
const editableStorageKey = 'cornerstoneExample2Edits';

const variants = {
    standard: {
        sku: 'CF-PDP-100-STD',
        price: 349,
        metafields: [
            ['Variant Product Metafield', 'Variant SKU', 'CF-PDP-100-STD'],
            ['Variant Product Metafield', 'Compatibility', 'Base PDP build'],
        ],
    },
    performance: {
        sku: 'CF-PDP-100-PERF',
        price: 429,
        metafields: [
            ['Variant Product Metafield-2', 'Variant SKU', 'CF-PDP-100-PERF'],
            ['Variant Product Metafield-2', 'Compatibility', 'Expansion and controller upgrades'],
        ],
    },
    field: {
        sku: 'CF-PDP-100-FIELD',
        price: 399,
        metafields: [
            ['Variant-2 Product Metafield', 'Variant SKU', 'CF-PDP-100-FIELD'],
            ['Variant-2 Product Metafield', 'Compatibility', 'Field service kit'],
        ],
    },
};

const addons = [
    { id: 'rail', name: 'Mounting Rail Set', price: 24, image: `${assetRoot}/img/BrandDefault.gif` },
    { id: 'thermal', name: 'Thermal Upgrade Kit', price: 34, image: `${assetRoot}/img/ProductDefault.gif` },
    { id: 'cert', name: 'Deployment Certificate', price: 18, image: `${assetRoot}/img/GiftCertificate.png` },
];

const dynamicTabs = [
    {
        label: 'Shipping Specs',
        fields: [
            ['Ships From', 'Austin, TX warehouse'],
            ['Lead Time', '2 business days'],
        ],
    },
    {
        label: 'Care Instructions',
        fields: [
            ['Cleaning', 'Wipe with a dry microfiber cloth'],
            ['Storage', 'Store configured parts in labeled sleeves'],
        ],
    },
];

const productMetafields = [
    ['Base Product Metafield', 'Material', 'Powder-coated aluminum'],
    ['Base Product Metafield', 'Product Class', 'Configurable assembly'],
    ['Base Product Metafield', 'Support Level', 'Priority'],
];

let currentVariant = 'standard';
const selectedAddons = new Set();

function applySavedEdits() {
    let edits = {};
    const encodedEdits = new URLSearchParams(window.location.search).get('edits');
    try {
        if (encodedEdits) {
            const binary = atob(encodedEdits);
            const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
            edits = JSON.parse(new TextDecoder().decode(bytes));
            localStorage.setItem(editableStorageKey, JSON.stringify(edits));
        } else {
            edits = JSON.parse(localStorage.getItem(editableStorageKey) || '{}');
        }
    } catch (error) {
        edits = {};
    }

    document.querySelectorAll('[data-edit-text]').forEach((node) => {
        const value = edits[node.dataset.editText];
        if (value) node.textContent = value;
    });

    document.querySelectorAll('[data-edit-image]').forEach((node) => {
        const value = edits[node.dataset.editImage];
        if (value) node.src = value;
    });

    document.querySelectorAll('[data-edit-data-image]').forEach((node) => {
        const value = edits[node.dataset.editDataImage];
        if (value) node.dataset.image = value;
    });
}

function slugify(value) {
    return value.toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
}

function renderAddons() {
    const target = document.querySelector('[data-addon-list]');
    target.innerHTML = addons.map((addon) => `
        <label class="addon">
            <img src="${addon.image}" alt="">
            <span>
                <strong>${addon.name}</strong>
                <span>${currency.format(addon.price)}</span>
            </span>
            <input type="checkbox" value="${addon.id}" aria-label="Add ${addon.name}">
        </label>
    `).join('');

    target.addEventListener('change', (event) => {
        if (event.target.checked) {
            selectedAddons.add(event.target.value);
        } else {
            selectedAddons.delete(event.target.value);
        }
        updateTotal();
    });
}

function updateTotal() {
    const addonTotal = addons
        .filter((addon) => selectedAddons.has(addon.id))
        .reduce((total, addon) => total + addon.price, 0);
    const total = variants[currentVariant].price + addonTotal;
    const selectedCount = selectedAddons.size;

    document.querySelector('[data-total-price]').textContent = currency.format(total);
    document.querySelector('[data-cart-note]').textContent = selectedCount
        ? `${selectedCount} configurator add-on${selectedCount === 1 ? '' : 's'} selected.`
        : 'Base product selected. Choose add-ons to update the PDP total.';
}

function renderDynamicTabs() {
    const root = document.querySelector('[data-tabs]');
    const tabList = root.querySelector('.tabs');
    const panels = root.querySelector('.tab-panels');

    dynamicTabs.forEach((tab) => {
        const id = `tab-cf-${slugify(tab.label)}`;
        tabList.insertAdjacentHTML('beforeend', `
            <li class="tab" role="presentation">
                <button class="tab-title" type="button" role="tab" aria-selected="false" data-tab-target="${id}">${tab.label}</button>
            </li>
        `);
        panels.insertAdjacentHTML('beforeend', `
            <div class="tab-panel" id="${id}" role="tabpanel" hidden>
                <dl class="product-facts">
                    ${tab.fields.map(([name, value]) => `<dt>${name}:</dt><dd>${value}</dd>`).join('')}
                </dl>
            </div>
        `);
    });

    root.addEventListener('click', (event) => {
        const button = event.target.closest('.tab-title');
        if (!button) return;

        tabList.querySelectorAll('.tab').forEach((item) => item.classList.remove('is-active'));
        tabList.querySelectorAll('.tab-title').forEach((item) => item.setAttribute('aria-selected', 'false'));
        panels.querySelectorAll('.tab-panel').forEach((panel) => {
            panel.classList.remove('is-active');
            panel.hidden = true;
        });

        button.closest('.tab').classList.add('is-active');
        button.setAttribute('aria-selected', 'true');
        const panel = document.getElementById(button.dataset.tabTarget);
        panel.classList.add('is-active');
        panel.hidden = false;
    });
}

function renderMetafields(target, fields) {
    target.innerHTML = fields.map(([namespace, key, value]) => `
        <dt>${namespace} ${key}</dt>
        <dd>${value}</dd>
    `).join('');
}

function selectVariant(key) {
    currentVariant = key;
    document.querySelectorAll('[data-variant]').forEach((button) => {
        button.classList.toggle('is-active', button.dataset.variant === key);
    });
    document.querySelector('[data-sku]').textContent = variants[key].sku;
    renderMetafields(document.querySelector('[data-variant-metafields]'), variants[key].metafields);
    updateTotal();
}

document.querySelector('[data-variant-options]').addEventListener('click', (event) => {
    const button = event.target.closest('[data-variant]');
    if (!button) return;
    selectVariant(button.dataset.variant);
});

document.querySelector('.thumb-grid').addEventListener('click', (event) => {
    const button = event.target.closest('[data-image]');
    if (!button) return;

    document.querySelectorAll('.thumb').forEach((thumb) => thumb.classList.remove('is-active'));
    button.classList.add('is-active');
    document.querySelector('[data-main-image]').src = button.dataset.image;
});

applySavedEdits();
renderAddons();
renderDynamicTabs();
renderMetafields(document.querySelector('[data-product-metafields]'), productMetafields);
selectVariant('standard');
