const storageKey = 'cornerstoneExample1Edits';
const form = document.querySelector('[data-editor-form]');
const status = document.querySelector('[data-status]');
const previewLink = document.querySelector('[data-preview-link]');

function encodeEdits(values) {
    const bytes = new TextEncoder().encode(JSON.stringify(values));
    let binary = '';
    bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
    });
    return btoa(binary);
}

function loadSavedValues() {
    let saved = {};
    try {
        saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    } catch (error) {
        saved = {};
    }

    Object.entries(saved).forEach(([key, value]) => {
        const field = form.elements[key];
        if (field) field.value = value;
    });
}

function collectValues() {
    return Array.from(new FormData(form).entries()).reduce((values, [key, value]) => {
        values[key] = value.trim();
        return values;
    }, {});
}

form.addEventListener('submit', (event) => {
    event.preventDefault();
    const values = collectValues();
    localStorage.setItem(storageKey, JSON.stringify(values));
    previewLink.href = `index.html?edits=${encodeURIComponent(encodeEdits(values))}`;
    status.textContent = 'Saved. Use View Site to open the edited page.';
});

document.querySelector('[data-reset]').addEventListener('click', () => {
    localStorage.removeItem(storageKey);
    form.reset();
    status.textContent = 'Reset to defaults.';
});

loadSavedValues();
