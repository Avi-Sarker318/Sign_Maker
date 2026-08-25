"""
Sticky Signs layout and drawing.

This is the "two signs per portrait sheet, stacked" layout. Shared
parsing/grouping/sorting logic lives in signs_common.py; this module only
knows how to lay one Sticky Sign out on a page.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from signs_common import (  # noqa: F401  (re-exported for callers)
    LABEL_RE,
    RANGE_RE,
    expand_range,
    parse_labels,
    group_by_prefix,
    safe_filename,
    natural_sort_key,
    barcode_modules,
    next_available_dir,
)
from signs_common import generate_signs as _common_generate_signs

# ---------------------------------------------------------------------------
# Layout, measured from the existing Sticky Signs PDFs. All units are points
# (72 per inch). Change these to retune the sheet; nothing else depends on
# the literal numbers.
#
# Every measurement below belongs to the BOTTOM cell. The top cell is the
# same layout shifted up by CELL_Y_OFFSET, which is how the originals are
# built.
# ---------------------------------------------------------------------------
PAGE_SIZE = letter                     # 612 x 792 pt, portrait

CELLS_PER_PAGE = 2
CELL_Y_OFFSET = 393.12                 # bottom cell -> top cell

CELL_BORDER = (5.76, 5.76, 600.48, 387.36)
CELL_BORDER_GRAY = 0.55
CELL_BORDER_WIDTH = 0.5

RULE_X = 38.16
RULE_Y0 = 16.56
RULE_Y1 = 382.32
RULE_GRAY = 0.7
RULE_WIDTH = 0.4

MODULE_WIDTH = 4.388571                # nominal narrow-bar width (single-digit stock)
BLOCK_WIDTH = 90 * MODULE_WIDTH        # 394.97 pt

BAR_HEIGHT = 226.7712
BAR_BOTTOM_Y = 61.32
BAR_CENTER_X = 318.96

SMALL_FONT = ("Helvetica-Bold", 16)
SMALL_POS = (42.48, 366.32)

ROTATED_FONT = ("Helvetica-Bold", 15.552)
ROTATED_ORIGIN = (21.96, 199.44)
ROTATED_OFFSET = (-19.88323, -5.4432)

LARGE_FONT = ("Helvetica-Bold", 52)
LARGE_BASELINE_Y = 16.56

RUN_FOLDER_NAME = "Sticky Signs PDFS"
SIGN_TYPE_LABEL = "Sticky Signs"


def draw_cell(pdf, label, y_offset):
    """
    Render one sign into a cell.

    y_offset is 0 for the bottom cell and CELL_Y_OFFSET for the top one;
    every coordinate below is measured from the bottom cell.
    """
    pdf.setStrokeGray(CELL_BORDER_GRAY)
    pdf.setLineWidth(CELL_BORDER_WIDTH)
    bx, by, bw, bh = CELL_BORDER
    pdf.rect(bx, by + y_offset, bw, bh, stroke=1, fill=0)

    pdf.setStrokeGray(RULE_GRAY)
    pdf.setLineWidth(RULE_WIDTH)
    pdf.line(RULE_X, RULE_Y0 + y_offset, RULE_X, RULE_Y1 + y_offset)

    pdf.setFillGray(0)

    pdf.saveState()
    pdf.translate(ROTATED_ORIGIN[0], ROTATED_ORIGIN[1] + y_offset)
    pdf.rotate(90)
    pdf.setFont(*ROTATED_FONT)
    pdf.drawString(ROTATED_OFFSET[0], ROTATED_OFFSET[1], label)
    pdf.restoreState()

    modules = barcode_modules(label)
    module_width = BLOCK_WIDTH / len(modules)
    x = BAR_CENTER_X - BLOCK_WIDTH / 2.0

    index = 0
    while index < len(modules):
        if modules[index] == "1":
            run = 1
            while index + run < len(modules) and modules[index + run] == "1":
                run += 1
            pdf.rect(x, BAR_BOTTOM_Y + y_offset, module_width * run,
                     BAR_HEIGHT, stroke=0, fill=1)
            x += module_width * run
            index += run
        else:
            x += module_width
            index += 1

    pdf.setFont(*SMALL_FONT)
    pdf.drawString(SMALL_POS[0], SMALL_POS[1] + y_offset, label)

    pdf.setFont(*LARGE_FONT)
    pdf.drawCentredString(BAR_CENTER_X, LARGE_BASELINE_Y + y_offset, label)


def build_pdf(prefix, labels, out_dir):
    """
    Write one PDF for this group, two signs per sheet.

    The top cell is filled first so a page with a single label matches the
    originals, which start at the top of the sheet.
    """
    out_path = out_dir / f"{safe_filename(prefix)}.pdf"

    pdf = canvas.Canvas(str(out_path), pagesize=PAGE_SIZE)
    pdf.setTitle(f"Sticky Signs {prefix}")

    for index, label in enumerate(labels):
        slot = index % CELLS_PER_PAGE
        y_offset = CELL_Y_OFFSET if slot == 0 else 0.0
        draw_cell(pdf, label, y_offset)

        is_last = index == len(labels) - 1
        if slot == CELLS_PER_PAGE - 1 or is_last:
            pdf.showPage()

    pdf.save()
    return out_path


def generate_signs(tokens, output_dir: Path, run_name: str = None, log=print,
                    make_subfolder: bool = True, overwrite: bool = False):
    """Same behavior as before; see signs_common.generate_signs for details."""
    return _common_generate_signs(
        tokens, output_dir, build_pdf, RUN_FOLDER_NAME,
        run_name=run_name, log=log, make_subfolder=make_subfolder, overwrite=overwrite,
    )
