/*
 * Sign Maker - web app logic.
 *
 * Runs entirely in the browser: no server, no backend. The label list and
 * prefix history are saved to localStorage per sign type, so they're still
 * there next time you visit on the same device/browser (this is real
 * per-device persistence, unlike a shared multi-user hosted app).
 */

const STORAGE_PREFIX = "signmaker_v1_";

const state = {
  signType: "sticky",
  labels: { sticky: [], hanging: [] }, // { raw, display }
  knownPrefixes: { sticky: [], hanging: [] },
};

// ------------------------------------------------------------- storage
function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch (err) {
    return fallback;
  }
}

function saveJSON(key, value) {
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
  } catch (err) {
    // Storage can fail (private browsing, quota, etc) - not fatal, just
    // means the list won't be remembered next visit.
    console.warn("Could not save to localStorage:", err);
  }
}

function loadAllState() {
  state.signType = loadJSON("lastSignType", "sticky");
  for (const key of Object.keys(SIGN_TYPES)) {
    const rawTokens = loadJSON(`labels_${key}`, []);
    state.labels[key] = rawTokens.map((raw) => ({ raw, display: describeToken(raw) }));
    state.knownPrefixes[key] = loadJSON(`prefixes_${key}`, []);
  }
}

function saveLabels(signType) {
  saveJSON(`labels_${signType}`, state.labels[signType].map((item) => item.raw));
}

function savePrefixes(signType) {
  saveJSON(`prefixes_${signType}`, state.knownPrefixes[signType]);
}

// --------------------------------------------------------------- DOM refs
const el = {};
function cacheRefs() {
  el.typeButtons = document.querySelectorAll(".type-button");
  el.prefixInput = document.getElementById("prefix-input");
  el.prefixList = document.getElementById("prefix-suggestions");
  el.startInput = document.getElementById("start-input");
  el.endInput = document.getElementById("end-input");
  el.addBtn = document.getElementById("add-btn");
  el.warning = document.getElementById("quick-add-warning");
  el.labelList = document.getElementById("label-list");
  el.countLabel = document.getElementById("count-label");
  el.removeSelectedBtn = document.getElementById("remove-selected-btn");
  el.removeAllBtn = document.getElementById("remove-all-btn");
  el.pasteToggle = document.getElementById("paste-toggle");
  el.pasteBox = document.getElementById("paste-box");
  el.pasteTextarea = document.getElementById("paste-textarea");
  el.pasteAddBtn = document.getElementById("paste-add-btn");
  el.previewCanvas = document.getElementById("preview-canvas");
  el.previewCaption = document.getElementById("preview-caption");
  el.generateBtn = document.getElementById("generate-btn");
  el.statusMessage = document.getElementById("status-message");
}

// ------------------------------------------------------------- rendering
function currentLabels() {
  return state.labels[state.signType];
}

function refreshTypeButtons() {
  el.typeButtons.forEach((btn) => {
    const isActive = btn.dataset.type === state.signType;
    btn.classList.toggle("active", isActive);
  });
}

function refreshPrefixSuggestions() {
  el.prefixList.innerHTML = "";
  for (const prefix of state.knownPrefixes[state.signType]) {
    const opt = document.createElement("option");
    opt.value = prefix;
    el.prefixList.appendChild(opt);
  }
}

function refreshLabelList() {
  const labels = currentLabels();
  el.labelList.innerHTML = "";
  for (const item of labels) {
    const li = document.createElement("li");
    li.textContent = item.display;
    li.dataset.raw = item.raw;
    li.addEventListener("click", () => {
      li.classList.toggle("selected");
      updatePreview();
    });
    el.labelList.appendChild(li);
  }

  if (labels.length === 0) {
    el.countLabel.textContent = "No sign labels added yet.";
  } else {
    let total = 0;
    for (const item of labels) {
      const match = RANGE_RE.exec(item.raw);
      if (match) {
        total += Math.abs(parseInt(match[3], 10) - parseInt(match[2], 10)) + 1;
      } else {
        total += 1;
      }
    }
    const word = labels.length === 1 ? "entry" : "entries";
    el.countLabel.textContent = `${labels.length} ${word} added \u2014 ${total} sign(s) total.`;
  }

  saveLabels(state.signType);
  updatePreview();
}

function getSelectedLabelLis() {
  return Array.from(el.labelList.querySelectorAll("li.selected"));
}

// ------------------------------------------------------------ preview
function getPreviewLabel() {
  const selected = getSelectedLabelLis();
  if (selected.length > 0) {
    return firstLabelOfToken(selected[selected.length - 1].dataset.raw);
  }
  const prefix = el.prefixInput.value.trim();
  const start = el.startInput.value.trim();
  if (prefix && /^\d+$/.test(start)) {
    return `${prefix}-${start}`;
  }
  const labels = currentLabels();
  if (labels.length > 0) {
    return firstLabelOfToken(labels[labels.length - 1].raw);
  }
  return "a-001";
}

function updatePreview() {
  const label = getPreviewLabel();
  const cfg = SIGN_TYPES[state.signType];
  const canvas = el.previewCanvas;
  const width = canvas.width;
  const height = state.signType === "sticky"
    ? Math.round(width * (STICKY.cellYOffset / STICKY.pageSize[0]))
    : Math.round(width * (HANGING.pageSize[1] / HANGING.pageSize[0]));
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  drawPreview(ctx, width, height, state.signType, label);
  el.previewCaption.textContent = `\u2014 ${cfg.label}, showing: ${label}`;
}

// -------------------------------------------------------------- actions
function switchSignType(newType) {
  if (newType === state.signType || !(newType in SIGN_TYPES)) return;
  state.signType = newType;
  saveJSON("lastSignType", newType);
  el.prefixInput.value = "";
  el.startInput.value = "";
  el.endInput.value = "";
  el.warning.textContent = "";
  refreshTypeButtons();
  refreshPrefixSuggestions();
  refreshLabelList();
}

function showWarning(message) {
  el.warning.textContent = message;
}

function addToken(rawToken) {
  const trimmed = rawToken.trim();
  if (!trimmed) return false;
  const labels = currentLabels();
  if (labels.some((item) => item.raw === trimmed)) return false;
  labels.push({ raw: trimmed, display: describeToken(trimmed) });
  return true;
}

function rememberPrefix(prefix) {
  const list = state.knownPrefixes[state.signType];
  if (prefix && !list.includes(prefix)) {
    list.push(prefix);
    list.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
    savePrefixes(state.signType);
    refreshPrefixSuggestions();
  }
}

function handleQuickAdd() {
  const prefix = el.prefixInput.value.trim();
  const start = el.startInput.value.trim();
  const end = el.endInput.value.trim();
  showWarning("");

  if (!prefix) {
    showWarning('Type or choose what the sign "starts with" first (e.g. "a").');
    return;
  }
  if (!start) {
    showWarning('Type a number (e.g. "001").');
    return;
  }
  if (!/^\d+$/.test(start) || (end && !/^\d+$/.test(end))) {
    showWarning("The number field(s) should contain digits only, e.g. 001.");
    return;
  }

  const token = end ? `${prefix}-${start}:${end}` : `${prefix}-${start}`;
  addToken(token);
  rememberPrefix(prefix);
  refreshLabelList();

  if (end) {
    el.startInput.value = incrementNumber(end);
    el.endInput.value = "";
  } else {
    el.startInput.value = incrementNumber(start);
  }
  el.startInput.focus();
}

function handleRemoveSelected() {
  const selectedRaws = new Set(getSelectedLabelLis().map((li) => li.dataset.raw));
  if (selectedRaws.size === 0) return;
  state.labels[state.signType] = currentLabels().filter((item) => !selectedRaws.has(item.raw));
  refreshLabelList();
}

function handleRemoveAll() {
  if (currentLabels().length === 0) return;
  if (!confirm("Remove every label from this sign type's list? This also clears what's remembered for next time.")) {
    return;
  }
  state.labels[state.signType] = [];
  refreshLabelList();
}

function handlePasteAdd() {
  const pieces = el.pasteTextarea.value.split(/[,\s]+/).map((p) => p.trim()).filter(Boolean);
  if (pieces.length === 0) {
    showWarning("Type or paste at least one label first.");
    return;
  }
  for (const piece of pieces) addToken(piece);
  const { groups } = groupByPrefix(parseLabels(pieces));
  for (const prefix of groups.keys()) rememberPrefix(prefix);
  refreshLabelList();
  el.pasteTextarea.value = "";
  el.pasteBox.classList.add("hidden");
}

async function handleGenerate() {
  const labels = currentLabels();
  if (labels.length === 0) {
    showWarning("Add at least one sign label first.");
    return;
  }

  el.generateBtn.disabled = true;
  el.statusMessage.className = "status working";
  el.statusMessage.textContent = "Working \u2026 creating your PDF files. This only takes a moment.";

  try {
    const tokens = labels.map((item) => item.raw);
    const { groups } = groupByPrefix(parseLabels(tokens));
    for (const prefix of groups.keys()) rememberPrefix(prefix);

    const cfg = SIGN_TYPES[state.signType];
    const zip = new JSZip();
    let fileCount = 0;
    let totalSigns = 0;

    for (const [prefix, groupLabels] of groups.entries()) {
      const sorted = [...groupLabels].sort(compareNaturalKeys);
      const doc = buildGroupPdf(state.signType, sorted);
      const pdfBytes = doc.output("arraybuffer");
      zip.file(`${safeFilename(prefix)}.pdf`, pdfBytes);
      fileCount += 1;
      totalSigns += sorted.length;
    }

    const zipBuffer = await zip.generateAsync({ type: "arraybuffer" });
    const zipBlob = new Blob([zipBuffer], { type: "application/zip" });
    const zipName = `${cfg.label.replace(/\s+/g, "_")}.zip`;
    downloadBlob(zipBlob, zipName);

    el.statusMessage.className = "status success";
    el.statusMessage.textContent =
      `\u2705 All done! Created ${fileCount} PDF file(s) for ${totalSigns} sign(s). ` +
      `Your download (${zipName}) should appear in your browser's downloads.`;
  } catch (err) {
    el.statusMessage.className = "status warning";
    el.statusMessage.textContent = `\u26a0 Something went wrong: ${err.message}`;
    console.error(err);
  } finally {
    el.generateBtn.disabled = false;
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// ---------------------------------------------------------------- init
function init() {
  cacheRefs();
  loadAllState();
  refreshTypeButtons();
  refreshPrefixSuggestions();
  refreshLabelList();

  el.typeButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchSignType(btn.dataset.type));
  });

  el.addBtn.addEventListener("click", handleQuickAdd);
  [el.prefixInput, el.startInput, el.endInput].forEach((input) => {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleQuickAdd();
    });
    input.addEventListener("input", updatePreview);
  });

  el.removeSelectedBtn.addEventListener("click", handleRemoveSelected);
  el.removeAllBtn.addEventListener("click", handleRemoveAll);

  el.pasteToggle.addEventListener("click", () => el.pasteBox.classList.toggle("hidden"));
  el.pasteAddBtn.addEventListener("click", handlePasteAdd);

  el.generateBtn.addEventListener("click", handleGenerate);
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", init);
}

if (typeof module !== "undefined") {
  module.exports = {
    state, loadAllState, switchSignType, addToken, handleQuickAdd,
    handleRemoveSelected, handleRemoveAll, refreshLabelList, currentLabels,
    getPreviewLabel, cacheRefs, init,
  };
}
