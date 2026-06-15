const soundDefinitions = [
  { name: "C4", frequency: 261.63, color: "#1f7a8c" },
  { name: "D4", frequency: 293.66, color: "#9b5de5" },
  { name: "E4", frequency: 329.63, color: "#0f766e" },
  { name: "F4", frequency: 349.23, color: "#2563eb" },
  { name: "G4", frequency: 392.00, color: "#d97706" },
  { name: "A4", frequency: 440.00, color: "#7c3aed" },
  { name: "B4", frequency: 493.88, color: "#be123c" },
  { name: "C5", frequency: 523.25, color: "#047857" },
  { name: "D5", frequency: 587.33, color: "#b45309" },
  { name: "E5", frequency: 659.25, color: "#0369a1" },
  { name: "F5", frequency: 698.46, color: "#a21caf" },
  { name: "G5", frequency: 783.99, color: "#4d7c0f" }
];

const storageKey = "ui-test-dataset";
const buttonsContainer = document.querySelector("#sound-buttons");
const datasetMessage = document.querySelector("#dataset-message");
const saveStatus = document.querySelector("#save-status");
const connectFileButton = document.querySelector("#connect-file");
const downloadDataButton = document.querySelector("#download-data");
const resetDataButton = document.querySelector("#reset-data");

let audioContext;
let fileHandle = null;
let state = loadState();

function createInitialState() {
  return {
    createdAt: new Date().toISOString(),
    buttons: soundDefinitions.map((sound, index) => ({
      id: index + 1,
      name: sound.name,
      frequency: sound.frequency,
      count: 0,
      presses: []
    }))
  };
}

function loadState() {
  const saved = localStorage.getItem(storageKey);

  if (!saved) {
    return createInitialState();
  }

  try {
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed.buttons) || parsed.buttons.length !== soundDefinitions.length) {
      return createInitialState();
    }
    parsed.buttons = parsed.buttons.map((button, index) => ({
      ...button,
      id: index + 1,
      name: soundDefinitions[index].name,
      frequency: soundDefinitions[index].frequency
    }));
    return parsed;
  } catch {
    return createInitialState();
  }
}

function saveState() {
  localStorage.setItem(storageKey, JSON.stringify(state));
}

function getDatasetText() {
  const now = new Date().toISOString();
  const total = state.buttons.reduce((sum, button) => sum + button.count, 0);
  const lines = [
    "UI_TEST_DATASET",
    `Created At: ${state.createdAt}`,
    `Last Updated: ${now}`,
    `Total Presses: ${total}`,
    "",
    "Button Summary:"
  ];

  state.buttons.forEach((button) => {
    lines.push(`Button ${button.id} - ${button.name} (${button.frequency.toFixed(2)} Hz): ${button.count}`);
  });

  lines.push("", "Press Log:");

  const events = state.buttons
    .flatMap((button) => button.presses.map((time) => ({
      id: button.id,
      name: button.name,
      frequency: button.frequency,
      time
    })))
    .sort((first, second) => new Date(first.time) - new Date(second.time));

  if (events.length === 0) {
    lines.push("No button presses recorded yet.");
  } else {
    events.forEach((event, index) => {
      lines.push(`${index + 1}. ${event.time} | Button ${event.id} | ${event.name} | ${event.frequency.toFixed(2)} Hz`);
    });
  }

  return `${lines.join("\n")}\n`;
}

function renderButtons() {
  buttonsContainer.innerHTML = "";

  soundDefinitions.forEach((sound, index) => {
    const button = document.createElement("button");
    button.className = "sound-button";
    button.type = "button";
    button.style.setProperty("--button-color", sound.color);
    button.setAttribute("aria-label", `Play ${sound.name} tone`);
    button.innerHTML = `
      <span class="sound-name">${index + 1}. ${sound.name}</span>
      <span class="sound-frequency">${sound.frequency.toFixed(2)} Hz</span>
    `;
    button.addEventListener("click", () => recordPress(index));
    buttonsContainer.appendChild(button);
  });
}

function renderDataset() {
  datasetMessage.textContent = "Dataset is recording to browser storage and the text file export.";
}

function playSound(sound) {
  audioContext = audioContext || new AudioContext();

  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  const start = audioContext.currentTime;
  const end = start + 0.22;

  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(sound.frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(0.22, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, end);

  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start(start);
  oscillator.stop(end);
}

async function recordPress(index) {
  const sound = soundDefinitions[index];
  const button = state.buttons[index];

  playSound(sound);
  button.count += 1;
  button.presses.push(new Date().toISOString());
  saveState();
  renderButtons();
  renderDataset();
  await writeConnectedDataset();
}

async function writeConnectedDataset() {
  if (!fileHandle) {
    saveStatus.textContent = "Saved in browser";
    return;
  }

  try {
    const writable = await fileHandle.createWritable();
    await writable.write(getDatasetText());
    await writable.close();
    saveStatus.textContent = "Dataset file updated";
  } catch (error) {
    saveStatus.textContent = "File update blocked";
  }
}

async function connectDatasetFile() {
  if (!window.showSaveFilePicker) {
    saveStatus.textContent = "Use Download Dataset";
    return;
  }

  try {
    fileHandle = await window.showSaveFilePicker({
      suggestedName: "UI_TEST_DATASET.txt",
      types: [{
        description: "Text dataset",
        accept: { "text/plain": [".txt"] }
      }]
    });
    await writeConnectedDataset();
  } catch (error) {
    saveStatus.textContent = "Dataset not connected";
  }
}

function downloadDataset() {
  const blob = new Blob([getDatasetText()], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = "UI_TEST_DATASET.txt";
  link.click();
  URL.revokeObjectURL(url);
  saveStatus.textContent = "Dataset downloaded";
}

async function resetDataset() {
  const confirmed = window.confirm("Reset all button counts and press times?");
  if (!confirmed) {
    return;
  }

  state = createInitialState();
  saveState();
  renderButtons();
  renderDataset();
  await writeConnectedDataset();
}

connectFileButton.addEventListener("click", connectDatasetFile);
downloadDataButton.addEventListener("click", downloadDataset);
resetDataButton.addEventListener("click", resetDataset);

renderButtons();
renderDataset();
