/*
 * Sign layout - a JS port of sticky_signs_core.py / hanging_signs_core.py,
 * using jsPDF instead of reportlab. All the measurements below are copied
 * directly from those two files so the printed output matches exactly.
 */

const STICKY = {
  key: "sticky",
  label: "Sticky Signs",
  icon: "\u{1F3F7}\uFE0F",
  tagline: "Two signs per sheet, stacked - small barcode labels.",
  pageSize: [612, 792], // portrait letter, points
  cellsPerPage: 2,
  cellYOffset: 393.12,
  cellBorder: [5.76, 5.76, 600.48, 387.36], // x, y, width, height
  ruleX: 38.16, ruleY0: 16.56, ruleY1: 382.32,
  moduleWidth: 4.388571,
  get blockWidth() { return 90 * this.moduleWidth; },
  barHeight: 226.7712,
  barBottomY: 61.32,
  barCenterX: 318.96,
  smallFontSize: 16, smallPos: [42.48, 366.32],
  rotatedFontSize: 15.552, rotatedOrigin: [21.96, 199.44],
  largeFontSize: 52, largeBaselineY: 16.56,
  runFolderName: "Sticky Signs PDFS",
};

const HANGING = {
  key: "hanging",
  label: "Hanging Signs",
  icon: "\u{1FA84}",
  tagline: "One full landscape sheet per label - big overhead signs.",
  pageSize: [792, 612], // landscape letter, points
  moduleWidth: 8.1,
  get blockWidth() { return 90 * this.moduleWidth; },
  barHeight: 479.36,
  barOriginY: 118.24,
  smallFontSize: 16, smallPos: [7.2, 95.04],
  largeFontSize: 100, largeBaselineY: 14.4,
  runFolderName: "Hanging Signs PDFS",
};

const SIGN_TYPES = { sticky: STICKY, hanging: HANGING };

/** Splits a Code128 module string into (start, run-length) pairs for '1' runs. */
function barRuns(modules) {
  const runs = [];
  let i = 0;
  while (i < modules.length) {
    if (modules[i] === "1") {
      let run = 1;
      while (i + run < modules.length && modules[i + run] === "1") run++;
      runs.push([i, run]);
      i += run;
    } else {
      i += 1;
    }
  }
  return runs;
}

/** Draws one Sticky Sign cell. yOffset is 0 for bottom cell, cellYOffset for top. */
function drawStickyCell(doc, label, yOffset) {
  const cfg = STICKY;
  const [bx, by, bw, bh] = cfg.cellBorder;

  doc.setDrawColor(140); // ~0.55 gray
  doc.setLineWidth(0.5);
  doc.rect(bx, cfg.pageSize[1] - (by + yOffset + bh), bw, bh);

  doc.setDrawColor(178); // ~0.7 gray
  doc.setLineWidth(0.4);
  doc.line(
    cfg.ruleX, cfg.pageSize[1] - (cfg.ruleY1 + yOffset),
    cfg.ruleX, cfg.pageSize[1] - (cfg.ruleY0 + yOffset),
  );

  doc.setTextColor(0);
  doc.setFont("helvetica", "bold");

  // Rotated caption running up the left edge.
  doc.setFontSize(cfg.rotatedFontSize);
  const [rx, ry] = cfg.rotatedOrigin;
  doc.text(label, rx, cfg.pageSize[1] - (ry + yOffset), { angle: 90 });

  // Barcode bars - fixed total block width regardless of digit count.
  const modules = encodeCode128B(label);
  const moduleWidth = cfg.blockWidth / modules.length;
  doc.setFillColor(0);
  const startX = cfg.barCenterX - cfg.blockWidth / 2;
  const yPt = cfg.pageSize[1] - (cfg.barBottomY + yOffset + cfg.barHeight);
  for (const [start, run] of barRuns(modules)) {
    doc.rect(startX + start * moduleWidth, yPt, moduleWidth * run, cfg.barHeight, "F");
  }

  // Small caption, top-left.
  doc.setFontSize(cfg.smallFontSize);
  doc.text(label, cfg.smallPos[0], cfg.pageSize[1] - (cfg.smallPos[1] + yOffset));

  // Big centered label.
  doc.setFontSize(cfg.largeFontSize);
  doc.text(label, cfg.barCenterX, cfg.pageSize[1] - (cfg.largeBaselineY + yOffset), { align: "center" });
}

/** Draws one full Hanging Sign page. */
function drawHangingPage(doc, label) {
  const cfg = HANGING;
  const [pageW, pageH] = cfg.pageSize;

  doc.setFillColor(255);
  doc.rect(0, 0, pageW, pageH, "F");
  doc.setFillColor(0);

  const modules = encodeCode128B(label);
  const moduleWidth = cfg.blockWidth / modules.length;
  const startX = (pageW - cfg.blockWidth) / 2;
  const yPt = pageH - (cfg.barOriginY + cfg.barHeight);
  for (const [start, run] of barRuns(modules)) {
    doc.rect(startX + start * moduleWidth, yPt, moduleWidth * run, cfg.barHeight, "F");
  }

  doc.setTextColor(0);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(cfg.smallFontSize);
  doc.text(label, cfg.smallPos[0], pageH - cfg.smallPos[1]);

  doc.setFontSize(cfg.largeFontSize);
  doc.text(label, pageW / 2, pageH - cfg.largeBaselineY, { align: "center" });
}

/**
 * Builds one PDF (a jsPDF doc) for a single prefix group.
 * signTypeKey: "sticky" or "hanging". labels: already-sorted array.
 */
function buildGroupPdf(signTypeKey, labels) {
  const { jsPDF } = window.jspdf;
  const cfg = SIGN_TYPES[signTypeKey];

  if (signTypeKey === "sticky") {
    const doc = new jsPDF({ orientation: "portrait", unit: "pt", format: cfg.pageSize });
    labels.forEach((label, index) => {
      const slot = index % cfg.cellsPerPage;
      const yOffset = slot === 0 ? cfg.cellYOffset : 0;
      if (index > 0 && slot === 0) doc.addPage();
      drawStickyCell(doc, label, yOffset);
    });
    return doc;
  }

  const doc = new jsPDF({ orientation: "landscape", unit: "pt", format: [cfg.pageSize[1], cfg.pageSize[0]] });
  labels.forEach((label, index) => {
    if (index > 0) doc.addPage();
    drawHangingPage(doc, label);
  });
  return doc;
}
