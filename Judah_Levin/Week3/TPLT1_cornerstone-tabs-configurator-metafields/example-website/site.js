const assetRoot = '../cornerstone-tabs-configurator-metafields/assets';
const productImage = `${assetRoot}/img/ProductDefault.gif`;
const brandImage = `${assetRoot}/img/BrandDefault.gif`;
const giftImage = `${assetRoot}/img/GiftCertificate.png`;

const customFields = [
    { name: '__newtab', value: 'Shipping Specs' },
    { name: 'Ships From', value: 'Austin, TX warehouse' },
    { name: 'Lead Time', value: '2 business days' },
    { name: '__newtab', value: 'Care Instructions' },
    { name: 'Cleaning', value: 'Wipe with a dry microfiber cloth' },
    { name: 'Storage', value: 'Store components in labeled anti-static sleeves' },
];

const configuratorGroups = [
    {
        name: '--CPU',
        products: [
            { id: 101, name: 'Base Controller', price: 89, image: productImage },
            { id: 102, name: 'Performance Controller', price: 139, image: brandImage },
        ],
    },
    {
        name: '--Expansion',
        products: [
            { id: 201, name: 'I/O Expansion Card', price: 49, image: giftImage },
            { id: 202, name: 'Thermal Upgrade Kit', price: 34, image: productImage },
        ],
    },
    {
        name: '--Accessories',
        products: [
            { id: 301, name: 'Mounting Rail Set', price: 24, image: brandImage },
            { id: 302, name: 'Cable Organizer Pack', price: 18, image: giftImage },
        ],
    },
];

const baseMetafields = [
    { namespace: 'Base Product Metafield', key: 'Material', value: 'Powder-coated aluminum' },
    { namespace: 'Base Product Metafield', key: 'Product Class', value: 'Configurable assembly' },
    { namespace: 'Base Product Metafield', key: 'Support Level', value: 'Priority' },
];

const variantMetafields = [
    { namespace: 'Variant Product Metafield', key: 'Variant SKU', value: 'CF-TABS-001-PERF' },
    { namespace: 'Variant Product Metafield-2', key: 'Compatibility', value: 'Performance and expansion builds' },
];

const selections = new Map();
const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const editableStorageKey = 'cornerstoneExample1Edits';

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
}

function slugify(text) {
    return text.toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
}

function renderDynamicTabs() {
    const tabsRoot = document.querySelector('[data-custom-tabs]');
    const tabList = tabsRoot.querySelector('.tabs');
    const contents = tabsRoot.querySelector('.tabs-contents');
    let currentGroup = null;

    customFields.forEach((field) => {
        if (field.name === '__newtab') {
            currentGroup = { label: field.value, fields: [] };
            const id = `tab-cf-${slugify(field.value)}`;
            const li = document.createElement('li');
            li.className = 'tab';
            li.setAttribute('role', 'presentation');
            li.innerHTML = `<button class="tab-title" type="button" role="tab" aria-selected="false" data-tab-target="${id}">${field.value}</button>`;
            tabList.append(li);

            const panel = document.createElement('div');
            panel.className = 'tab-content';
            panel.id = id;
            panel.hidden = true;
            panel.setAttribute('role', 'tabpanel');
            contents.append(panel);
            currentGroup.panel = panel;
        } else if (currentGroup) {
            currentGroup.fields.push(field);
            currentGroup.panel.innerHTML = `<dl class="productView-info">${
                currentGroup.fields.map((item) => (
                    `<dt class="productView-info-name">${item.name}:</dt><dd class="productView-info-value">${item.value}</dd>`
                )).join('')
            }</dl>`;
        }
    });

    tabsRoot.addEventListener('click', (event) => {
        const button = event.target.closest('.tab-title');
        if (!button) return;

        tabList.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('is-active'));
        tabList.querySelectorAll('.tab-title').forEach((tabButton) => tabButton.setAttribute('aria-selected', 'false'));
        contents.querySelectorAll('.tab-content').forEach((panel) => {
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

function parseCategoryName(fieldName) {
    return fieldName.replace(/^--/, '').trim();
}

function renderConfigurator() {
    const container = document.querySelector('[data-configurator-categories]');
    configuratorGroups.forEach((group) => {
        const category = document.createElement('section');
        category.className = 'configurator-category';
        category.innerHTML = `
            <button class="configurator-category-header" type="button" aria-expanded="true">
                <span class="configurator-category-title">${parseCategoryName(group.name)}</span>
                <span class="configurator-category-count">${group.products.length} products</span>
            </button>
            <div class="configurator-products"></div>
        `;

        const productList = category.querySelector('.configurator-products');
        group.products.forEach((product) => {
            const item = document.createElement('article');
            item.className = 'configurator-product';
            item.innerHTML = `
                <img src="${product.image}" alt="">
                <div>
                    <span class="configurator-product-name">${product.name}</span>
                    <span class="configurator-product-price">${currency.format(product.price)}</span>
                </div>
                <div class="quantity-control" aria-label="${product.name} quantity">
                    <button type="button" data-step="-1" data-product-id="${product.id}">-</button>
                    <input value="0" inputmode="numeric" aria-label="${product.name} quantity" data-quantity="${product.id}">
                    <button type="button" data-step="1" data-product-id="${product.id}">+</button>
                </div>
            `;
            productList.append(item);
        });

        container.append(category);
    });

    container.addEventListener('click', (event) => {
        const header = event.target.closest('.configurator-category-header');
        if (header) {
            const category = header.closest('.configurator-category');
            const collapsed = category.classList.toggle('is-collapsed');
            header.setAttribute('aria-expanded', String(!collapsed));
            return;
        }

        const stepper = event.target.closest('[data-step]');
        if (!stepper) return;
        const id = Number(stepper.dataset.productId);
        const product = configuratorGroups.flatMap((group) => group.products).find((item) => item.id === id);
        const nextQty = Math.max(0, (selections.get(id)?.quantity || 0) + Number(stepper.dataset.step));

        if (nextQty === 0) {
            selections.delete(id);
        } else {
            selections.set(id, { ...product, quantity: nextQty });
        }

        document.querySelector(`[data-quantity="${id}"]`).value = nextQty;
        renderSelections();
        renderVariantMetafields(nextQty > 0);
    });
}

function renderSelections() {
    const list = document.querySelector('[data-selection-list]');
    const total = [...selections.values()].reduce((sum, item) => sum + item.price * item.quantity, 349);
    document.querySelector('[data-total]').textContent = currency.format(total);

    if (selections.size === 0) {
        list.innerHTML = '<p class="selection-empty">No configurable components selected yet.</p>';
        return;
    }

    list.innerHTML = [...selections.values()].map((item) => (
        `<div class="selection-item"><span>${item.quantity} x ${item.name}</span><strong>${currency.format(item.price * item.quantity)}</strong></div>`
    )).join('');
}

function renderMetafields(container, title, fields) {
    container.innerHTML = `
        <p class="productView-metafields-title">${title}</p>
        <dl class="productView-info productView-metafields-list">
            ${fields.map((field) => (
                `<dt class="productView-info-name">${field.namespace} &middot; ${field.key}</dt><dd class="productView-info-value">${field.value}</dd>`
            )).join('')}
        </dl>
    `;
}

function renderVariantMetafields(hasSelection) {
    const container = document.querySelector('[data-product-metafields-variant]');
    if (!hasSelection && selections.size === 0) {
        container.innerHTML = '<p class="productView-metafields-title">Variant metafields</p><p class="selection-empty">Select a configurator item to simulate variant metafields loading.</p>';
        return;
    }
    renderMetafields(container, 'Variant metafields', variantMetafields);
}

applySavedEdits();
renderDynamicTabs();
renderConfigurator();
renderSelections();
renderMetafields(document.querySelector('[data-product-metafields-base]'), 'Product metafields', baseMetafields);
renderVariantMetafields(false);
