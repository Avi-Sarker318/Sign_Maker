"""
Hanging Signs layout and drawing.

This is the "one full landscape sheet per label" layout - big overhead signs
meant to hang, as opposed to Sticky Signs' two-per-page stacked layout.
Shared parsing/grouping/sorting logic lives in signs_common.py; this module
only knows how to lay one Hanging Sign out on a page.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter, landscape
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
# Layout, measured from the existing Hanging Signs PDFs. All units are points
# (72 per inch). Change these to retune the sheet; nothing else depends on
# the literal numbers.
# ---------------------------------------------------------------------------
PAGE_SIZE = landscape(letter)          # 792 x 612 pt

MODULE_WIDTH = 8.1                     # nominal narrow-bar width (single-digit stock)

# Fixed target width for the barcode block. 90 modules * 8.1pt = 729pt is the
# width of the existing single-digit sheets, so every label is scaled to
# match it. Labels with more bars (10-, 11-, 12-) get proportionally thinner
# bars instead of a wider block, keeping the printed size identical.
BLOCK_WIDTH = 90 * MODULE_WIDTH        # 729.0 pt

BAR_HEIGHT = 479.36                    # bar height
BAR_ORIGIN_Y = 118.24                  # bottom edge of the bars

SMALL_FONT = ("Helvetica-Bold", 16)    # caption under the bars
SMALL_POS = (7.2, 95.04)

LARGE_FONT = ("Helvetica-Bold", 100)   # big human-readable label
LARGE_BASELINE_Y = 14.4                # centered horizontally at render time

RUN_FOLDER_NAME = "Hanging Signs PDFS"
SIGN_TYPE_LABEL = "Hanging Signs"


def draw_page(pdf, label):
    """Render one full sheet: bars, small caption, large label."""
    page_width, _ = PAGE_SIZE

    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(0, 0, *PAGE_SIZE, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)

    # Bars are drawn as filled vector rectangles, not an embedded image, so
    # they stay sharp at any print size and scan cleanly.
    #
    # The block is centered on the page and always occupies BLOCK_WIDTH. The
    # per-page module width is derived from that fixed total, so a label with
    # more bars (10-001) gets thinner bars rather than a wider barcode. This
    # is what keeps every sheet the same printed size.
    modules = barcode_modules(label)
    module_width = BLOCK_WIDTH / len(modules)
    x = (page_width - BLOCK_WIDTH) / 2.0

    index = 0
    while index < len(modules):
        if modules[index] == "1":
            run = 1
            while index + run < len(modules) and modules[index + run] == "1":
                run += 1
            pdf.rect(x, BAR_ORIGIN_Y, module_width * run, BAR_HEIGHT,
                     stroke=0, fill=1)
            x += module_width * run
            index += run
        else:
            x += module_width
            index += 1

    pdf.setFont(*SMALL_FONT)
    pdf.drawString(SMALL_POS[0], SMALL_POS[1], label)

    pdf.setFont(*LARGE_FONT)
    pdf.drawCentredString(page_width / 2.0, LARGE_BASELINE_Y, label)

    pdf.showPage()


def build_pdf(prefix, labels, out_dir):
    """Write one PDF containing a page for each label in this group."""
    out_path = out_dir / f"{safe_filename(prefix)}.pdf"

    pdf = canvas.Canvas(str(out_path), pagesize=PAGE_SIZE)
    pdf.setTitle(f"Hanging Signs {prefix}")

    for label in labels:
        draw_page(pdf, label)

    pdf.save()
    return out_path


def generate_signs(tokens, output_dir: Path, run_name: str = None, log=print,
                    make_subfolder: bool = True, overwrite: bool = False):
    """Same behavior as sticky_signs_core.generate_signs; see signs_common."""
    return _common_generate_signs(
        tokens, output_dir, build_pdf, RUN_FOLDER_NAME,
        run_name=run_name, log=log, make_subfolder=make_subfolder, overwrite=overwrite,
    )
