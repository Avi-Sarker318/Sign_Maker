#!/usr/bin/env python3
"""
Sign Maker - friendly Windows window for both Sticky Signs and Hanging Signs.

Ask which kind of sign you want, add labels, see a live to-scale preview of
that exact sign type, and generate PDFs. Each sign type keeps its own
remembered list and prefix history, since they're usually different sets of
labels. Same barcode/PDF logic as generate_sticky_signs.py /
generate_hanging_signs.py underneath - this is just the window.
"""

import json
import queue
import re
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import hanging_signs_core
import sticky_signs_core
from signs_common import RANGE_RE, barcode_modules, group_by_prefix, parse_labels

# When bundled by PyInstaller, write output next to the .exe rather than into
# a temp folder, so users can actually find the PDFs.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

DEFAULT_OUTPUT_DIR = APP_DIR / "output"
SETTINGS_FILE = APP_DIR / "sign_maker_settings.json"

# ---------------------------------------------------------------- palette
PAGE_BG = "#eef1f6"
HEADER_BG = "#1e3a5f"
HEADER_TEXT = "#ffffff"
HEADER_SUBTEXT = "#c7d4e3"
CARD_BG = "#ffffff"
CARD_BORDER = "#e1e5eb"
BADGE_BG = "#2563eb"
TEXT_DARK = "#1f2937"
TEXT_MUTED = "#6b7280"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4fd1"
SUCCESS = "#15803d"
SUCCESS_HOVER = "#116c32"
WARNING = "#b45309"
FIELD_BORDER = "#cbd2db"
TYPE_UNSELECTED_BG = "#f0f2f5"

_WORKER_DONE = object()

# ----------------------------------------------------------- sign types
# Each sign type gets its own remembered label list and prefix history,
# since Sticky Signs and Hanging Signs are usually completely different
# batches of labels. Switching types swaps which list/history is active;
# nothing is lost either way.
SIGN_TYPES = {
    "sticky": {
        "key": "sticky",
        "label": "Sticky Signs",
        "icon": "\U0001f3f7\ufe0f",
        "tagline": "Two signs per sheet, stacked - small barcode labels.",
        "module": sticky_signs_core,
        "labels_file": APP_DIR / "sticky_signs_current_labels.json",
        "history_file": APP_DIR / "sticky_signs_history.json",
    },
    "hanging": {
        "key": "hanging",
        "label": "Hanging Signs",
        "icon": "\U0001fa84",
        "tagline": "One full landscape sheet per label - big overhead signs.",
        "module": hanging_signs_core,
        "labels_file": APP_DIR / "hanging_signs_current_labels.json",
        "history_file": APP_DIR / "hanging_signs_history.json",
    },
}
DEFAULT_SIGN_TYPE = "sticky"


class RoundedCard(tk.Frame):
    """A white, rounded-corner card whose height auto-fits its content and
    whose width tracks its parent. Put your widgets inside `.inner`."""

    def __init__(self, parent, radius=16, bg=CARD_BG, border=CARD_BORDER, **kwargs):
        super().__init__(parent, background=PAGE_BG, **kwargs)
        self.radius = radius
        self.bg = bg
        self.border = border

        self.canvas = tk.Canvas(self, background=PAGE_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, background=bg)
        self._window = self.canvas.create_window((3, 3), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        inner_width = max(event.width - 6, 1)
        self.canvas.itemconfigure(self._window, width=inner_width)
        self._redraw(event.width, self.canvas.winfo_height())

    def _on_inner_configure(self, _event=None):
        height = self.inner.winfo_reqheight() + 6
        width = self.canvas.winfo_width() or self.inner.winfo_reqwidth() + 6
        self.canvas.configure(height=height)
        self._redraw(width, height)

    def _redraw(self, width, height):
        if width < 4 or height < 4:
            return
        self.canvas.delete("card_shape")
        self._round_rect(1, 1, width - 2, height - 2, self.radius,
                          fill=self.bg, outline=self.border, width=1, tags="card_shape")
        self.canvas.tag_lower("card_shape")

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)


def make_step_header(parent, number, title, description):
    """A circular numbered badge + bold title + muted description row."""
    row = tk.Frame(parent, background=CARD_BG)
    row.pack(fill="x", pady=(0, 4))

    badge = tk.Canvas(row, width=34, height=34, background=CARD_BG, highlightthickness=0)
    badge.pack(side="left", padx=(0, 12), pady=2)
    badge.create_oval(1, 1, 33, 33, fill=BADGE_BG, outline="")
    badge.create_text(17, 17, text=str(number), fill="white", font=("Segoe UI", 13, "bold"))

    text_col = tk.Frame(row, background=CARD_BG)
    text_col.pack(side="left", fill="x", expand=True)
    tk.Label(text_col, text=title, font=("Segoe UI", 14, "bold"),
              background=CARD_BG, fg=TEXT_DARK, anchor="w").pack(anchor="w")
    if description:
        tk.Label(text_col, text=description, font=("Segoe UI", 10),
                  background=CARD_BG, fg=TEXT_MUTED, anchor="w", wraplength=620,
                  justify="left").pack(anchor="w")
    return row


def styled_button(parent, text, command, bg, hover_bg, fg="white",
                   font=("Segoe UI", 11, "bold"), padx=16, pady=8):
    """A flat tk.Button with a hover color change."""
    btn = tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg, font=font,
        relief="flat", bd=0, padx=padx, pady=pady, cursor="hand2",
        highlightthickness=0,
    )
    btn.bind("<Enter>", lambda _e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
    return btn


class SignMakerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Sign Maker")
        self.geometry("860x960")
        self.minsize(740, 700)
        self.configure(background=PAGE_BG)
        self.option_add("*Font", ("Segoe UI", 11))

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Card.TEntry", fieldbackground="white", padding=6,
                         bordercolor=FIELD_BORDER, lightcolor=FIELD_BORDER,
                         darkcolor=FIELD_BORDER)
        style.configure("TCombobox", padding=6)
        style.configure("TScrollbar", background=PAGE_BG)

        self.sign_type = self._load_last_sign_type()
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self._log_queue = queue.Queue()
        self._worker_running = False

        self.known_prefixes = self._load_history()
        self.labels = self._load_labels()  # list of {"raw": str, "display": str}

        self.quick_prefix = tk.StringVar()
        self.quick_start = tk.StringVar()
        self.quick_end = tk.StringVar()
        self.status_var = tk.StringVar(value="")
        self.count_var = tk.StringVar(value="No sign labels added yet.")
        self.preview_caption_var = tk.StringVar(value="")
        self.details_visible = False

        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_job_id = None
        self._poll_log_queue()

    # ---------------------------------------------------------- sign type
    def _config(self):
        return SIGN_TYPES[self.sign_type]

    def _module(self):
        return self._config()["module"]

    def _load_last_sign_type(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            key = data.get("last_sign_type")
            if key in SIGN_TYPES:
                return key
        except Exception:  # noqa: BLE001
            pass
        return DEFAULT_SIGN_TYPE

    def _save_last_sign_type(self):
        try:
            SETTINGS_FILE.write_text(
                json.dumps({"last_sign_type": self.sign_type}, indent=2), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001
            pass

    def _switch_sign_type(self, new_key):
        if new_key == self.sign_type or new_key not in SIGN_TYPES:
            return
        self._save_labels()
        self.sign_type = new_key
        self._save_last_sign_type()

        self.known_prefixes = self._load_history()
        self.labels = self._load_labels()
        self.quick_prefix.set("")
        self.quick_start.set("")
        self.quick_end.set("")
        self.status_var.set("")

        self.prefix_combo.configure(values=self.known_prefixes)
        self._resize_preview_canvas()
        self._refresh_type_buttons()
        self._refresh_listbox()

    # ------------------------------------------------------------- history
    def _load_history(self):
        try:
            data = json.loads(self._config()["history_file"].read_text(encoding="utf-8"))
            prefixes = data.get("prefixes", [])
            return sorted({str(p) for p in prefixes}, key=str.lower)
        except Exception:  # noqa: BLE001
            return []

    def _save_history(self):
        try:
            self._config()["history_file"].write_text(
                json.dumps({"prefixes": self.known_prefixes}, indent=2), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001
            pass

    def _remember_prefix(self, prefix):
        if prefix and prefix not in self.known_prefixes:
            self.known_prefixes.append(prefix)
            self.known_prefixes.sort(key=str.lower)
            self._save_history()
            if hasattr(self, "prefix_combo"):
                self.prefix_combo.configure(values=self.known_prefixes)

    # -------------------------------------------------------------- labels
    def _load_labels(self):
        try:
            data = json.loads(self._config()["labels_file"].read_text(encoding="utf-8"))
            raw_tokens = data.get("labels", [])
            return [{"raw": t, "display": self._describe_token(t)} for t in raw_tokens
                    if isinstance(t, str) and t.strip()]
        except Exception:  # noqa: BLE001
            return []

    def _save_labels(self):
        try:
            self._config()["labels_file"].write_text(
                json.dumps({"labels": [item["raw"] for item in self.labels]}, indent=2),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ UI
    def _build_widgets(self):
        header = tk.Frame(self, background=HEADER_BG)
        header.pack(fill="x", side="top")
        header_inner = tk.Frame(header, background=HEADER_BG)
        header_inner.pack(fill="x", padx=24, pady=18)
        tk.Label(
            header_inner, text="\U0001f4cb  Sign Maker",
            font=("Segoe UI", 20, "bold"), background=HEADER_BG, fg=HEADER_TEXT,
        ).pack(anchor="w")
        tk.Label(
            header_inner, text="Choose a sign type, add your labels, and create printable PDFs.",
            font=("Segoe UI", 11), background=HEADER_BG, fg=HEADER_SUBTEXT,
        ).pack(anchor="w", pady=(2, 0))

        body_wrap = tk.Frame(self, background=PAGE_BG)
        body_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(body_wrap, background=PAGE_BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(body_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        outer = tk.Frame(canvas, background=PAGE_BG, padx=24, pady=20)
        window_id = canvas.create_window((0, 0), window=outer, anchor="nw")

        def _on_outer_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        outer.bind("<Configure>", _on_outer_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            delta = -1 * (event.delta // 120) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._body_canvas = canvas

        self._build_type_selector(outer)
        self._build_step1(outer)
        self._build_preview_card(outer)
        self._build_step2(outer)
        self._build_step3(outer)

        self.status_card = tk.Frame(outer, background=PAGE_BG)
        self.status_card.pack(fill="x", pady=(4, 4))
        self.status_label = tk.Label(
            self.status_card, textvariable=self.status_var, font=("Segoe UI", 12, "bold"),
            background=PAGE_BG, fg=ACCENT, wraplength=760, justify="left", anchor="w",
        )
        self.status_label.pack(anchor="w", fill="x")

        self.progress = ttk.Progressbar(outer, mode="indeterminate")

        self.details_toggle_btn = tk.Label(
            outer, text="Show technical details \u25be", font=("Segoe UI", 9, "underline"),
            background=PAGE_BG, fg=TEXT_MUTED, cursor="hand2",
        )
        self.details_toggle_btn.pack(anchor="w", pady=(6, 0))
        self.details_toggle_btn.bind("<Button-1>", lambda _e: self._toggle_details())

        self.details_frame = tk.Frame(outer, background=PAGE_BG)
        self.log_box = scrolledtext.ScrolledText(
            self.details_frame, height=7, wrap="word", state="disabled",
            font=("Consolas", 9), background="#f4f4f4", foreground="#000000",
        )
        self.log_box.pack(fill="both", expand=True, pady=(6, 0))

        self._refresh_listbox()

    def _build_type_selector(self, parent):
        card = RoundedCard(parent)
        card.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(card.inner, background=CARD_BG, padx=20, pady=18)
        inner.pack(fill="x")

        tk.Label(
            inner, text="What are you making?", font=("Segoe UI", 14, "bold"),
            background=CARD_BG, fg=TEXT_DARK,
        ).pack(anchor="w")
        tk.Label(
            inner, text="Pick one - you can switch anytime, and each keeps its own list.",
            font=("Segoe UI", 10), background=CARD_BG, fg=TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 10))

        row = tk.Frame(inner, background=CARD_BG)
        row.pack(fill="x")

        self.type_buttons = {}
        for key, cfg in SIGN_TYPES.items():
            btn = tk.Button(
                row, text=f"{cfg['icon']}  {cfg['label']}\n{cfg['tagline']}",
                justify="left", anchor="w", wraplength=300,
                command=lambda k=key: self._switch_sign_type(k),
                font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
                padx=16, pady=14, cursor="hand2", highlightthickness=2,
            )
            btn.pack(side="left", padx=(0, 12), fill="both", expand=True)
            self.type_buttons[key] = btn

        self._refresh_type_buttons()

    def _refresh_type_buttons(self):
        for key, btn in self.type_buttons.items():
            if key == self.sign_type:
                btn.configure(bg=ACCENT, fg="white", highlightbackground=ACCENT_HOVER,
                              highlightcolor=ACCENT_HOVER)
            else:
                btn.configure(bg=TYPE_UNSELECTED_BG, fg=TEXT_DARK,
                              highlightbackground=TYPE_UNSELECTED_BG,
                              highlightcolor=TYPE_UNSELECTED_BG)

    def _build_step1(self, parent):
        card = RoundedCard(parent)
        card.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(card.inner, background=CARD_BG, padx=20, pady=18)
        inner.pack(fill="x")

        make_step_header(
            inner, 1, "Add your sign labels",
            'Signs that start the same way (like "a") get grouped into one PDF together. '
            'Your list is saved automatically, so you can add more later - even out of '
            'order - and everything will still print sorted by number.',
        )

        quick_box = tk.Frame(inner, background="#f7f9fc", highlightbackground=CARD_BORDER,
                              highlightthickness=1)
        quick_box.pack(fill="x", pady=(12, 4))
        quick_inner = tk.Frame(quick_box, background="#f7f9fc", padx=14, pady=12)
        quick_inner.pack(fill="x")

        tk.Label(quick_inner, text="Starts with", font=("Segoe UI", 9, "bold"),
                  background="#f7f9fc", fg=TEXT_MUTED).grid(row=0, column=0, sticky="w")
        tk.Label(quick_inner, text="Number", font=("Segoe UI", 9, "bold"),
                  background="#f7f9fc", fg=TEXT_MUTED).grid(row=0, column=1, sticky="w", padx=(16, 0))
        tk.Label(quick_inner, text="Up to (optional)", font=("Segoe UI", 9, "bold"),
                  background="#f7f9fc", fg=TEXT_MUTED).grid(row=0, column=2, sticky="w", padx=(16, 0))

        self.prefix_combo = ttk.Combobox(
            quick_inner, textvariable=self.quick_prefix, values=self.known_prefixes,
            width=8, style="Card.TEntry",
        )
        self.prefix_combo.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.prefix_combo.bind("<KeyRelease>", self._on_prefix_key)

        start_entry = ttk.Entry(quick_inner, textvariable=self.quick_start, width=8,
                                 style="Card.TEntry")
        start_entry.grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(4, 0))
        start_entry.bind("<Return>", lambda _e: self._on_quick_add())
        start_entry.bind("<KeyRelease>", self._update_preview)

        end_entry = ttk.Entry(quick_inner, textvariable=self.quick_end, width=8,
                               style="Card.TEntry")
        end_entry.grid(row=1, column=2, sticky="w", padx=(16, 0), pady=(4, 0))
        end_entry.bind("<Return>", lambda _e: self._on_quick_add())

        add_btn = styled_button(quick_inner, "+  Add", self._on_quick_add, ACCENT, ACCENT_HOVER)
        add_btn.grid(row=1, column=3, sticky="w", padx=(20, 0), pady=(4, 0))

        tk.Label(
            inner,
            text=('Example: Starts with "a", Number "001" \u2192 adds a-001, then gets ready '
                  'for the next one so you can keep clicking + Add. Fill in "Up to" as well '
                  'to add a whole batch at once.'),
            wraplength=740, foreground=TEXT_MUTED, background=CARD_BG, font=("Segoe UI", 9),
            justify="left",
        ).pack(anchor="w", pady=(8, 12))

        list_row = tk.Frame(inner, background=CARD_BG)
        list_row.pack(fill="both", expand=True)

        list_frame = tk.Frame(list_row, background=CARD_BG, highlightbackground=FIELD_BORDER,
                               highlightthickness=1)
        list_frame.pack(side="left", fill="both", expand=True)

        self.listbox = tk.Listbox(
            list_frame, height=5, font=("Segoe UI", 11), selectmode="extended",
            activestyle="none", highlightthickness=0, borderwidth=0,
            selectbackground=ACCENT, selectforeground="white",
        )
        self.listbox.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        self.listbox.bind("<<ListboxSelect>>", self._update_preview)
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        list_scroll.pack(side="left", fill="y")
        self.listbox.configure(yscrollcommand=list_scroll.set)

        button_col = tk.Frame(list_row, background=CARD_BG)
        button_col.pack(side="left", fill="y", padx=(12, 0))
        ttk.Button(button_col, text="Remove selected", command=self._remove_selected).pack(
            fill="x", pady=(0, 6)
        )
        ttk.Button(button_col, text="Remove all", command=self._remove_all).pack(fill="x")

        tk.Label(inner, textvariable=self.count_var, background=CARD_BG,
                  fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))

        adv_link = tk.Label(
            inner, text="Advanced: paste a list instead \u2192", font=("Segoe UI", 9, "underline"),
            background=CARD_BG, fg=ACCENT, cursor="hand2",
        )
        adv_link.pack(anchor="w", pady=(8, 0))
        adv_link.bind("<Button-1>", lambda _e: self._open_advanced_paste())

    def _build_preview_card(self, parent):
        card = RoundedCard(parent)
        card.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(card.inner, background=CARD_BG, padx=20, pady=18)
        inner.pack(fill="x")

        header_row = tk.Frame(inner, background=CARD_BG)
        header_row.pack(fill="x")
        tk.Label(
            header_row, text="\U0001f5bc  Live preview", font=("Segoe UI", 14, "bold"),
            background=CARD_BG, fg=TEXT_DARK,
        ).pack(side="left")
        tk.Label(
            header_row, textvariable=self.preview_caption_var, font=("Segoe UI", 10),
            background=CARD_BG, fg=TEXT_MUTED,
        ).pack(side="left", padx=(10, 0))

        tk.Label(
            inner,
            text="This is what one printed sign will actually look like, to scale.",
            font=("Segoe UI", 10), background=CARD_BG, fg=TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 10))

        self._preview_w = 460
        preview_wrap = tk.Frame(inner, background=CARD_BG)
        preview_wrap.pack(anchor="w")
        self.preview_canvas = tk.Canvas(
            preview_wrap, width=self._preview_w, height=291,
            background="white", highlightbackground=FIELD_BORDER, highlightthickness=1,
        )
        self.preview_canvas.pack()
        self._resize_preview_canvas()

        tk.Label(
            inner,
            text=("Note: the barcode always prints at the same size, no matter how many "
                  "digits the label has - longer labels just get thinner bars."),
            font=("Segoe UI", 9), background=CARD_BG, fg=TEXT_MUTED, wraplength=620,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        self._update_preview()

    def _build_step2(self, parent):
        card = RoundedCard(parent)
        card.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(card.inner, background=CARD_BG, padx=20, pady=18)
        inner.pack(fill="x")

        make_step_header(inner, 2, "Choose where to save", "Most people can leave this as it is.")

        row = tk.Frame(inner, background=CARD_BG)
        row.pack(fill="x", pady=(10, 0))
        entry = ttk.Entry(row, textvariable=self.output_dir, style="Card.TEntry")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(row, text="Choose folder...", command=self._browse_folder).pack(side="left")

    def _build_step3(self, parent):
        card = RoundedCard(parent)
        card.pack(fill="x", pady=(0, 4))
        inner = tk.Frame(card.inner, background=CARD_BG, padx=20, pady=18)
        inner.pack(fill="x")

        make_step_header(
            inner, 3, "Make your signs",
            "Click again anytime after adding more labels - it updates your PDFs with "
            "everything in the list, sorted by number, replacing the older version.",
        )

        row = tk.Frame(inner, background=CARD_BG)
        row.pack(fill="x", pady=(10, 0))
        self.generate_btn = styled_button(
            row, "\U0001f5a8  Create My Signs", self._on_generate, SUCCESS, SUCCESS_HOVER,
            font=("Segoe UI", 14, "bold"), padx=22, pady=13,
        )
        self.generate_btn.pack(side="left")

        ttk.Button(row, text="Open my files", command=self._open_output_folder).pack(
            side="left", padx=(14, 0)
        )

    # ------------------------------------------------------------ helpers
    def _describe_token(self, token):
        match = RANGE_RE.match(token)
        if match:
            prefix, start, end = match.groups()
            count = abs(int(end) - int(start)) + 1
            return f"{prefix}-{start}   through   {prefix}-{end}   ({count} signs)"
        return token

    def _update_count_label(self):
        if not self.labels:
            self.count_var.set("No sign labels added yet.")
            return
        total = 0
        for item in self.labels:
            match = RANGE_RE.match(item["raw"])
            if match:
                _prefix, start, end = match.groups()
                total += abs(int(end) - int(start)) + 1
            else:
                total += 1
        word = "label" if len(self.labels) == 1 else "entries"
        self.count_var.set(f"{len(self.labels)} {word} added \u2014 {total} sign(s) total.")

    def _refresh_listbox(self):
        self.listbox.delete(0, "end")
        for item in self.labels:
            self.listbox.insert("end", item["display"])
        self._update_count_label()
        self._update_preview()
        self._save_labels()

    def _add_token(self, raw_token):
        raw_token = raw_token.strip()
        if not raw_token:
            return
        if any(item["raw"] == raw_token for item in self.labels):
            return
        self.labels.append({"raw": raw_token, "display": self._describe_token(raw_token)})

    def _remove_selected(self):
        selected = list(self.listbox.curselection())
        if not selected:
            return
        for index in reversed(selected):
            del self.labels[index]
        self._refresh_listbox()

    def _remove_all(self):
        if not self.labels:
            return
        if messagebox.askyesno(
            "Remove all?",
            "Remove every label from the list? Your list is saved automatically, "
            "so this also clears what's remembered for next time.",
        ):
            self.labels = []
            self._refresh_listbox()

    def _on_prefix_key(self, event=None):
        self._filter_prefix_suggestions(event)
        self._update_preview()

    def _filter_prefix_suggestions(self, _event=None):
        typed = self.quick_prefix.get().strip().lower()
        if not typed:
            self.prefix_combo.configure(values=self.known_prefixes)
            return
        matches = [p for p in self.known_prefixes if p.lower().startswith(typed)]
        self.prefix_combo.configure(values=matches or self.known_prefixes)

    def _first_label_of_token(self, token):
        match = RANGE_RE.match(token)
        if match:
            prefix, start, _end = match.groups()
            return f"{prefix}-{start}"
        return token

    def _get_preview_label(self):
        selected = self.listbox.curselection()
        if selected and self.labels:
            index = selected[-1]
            if index < len(self.labels):
                return self._first_label_of_token(self.labels[index]["raw"])
        prefix = self.quick_prefix.get().strip()
        start = self.quick_start.get().strip()
        if prefix and start.isdigit():
            return f"{prefix}-{start}"
        if self.labels:
            return self._first_label_of_token(self.labels[-1]["raw"])
        return "a-001"

    def _resize_preview_canvas(self):
        module = self._module()
        page_w, page_h = module.PAGE_SIZE
        if self.sign_type == "sticky":
            vertical_extent = module.CELL_BORDER[3]
        else:
            vertical_extent = page_h
        scale = self._preview_w / page_w
        height = round(self._preview_w * (vertical_extent / page_w))
        self.preview_canvas.configure(height=height)
        self._preview_h = height
        self.preview_caption_var.set(f"\u2014 {self._config()['label']}")
        self._update_preview()

    def _update_preview(self, _event=None):
        if not hasattr(self, "preview_canvas"):
            return
        label = self._get_preview_label()
        self.preview_caption_var.set(f"\u2014 {self._config()['label']}, showing: {label}")
        if self.sign_type == "sticky":
            self._draw_preview_sticky(label)
        else:
            self._draw_preview_hanging(label)

    def _draw_preview_sticky(self, label_text):
        module = sticky_signs_core
        canvas_ = self.preview_canvas
        canvas_.delete("all")
        width, height = self._preview_w, self._preview_h
        scale = width / module.PAGE_SIZE[0]
        cell_bottom = module.CELL_BORDER[1]
        cell_top = module.CELL_BORDER[1] + module.CELL_BORDER[3]

        def to_px(x, y):
            return x * scale, (cell_top - y) * scale

        bx0, by0 = to_px(module.CELL_BORDER[0], cell_top)
        bx1, by1 = to_px(module.CELL_BORDER[0] + module.CELL_BORDER[2], cell_bottom)
        canvas_.create_rectangle(bx0, by0, bx1, by1, outline="#9aa0a8", width=1)

        rx, ry0 = to_px(module.RULE_X, module.RULE_Y1)
        _, ry1 = to_px(module.RULE_X, module.RULE_Y0)
        canvas_.create_line(rx, ry0, rx, ry1, fill="#c2c6cc")

        sx, sy = to_px(module.SMALL_POS[0], module.SMALL_POS[1])
        canvas_.create_text(
            sx, sy, text=label_text, anchor="w",
            font=("Helvetica", max(int(16 * scale), 7), "bold"),
        )

        rcx, rcy = to_px(module.ROTATED_ORIGIN[0] + 4, module.ROTATED_ORIGIN[1])
        canvas_.create_text(
            rcx, rcy, text=label_text, angle=90,
            font=("Helvetica", max(int(15.552 * scale), 6), "bold"),
        )

        try:
            modules = barcode_modules(label_text)
            module_width = module.BLOCK_WIDTH / len(modules)
            x = module.BAR_CENTER_X - module.BLOCK_WIDTH / 2.0
            bar_top = module.BAR_BOTTOM_Y + module.BAR_HEIGHT
            index = 0
            while index < len(modules):
                if modules[index] == "1":
                    run = 1
                    while index + run < len(modules) and modules[index + run] == "1":
                        run += 1
                    x1, y1 = to_px(x, bar_top)
                    x2, y2 = to_px(x + module_width * run, module.BAR_BOTTOM_Y)
                    canvas_.create_rectangle(x1, y1, x2, y2, fill="black", outline="")
                    x += module_width * run
                    index += run
                else:
                    x += module_width
                    index += 1
        except Exception:  # noqa: BLE001
            cx, cy = to_px(module.BAR_CENTER_X, module.BAR_BOTTOM_Y + module.BAR_HEIGHT / 2)
            canvas_.create_text(
                cx, cy, text="(barcode preview unavailable for this label)",
                font=("Segoe UI", 9), fill=TEXT_MUTED,
            )

        # Tkinter's font box renders a touch taller than reportlab's for the
        # same point size, so use a slightly smaller size than the literal
        # to-scale value to keep a clean gap above the bars.
        lx, ly = to_px(module.BAR_CENTER_X, module.LARGE_BASELINE_Y)
        canvas_.create_text(
            lx, ly, text=label_text, anchor="s",
            font=("Helvetica", max(int(45 * scale), 11), "bold"),
        )

    def _draw_preview_hanging(self, label_text):
        module = hanging_signs_core
        canvas_ = self.preview_canvas
        canvas_.delete("all")
        width, height = self._preview_w, self._preview_h
        page_w, page_h = module.PAGE_SIZE
        scale = width / page_w

        def to_px(x, y):
            return x * scale, (page_h - y) * scale

        canvas_.create_rectangle(1, 1, width - 1, height - 1, outline="#c2c6cc", width=1)

        try:
            modules = barcode_modules(label_text)
            module_width = module.BLOCK_WIDTH / len(modules)
            x = (page_w - module.BLOCK_WIDTH) / 2.0
            bar_top = module.BAR_ORIGIN_Y + module.BAR_HEIGHT
            index = 0
            while index < len(modules):
                if modules[index] == "1":
                    run = 1
                    while index + run < len(modules) and modules[index + run] == "1":
                        run += 1
                    x1, y1 = to_px(x, bar_top)
                    x2, y2 = to_px(x + module_width * run, module.BAR_ORIGIN_Y)
                    canvas_.create_rectangle(x1, y1, x2, y2, fill="black", outline="")
                    x += module_width * run
                    index += run
                else:
                    x += module_width
                    index += 1
        except Exception:  # noqa: BLE001
            cx, cy = to_px(page_w / 2, module.BAR_ORIGIN_Y + module.BAR_HEIGHT / 2)
            canvas_.create_text(
                cx, cy, text="(barcode preview unavailable for this label)",
                font=("Segoe UI", 9), fill=TEXT_MUTED,
            )

        sx, sy = to_px(module.SMALL_POS[0], module.SMALL_POS[1])
        canvas_.create_text(
            sx, sy, text=label_text, anchor="w",
            font=("Helvetica", max(int(16 * scale), 7), "bold"),
        )

        # Same deliberate small reduction as the Sticky preview, to avoid
        # Tkinter's slightly-taller font box touching the bars above it.
        lx, ly = to_px(page_w / 2, module.LARGE_BASELINE_Y)
        canvas_.create_text(
            lx, ly, text=label_text, anchor="s",
            font=("Helvetica", max(int(85 * scale), 14), "bold"),
        )

    @staticmethod
    def _increment_number(num_str):
        if not num_str.isdigit():
            return num_str
        width = len(num_str)
        return f"{int(num_str) + 1:0{width}d}"

    def _on_quick_add(self):
        prefix = self.quick_prefix.get().strip()
        start = self.quick_start.get().strip()
        end = self.quick_end.get().strip()

        if not prefix:
            messagebox.showwarning(
                "Missing info", 'Type or choose what the sign "starts with" first (e.g. "a").'
            )
            return
        if not start:
            messagebox.showwarning("Missing info", 'Type a number (e.g. "001").')
            return
        if not start.isdigit() or (end and not end.isdigit()):
            messagebox.showwarning(
                "Numbers only", "The number field(s) should contain digits only, e.g. 001."
            )
            return

        token = f"{prefix}-{start}:{end}" if end else f"{prefix}-{start}"
        self._add_token(token)
        self._refresh_listbox()
        self._remember_prefix(prefix)

        if end:
            self.quick_start.set(self._increment_number(end))
            self.quick_end.set("")
        else:
            self.quick_start.set(self._increment_number(start))

    def _open_advanced_paste(self):
        top = tk.Toplevel(self)
        top.title("Paste a list of labels")
        top.geometry("520x440")
        top.configure(background=PAGE_BG)
        top.transient(self)

        tk.Label(
            top,
            text=(
                "For people comfortable typing lists: paste or type labels below, "
                "one per line (commas also work). Ranges like a-001:010 are fine too. "
                f"These will be added to your {self._config()['label']} list."
            ),
            wraplength=480, background=PAGE_BG, fg=TEXT_DARK, padx=12, pady=12, justify="left",
        ).pack(anchor="w")

        text_box = scrolledtext.ScrolledText(top, height=14, font=("Consolas", 11))
        text_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        button_row = tk.Frame(top, background=PAGE_BG, padx=12, pady=12)
        button_row.pack(fill="x")

        def load_file():
            path = filedialog.askopenfilename(
                title="Choose a text file of labels",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                content = Path(path).read_text(encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Could not read file", str(exc), parent=top)
                return
            lines = [line.split("#", 1)[0].strip() for line in content.splitlines()]
            text_box.delete("1.0", "end")
            text_box.insert("1.0", "\n".join(line for line in lines if line))

        def add_these():
            content = text_box.get("1.0", "end-1c")
            pieces = [p for p in re.split(r"[,\s]+", content) if p.strip()]
            if not pieces:
                messagebox.showwarning("Nothing to add", "Type or paste at least one label.", parent=top)
                return
            for piece in pieces:
                self._add_token(piece)
            self._refresh_listbox()
            try:
                groups, _skipped = group_by_prefix(parse_labels(pieces))
                for prefix in groups:
                    self._remember_prefix(prefix)
            except Exception:  # noqa: BLE001
                pass
            top.destroy()

        ttk.Button(button_row, text="Load from text file...", command=load_file).pack(side="left")
        ttk.Button(button_row, text="Add these", command=add_these).pack(side="right")
        ttk.Button(button_row, text="Cancel", command=top.destroy).pack(side="right", padx=8)

    def _toggle_details(self):
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.details_frame.pack(fill="both", expand=True, pady=(4, 0))
            self.details_toggle_btn.configure(text="Hide technical details \u25b4")
        else:
            self.details_frame.pack_forget()
            self.details_toggle_btn.configure(text="Show technical details \u25be")

    def _browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir.get() or str(APP_DIR))
        if chosen:
            self.output_dir.set(chosen)

    def _open_output_folder(self):
        folder = Path(self.output_dir.get())
        folder.mkdir(parents=True, exist_ok=True)
        self._open_output_folder_path(folder)

    def _open_output_folder_path(self, folder):
        folder = Path(folder)
        try:
            if sys.platform.startswith("win"):
                import os
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", str(folder)], check=False)
            else:
                webbrowser.open(folder.as_uri())
        except Exception:  # noqa: BLE001
            pass

    def _append_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                message = self._log_queue.get_nowait()
                if isinstance(message, tuple) and message[0] == "RESULT":
                    self._handle_result(message[1])
                elif message is _WORKER_DONE:
                    self._worker_running = False
                    self.generate_btn.configure(state="normal")
                    self.progress.stop()
                    self.progress.pack_forget()
                else:
                    self._append_log(message)
        except queue.Empty:
            pass
        self._poll_job_id = self.after(100, self._poll_log_queue)

    def _on_close(self):
        if getattr(self, "_poll_job_id", None) is not None:
            try:
                self.after_cancel(self._poll_job_id)
            except Exception:  # noqa: BLE001
                pass
        try:
            self._save_labels()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()

    def _handle_result(self, result):
        if result.get("error"):
            self.status_label.configure(fg=WARNING)
            self.status_var.set(f"\u26a0  Something went wrong: {result['error']}")
            return
        groups = result["groups"]
        total = result["total"]
        out_dir = result["out_dir"]
        if groups:
            self.status_label.configure(fg=SUCCESS)
            self.status_var.set(
                f"\u2705  All done! Created {groups} PDF file(s) for {total} sign(s).\n"
                f"Saved in: {out_dir}"
            )
            self._open_output_folder_path(out_dir)
        else:
            self.status_label.configure(fg=WARNING)
            self.status_var.set("\u26a0  Nothing was created. Double check the labels in your list.")

    # -------------------------------------------------------------- action
    def _on_generate(self):
        if self._worker_running:
            return

        if not self.labels:
            messagebox.showwarning("No labels yet", "Add at least one sign label in Step 1 first.")
            return

        tokens = [item["raw"] for item in self.labels]

        try:
            groups, _skipped = group_by_prefix(parse_labels(tokens))
            for prefix in groups:
                self._remember_prefix(prefix)
        except Exception:  # noqa: BLE001
            pass

        out_dir_text = self.output_dir.get().strip()
        if not out_dir_text:
            messagebox.showwarning("No folder chosen", "Choose a folder to save PDFs in.")
            return
        out_dir = Path(out_dir_text)

        self.status_label.configure(fg=ACCENT)
        self.status_var.set("Working \u2026 creating your PDF files. This only takes a moment.")
        self._append_log(f"--- Generating {self._config()['label']} into {out_dir} ---")
        self.generate_btn.configure(state="disabled")
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress.start(12)
        self._worker_running = True

        module = self._module()
        thread = threading.Thread(
            target=self._run_generation, args=(tokens, out_dir, module), daemon=True
        )
        thread.start()

    def _run_generation(self, tokens, out_dir, module):
        def log(msg):
            self._log_queue.put(msg)

        try:
            result_dir, groups, total, _skipped = module.generate_signs(
                tokens, out_dir, run_name=module.RUN_FOLDER_NAME, log=log, overwrite=True
            )
            self._log_queue.put(("RESULT", {
                "groups": groups, "total": total, "out_dir": str(result_dir),
            }))
        except Exception as exc:  # noqa: BLE001
            log(f"ERROR: {exc}")
            self._log_queue.put(("RESULT", {"error": str(exc)}))
        finally:
            self._log_queue.put(_WORKER_DONE)


def main():
    app = SignMakerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
