"""
Shared logic for all sign types (Sticky Signs, Hanging Signs, and any future
ones). Parsing labels, grouping by prefix, natural sort order, and the
generic "write these groups to PDFs" flow all live here so each sign type's
own core module only has to define its page layout and drawing code.
"""

import re
from collections import OrderedDict
from pathlib import Path

import barcode

# A label like "a-001" or "V1-017": prefix, dash, slot.
LABEL_RE = re.compile(r"^\s*(.+?)\s*-\s*(\S+)\s*$")

# A range like "a-001:003".
RANGE_RE = re.compile(r"^\s*(.+?)\s*-\s*(\d+)\s*[:]\s*(\d+)\s*$")


def expand_range(token):
    """
    Expand "a-001:003" into ["a-001", "a-002", "a-003"].

    Zero padding follows the start value, so 001:003 yields 3-digit slots.
    Returns None if the token is not a range.
    """
    match = RANGE_RE.match(token)
    if not match:
        return None
    prefix, start_raw, end_raw = match.groups()
    start, end = int(start_raw), int(end_raw)
    if end < start:
        start, end = end, start
    width = len(start_raw)
    return [f"{prefix}-{n:0{width}d}" for n in range(start, end + 1)]


def parse_labels(tokens):
    """Flatten raw tokens into labels, expanding ranges along the way."""
    labels = []
    for token in tokens:
        for piece in re.split(r"[,\s]+", token):
            piece = piece.strip()
            if not piece:
                continue
            expanded = expand_range(piece)
            if expanded:
                labels.extend(expanded)
            else:
                labels.append(piece)
    return labels


def group_by_prefix(labels):
    """
    Group labels by the text before the first "-", preserving input order
    both between groups and within each group.

    A label with no "-" forms its own group under the whole word.
    Duplicates inside a group are dropped so a label is never printed twice.
    """
    groups = OrderedDict()
    skipped = []
    for label in labels:
        match = LABEL_RE.match(label)
        if match:
            prefix = match.group(1)
        else:
            prefix = label.strip()
            if not prefix:
                skipped.append(label)
                continue
        bucket = groups.setdefault(prefix, [])
        if label not in bucket:
            bucket.append(label)
    return groups, skipped


def safe_filename(text):
    """Make a prefix usable as a filename without changing its meaning."""
    stem = re.sub(r'[<>:"/\\|?*]', "_", text).strip().rstrip(".")
    return stem or "unnamed"


def natural_sort_key(label):
    """
    Sort key that puts a-002 before a-010 (unlike plain text sorting, which
    would put "10" before "2"). Falls back to plain text order for labels
    whose slot isn't a number, and for labels with no dash at all.

    This is what lets you add more of a batch later, even out of order, and
    still get one PDF with everything in the right order.
    """
    match = LABEL_RE.match(label)
    if match and match.group(2).isdigit():
        return (0, int(match.group(2)), label)
    return (1, 0, label)


def barcode_modules(text):
    """
    Code 128 bar pattern as a string of "1" (bar) and "0" (space).

    python-barcode adds its own leading quiet zone, which is stripped here
    and re-added as page/cell margin by each sign type's layout so the
    geometry matches the original sheets exactly.
    """
    code = barcode.get_barcode_class("code128")(text)
    return code.build()[0]


def next_available_dir(base_dir: Path, run_name: str) -> Path:
    """Return base_dir/run_name, or run_name_2, _3, ... if it already exists."""
    out_dir = base_dir / run_name
    if not out_dir.exists():
        return out_dir
    counter = 2
    while (base_dir / f"{run_name}_{counter}").exists():
        counter += 1
    return base_dir / f"{run_name}_{counter}"


def generate_signs(tokens, output_dir: Path, build_pdf_fn, default_run_name: str,
                    run_name: str = None, log=print, make_subfolder: bool = True,
                    overwrite: bool = False):
    """
    The generic "turn a list of labels into PDFs" flow, shared by every sign
    type. Each sign type's own generate_signs() wrapper calls this with its
    own build_pdf_fn (which knows that type's page layout) and default folder
    name, so the parsing/grouping/sorting/folder logic only exists once.

    tokens: list of raw strings (labels/ranges), exactly what a user would type
    output_dir: base folder to create the run folder inside
    build_pdf_fn: callable(prefix, labels, out_dir) -> Path, writes one PDF
    default_run_name: subfolder name to use when run_name isn't given
    run_name: name for the run's own subfolder
    log: callable used to report progress, e.g. print() or a GUI text box append
    make_subfolder: if False, PDFs are written directly into output_dir with
                     no dated/numbered subfolder
    overwrite: if True, always write into output_dir/run_name and replace
               whatever PDFs are already there (lets adding more labels later
               update the same PDF instead of creating a separate "_2" folder).
               If False, a fresh "_2", "_3", ... folder is used each time.

    Each group's labels are sorted numerically (2-002 before 2-010) before
    being handed to build_pdf_fn, regardless of the order they were added in.

    Returns (out_dir, groups_written, total_labels, skipped).
    """
    labels = parse_labels(tokens)
    groups, skipped = group_by_prefix(labels)

    for bad in skipped:
        log(f"  ! skipped {bad!r}: empty label")

    if not groups:
        log("No usable labels found.")
        return output_dir, 0, 0, skipped

    for prefix in groups:
        groups[prefix] = sorted(groups[prefix], key=natural_sort_key)

    if not make_subfolder:
        out_dir = output_dir
    elif overwrite:
        out_dir = output_dir / (run_name or default_run_name)
    else:
        out_dir = next_available_dir(output_dir, run_name or default_run_name)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for prefix, group_labels in groups.items():
        out_path = build_pdf_fn(prefix, group_labels, out_dir)
        total += len(group_labels)
        log(f"  {out_path.name:<20} {len(group_labels):>4} label(s)   "
            f"{group_labels[0]} -> {group_labels[-1]}")

    log("")
    log(f"Wrote {len(groups)} PDF(s), {total} labels -> {out_dir.resolve()}")
    return out_dir, len(groups), total, skipped
