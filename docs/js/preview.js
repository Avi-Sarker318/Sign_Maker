/*
 * Live preview drawing - renders a to-scale preview of one sign onto a
 * <canvas> (or any CanvasRenderingContext2D-compatible context, which is
 * what makes this testable headlessly with node-canvas). Mirrors the same
 * layout math as sign-layout.js's PDF drawing, just targeting a canvas
 * instead of a PDF page.
 */

function drawPreview(ctx, canvasWidth, canvasHeight, signTypeKey, label) {
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  if (signTypeKey === "sticky") {
    drawPreviewSticky(ctx, canvasWidth, canvasHeight, label);
  } else {
    drawPreviewHanging(ctx, canvasWidth, canvasHeight, label);
  }
}

function drawPreviewSticky(ctx, width, height, label) {
  const cfg = STICKY;
  // The preview shows a single cell, using the same slice height as one
  // stacked cell (cellYOffset), with (0,0) at the slice's bottom-left.
  const sliceHeight = cfg.cellYOffset;
  const scale = width / cfg.pageSize[0];

  const toPx = (x, y) => [x * scale, (sliceHeight - y) * scale];

  // Cell border.
  const [bx, by, bw, bh] = cfg.cellBorder;
  const [bx0, by0] = toPx(bx, by + bh);
  const [bx1, by1] = toPx(bx + bw, by);
  ctx.strokeStyle = "#9aa0a8";
  ctx.lineWidth = 1;
  ctx.strokeRect(bx0, by0, bx1 - bx0, by1 - by0);

  // Rule line beside the rotated caption.
  const [rx, ry0] = toPx(cfg.ruleX, cfg.ruleY1);
  const [, ry1] = toPx(cfg.ruleX, cfg.ruleY0);
  ctx.strokeStyle = "#c2c6cc";
  ctx.beginPath();
  ctx.moveTo(rx, ry0);
  ctx.lineTo(rx, ry1);
  ctx.stroke();

  ctx.fillStyle = "#000000";

  // Small caption, top-left.
  const [sx, sy] = toPx(cfg.smallPos[0], cfg.smallPos[1]);
  ctx.font = `bold ${Math.max(16 * scale, 7)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(label, sx, sy);

  // Rotated caption running up the left edge.
  const [rcx, rcy] = toPx(cfg.rotatedOrigin[0] + 4, cfg.rotatedOrigin[1]);
  ctx.save();
  ctx.translate(rcx, rcy);
  ctx.rotate(-Math.PI / 2);
  ctx.font = `bold ${Math.max(15.552 * scale, 6)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, 0, 0);
  ctx.restore();

  // Barcode bars.
  try {
    const modules = encodeCode128B(label);
    const moduleWidth = cfg.blockWidth / modules.length;
    const startX = cfg.barCenterX - cfg.blockWidth / 2;
    const barTopY = cfg.barBottomY + cfg.barHeight;
    const [, barPxTop] = toPx(0, barTopY);
    const [, barPxBottom] = toPx(0, cfg.barBottomY);
    ctx.fillStyle = "#000000";
    for (const [start, run] of barRuns(modules)) {
      const [px] = toPx(startX + start * moduleWidth, 0);
      ctx.fillRect(px, barPxTop, moduleWidth * run * scale, barPxBottom - barPxTop);
    }
  } catch (err) {
    ctx.fillStyle = "#6b7280";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("(barcode preview unavailable)", width / 2, height / 2);
  }

  // Big centered label, sized slightly smaller than literal scale to avoid
  // canvas font metrics (like the desktop app) touching the bars above it.
  const [lx, ly] = toPx(cfg.barCenterX, cfg.largeBaselineY);
  ctx.fillStyle = "#000000";
  ctx.font = `bold ${Math.max(45 * scale, 11)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(label, lx, ly);
}

function drawPreviewHanging(ctx, width, height, label) {
  const cfg = HANGING;
  const [pageW, pageH] = cfg.pageSize;
  const scale = width / pageW;

  const toPx = (x, y) => [x * scale, (pageH - y) * scale];

  ctx.strokeStyle = "#c2c6cc";
  ctx.strokeRect(1, 1, width - 2, height - 2);

  try {
    const modules = encodeCode128B(label);
    const moduleWidth = cfg.blockWidth / modules.length;
    const startX = (pageW - cfg.blockWidth) / 2;
    const [, barPxTop] = toPx(0, cfg.barOriginY + cfg.barHeight);
    const [, barPxBottom] = toPx(0, cfg.barOriginY);
    ctx.fillStyle = "#000000";
    for (const [start, run] of barRuns(modules)) {
      const [px] = toPx(startX + start * moduleWidth, 0);
      ctx.fillRect(px, barPxTop, moduleWidth * run * scale, barPxBottom - barPxTop);
    }
  } catch (err) {
    ctx.fillStyle = "#6b7280";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("(barcode preview unavailable)", width / 2, height / 2);
  }

  const [sx, sy] = toPx(cfg.smallPos[0], cfg.smallPos[1]);
  ctx.fillStyle = "#000000";
  ctx.font = `bold ${Math.max(16 * scale, 7)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(label, sx, sy);

  const [lx, ly] = toPx(pageW / 2, cfg.largeBaselineY);
  ctx.font = `bold ${Math.max(85 * scale, 14)}px Helvetica, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(label, lx, ly);
}
