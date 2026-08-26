/*
 * Shared label logic - a JS port of signs_common.py. Parsing, grouping, and
 * natural sort order match the Python desktop/CLI tools exactly, so a batch
 * built here behaves the same way (same grouping rules, same sort order)
 * as one built with the desktop app.
 */

const LABEL_RE = /^\s*(.+?)\s*-\s*(\S+)\s*$/;
const RANGE_RE = /^\s*(.+?)\s*-\s*(\d+)\s*:\s*(\d+)\s*$/;

function expandRange(token) {
  const match = RANGE_RE.exec(token);
  if (!match) return null;
  const prefix = match[1];
  let start = parseInt(match[2], 10);
  let end = parseInt(match[3], 10);
  if (end < start) [start, end] = [end, start];
  const width = match[2].length;
  const out = [];
  for (let n = start; n <= end; n++) {
    out.push(`${prefix}-${String(n).padStart(width, "0")}`);
  }
  return out;
}

function parseLabels(tokens) {
  const labels = [];
  for (const token of tokens) {
    for (const piece of token.split(/[,\s]+/)) {
      const trimmed = piece.trim();
      if (!trimmed) continue;
      const expanded = expandRange(trimmed);
      if (expanded) {
        labels.push(...expanded);
      } else {
        labels.push(trimmed);
      }
    }
  }
  return labels;
}

function groupByPrefix(labels) {
  const groups = new Map();
  const skipped = [];
  for (const label of labels) {
    const match = LABEL_RE.exec(label);
    let prefix;
    if (match) {
      prefix = match[1];
    } else {
      prefix = label.trim();
      if (!prefix) {
        skipped.push(label);
        continue;
      }
    }
    if (!groups.has(prefix)) groups.set(prefix, []);
    const bucket = groups.get(prefix);
    if (!bucket.includes(label)) bucket.push(label);
  }
  return { groups, skipped };
}

function safeFilename(text) {
  const stem = text.replace(/[<>:"/\\|?*]/g, "_").trim().replace(/\.+$/, "");
  return stem || "unnamed";
}

/** Sorts a-002 before a-010, unlike plain text sort. Matches natural_sort_key(). */
function naturalSortKey(label) {
  const match = LABEL_RE.exec(label);
  if (match && /^\d+$/.test(match[2])) {
    return [0, parseInt(match[2], 10), label];
  }
  return [1, 0, label];
}

function compareNaturalKeys(a, b) {
  const ka = naturalSortKey(a);
  const kb = naturalSortKey(b);
  for (let i = 0; i < ka.length; i++) {
    if (ka[i] < kb[i]) return -1;
    if (ka[i] > kb[i]) return 1;
  }
  return 0;
}

/** Turns a raw token into plain-English text for the on-page list. */
function describeToken(token) {
  const match = RANGE_RE.exec(token);
  if (match) {
    const [, prefix, start, end] = match;
    const count = Math.abs(parseInt(end, 10) - parseInt(start, 10)) + 1;
    return `${prefix}-${start}  through  ${prefix}-${end}  (${count} signs)`;
  }
  return token;
}

function firstLabelOfToken(token) {
  const match = RANGE_RE.exec(token);
  if (match) return `${match[1]}-${match[2]}`;
  return token;
}

function incrementNumber(numStr) {
  if (!/^\d+$/.test(numStr)) return numStr;
  const width = numStr.length;
  return String(parseInt(numStr, 10) + 1).padStart(width, "0");
}

if (typeof module !== "undefined") {
  module.exports = {
    LABEL_RE, RANGE_RE, expandRange, parseLabels, groupByPrefix, safeFilename,
    naturalSortKey, compareNaturalKeys, describeToken, firstLabelOfToken, incrementNumber,
  };
}
