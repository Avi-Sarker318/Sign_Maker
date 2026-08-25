#!/usr/bin/env python3
"""
Adds labels to (or replaces) signs/labels.txt - the master list of sign
labels tracked in this repo. Used by the "Update sign labels" GitHub Action;
you don't normally need to run this yourself.

    python scripts/update_labels.py --file signs/labels.txt --add "2-031:035, 2-040:047"
    python scripts/update_labels.py --file signs/labels.txt --add "a-001:010" --start-new
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sticky_signs_core import LABEL_RE, RANGE_RE  # noqa: E402

HEADER = (
    "# Sticky Signs master label list.\n"
    "# One label or range per line (ranges like a-001:010 are fine). Lines\n"
    "# starting with # are ignored.\n"
    "#\n"
    "# You can edit this file directly right here on GitHub (click the pencil\n"
    "# icon, add or change a line, commit) or use the \"Update sign labels\"\n"
    "# Action instead. Either way, the \"Build & publish signs\" Action notices\n"
    "# the change and rebuilds the PDFs automatically - see the Releases page\n"
    "# for the result.\n"
)


def natural_key(token):
    """Sorts this file in a sensible order for humans browsing it on GitHub -
    the PDFs themselves are always re-sorted at build time regardless."""
    match = RANGE_RE.match(token) or LABEL_RE.match(token)
    if match:
        prefix, slot = match.group(1), match.group(2)
        if slot.isdigit():
            return (prefix.lower(), 0, int(slot))
        return (prefix.lower(), 1, slot)
    return (token.lower(), 2, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Path to the labels list file")
    parser.add_argument("--add", default="", help="New labels/ranges, comma or space separated")
    parser.add_argument("--start-new", action="store_true",
                         help="Replace the whole list instead of adding to it")
    args = parser.parse_args()

    path = Path(args.file)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if path.is_file() and not args.start_new:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                existing.append(line)

    new_pieces = [p for p in re.split(r"[,\s]+", args.add) if p.strip()]

    combined = list(existing)
    actually_added = []
    for piece in new_pieces:
        if piece not in combined:
            combined.append(piece)
            actually_added.append(piece)
    combined.sort(key=natural_key)

    body = "\n".join(combined) + ("\n" if combined else "")
    path.write_text(HEADER + "\n" + body, encoding="utf-8")

    action = "Replaced" if args.start_new else "Updated"
    plural = "entry" if len(combined) == 1 else "entries"
    print(f"{action} {path} - now has {len(combined)} {plural}.")
    if actually_added:
        print("Added:", ", ".join(actually_added))
    skipped_duplicates = [p for p in new_pieces if p not in actually_added]
    if skipped_duplicates:
        print("Already in the list (skipped):", ", ".join(skipped_duplicates))
    if not new_pieces:
        print("Nothing new was added.")


if __name__ == "__main__":
    main()
