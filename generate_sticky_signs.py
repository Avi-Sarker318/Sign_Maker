#!/usr/bin/env python3
"""
Sticky Signs barcode generator (command line).

Reads a list of labels, groups them by the prefix before the "-", and writes
one portrait PDF per prefix into ./output/Sticky Signs PDFS.

Two signs fit on each sheet, stacked, so a group of five labels produces a
three page PDF with the last cell left blank.

    a-001, a-002, a-003, c-001, c-004   ->   a.pdf  (3 labels, 2 pages)
                                             c.pdf  (2 labels, 1 page)

A label with no "-" becomes its own PDF named for the whole word:

    DOCK   ->   DOCK.pdf

Labels can be supplied four ways:

    python generate_sticky_signs.py                    # LABELS list below
    python generate_sticky_signs.py a-001 a-002        # on the command line
    python generate_sticky_signs.py --file labels.txt  # one per line
                                                       # or prompts if empty

Ranges are supported everywhere: "a-001:003" expands to a-001, a-002, a-003
and keeps the zero padding of the start value.

Signs are always sorted by number within each PDF (a-002 before a-010), no
matter what order you list them in - so you can add more later, even out of
order, and they'll still print correctly. Add --update to write into the
same run folder each time (replacing the old PDFs) instead of making a new
_2/_3 folder, which is what you want when you're building up one set of
signs over multiple sessions rather than making separate batches.

Prefer clicking a button instead of typing commands? Use sticky_signs_gui.py
(or the SickySigns.exe built from it) instead - same logic, a window.

Requires: pip install reportlab python-barcode
"""

import argparse
import sys
from pathlib import Path

from sticky_signs_core import generate_signs

# ---------------------------------------------------------------------------
# FILL THIS IN. One label per line, in quotes, comma after each.
# Ranges work too: "a-001:003" becomes a-001, a-002, a-003.
#
# Everything before the "-" decides which PDF the label lands in, so
# a-001 and a-002 share a.pdf while c-001 starts its own c.pdf.
#
# Example:
#     LABELS = [
#         "a-001",
#         "a-002",
#         "c-001:004",
#         "v-995",
#     ]
# ---------------------------------------------------------------------------
LABELS = [
    
]

OUTPUT_DIR = Path("output")

# Folder the PDFs land in. A second run adds "_2", "_3" and so on rather
# than overwriting what is already there.
RUN_FOLDER_NAME = "Sticky Signs PDFS"


def prompt_for_labels():
    """Interactive entry: accept lines until a blank one."""
    print("Enter labels (e.g. a-001 a-002 c-001, or a range a-001:003).")
    print("Separate with spaces or commas. Blank line when finished.\n")

    tokens = []
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        tokens.append(line)
    return tokens


def main():
    parser = argparse.ArgumentParser(
        description="Generate Sticky Signs barcode PDFs, one per label prefix."
    )
    parser.add_argument("labels", nargs="*",
                        help="Labels or ranges, e.g. a-001 a-002 c-001:004")
    parser.add_argument("--file", help="Read labels from a text file, one per line")
    parser.add_argument("--output-dir", default=None,
                        help="Write PDFs here instead of the run folder")
    parser.add_argument("--name",
                        help="Name the run folder instead of using the default")
    parser.add_argument("--update", action="store_true",
                        help=("Write into the same run folder every time, replacing the "
                              "old PDFs, instead of making a new _2/_3 folder. Use this "
                              "when you're adding more labels to a set you already made."))
    args = parser.parse_args()

    tokens = list(args.labels)

    if not tokens and not args.file:
        tokens = [t for t in LABELS if str(t).strip()]

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            print(f"Label file not found: {file_path.resolve()}", file=sys.stderr)
            return 1
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                tokens.append(line)

    if not tokens:
        if args.file or args.labels:
            # Labels were explicitly requested from a file or the command
            # line, so an empty result means "nothing to do", not "ask the
            # person to type some in". This matters most when this script
            # runs unattended (e.g. in a GitHub Action) - input() would hang
            # forever with no terminal attached to answer it.
            print("No usable labels found - nothing to do.")
            return 1
        print("The LABELS list at the top of this script is empty.\n")
        tokens = prompt_for_labels()

    if not tokens:
        print("No labels given, nothing to do.")
        return 1

    if args.output_dir:
        out_dir, groups, total, skipped = generate_signs(
            tokens, Path(args.output_dir), log=print, make_subfolder=False
        )
    else:
        run_name = args.name if args.name else RUN_FOLDER_NAME
        out_dir, groups, total, skipped = generate_signs(
            tokens, OUTPUT_DIR, run_name=run_name, log=print, overwrite=args.update
        )

    return 0 if groups else 1


if __name__ == "__main__":
    sys.exit(main())
