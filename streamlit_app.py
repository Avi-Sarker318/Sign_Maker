"""
Sign Maker - web version.

Same barcode/PDF logic as the desktop app (sign_maker_gui.py), but running
as a web page instead of a downloaded program. Deployed for free on
Streamlit Community Cloud - anyone with the link can use it in a browser,
nothing to install.

Note: unlike the desktop app, this page's label list only lives for your
current browser session/tab - it isn't remembered between visits, since
this is a shared public app rather than a program running on your own
computer. Download the PDFs when you're done with a batch.
"""

import io
import re
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

import hanging_signs_core
import sticky_signs_core
from signs_common import RANGE_RE, group_by_prefix, parse_labels

try:
    from pdf2image import convert_from_path
    PREVIEW_AVAILABLE = True
except Exception:  # noqa: BLE001
    PREVIEW_AVAILABLE = False

st.set_page_config(page_title="Sign Maker", page_icon="\U0001f4cb", layout="centered")

SIGN_TYPES = {
    "Sticky Signs": {
        "module": sticky_signs_core,
        "tagline": "Two signs per sheet, stacked - small barcode labels.",
    },
    "Hanging Signs": {
        "module": hanging_signs_core,
        "tagline": "One full landscape sheet per label - big overhead signs.",
    },
}


def describe_token(token):
    match = RANGE_RE.match(token)
    if match:
        prefix, start, end = match.groups()
        count = abs(int(end) - int(start)) + 1
        return f"{prefix}-{start}  through  {prefix}-{end}  ({count} signs)"
    return token


def first_label_of_token(token):
    match = RANGE_RE.match(token)
    if match:
        prefix, start, _end = match.groups()
        return f"{prefix}-{start}"
    return token


def increment_number(num_str):
    if not num_str.isdigit():
        return num_str
    width = len(num_str)
    return f"{int(num_str) + 1:0{width}d}"


def labels_key(sign_type):
    return f"labels__{sign_type}"


def get_labels(sign_type):
    return st.session_state.setdefault(labels_key(sign_type), [])


st.title("\U0001f4cb Sign Maker")
st.caption("Add labels and create printable barcode sign PDFs - right in your browser, nothing to install.")

if not PREVIEW_AVAILABLE:
    st.info(
        "Live preview isn't available in this environment (missing the pdf2image/poppler "
        "dependency), but generating and downloading PDFs still works normally."
    )

# ------------------------------------------------------------ sign type
st.subheader("What are you making?")
sign_type = st.radio(
    "Sign type", list(SIGN_TYPES.keys()), horizontal=True, label_visibility="collapsed",
)
st.caption(SIGN_TYPES[sign_type]["tagline"])
module = SIGN_TYPES[sign_type]["module"]
labels = get_labels(sign_type)

st.divider()

# ------------------------------------------------------------ quick add
st.subheader("1. Add your sign labels")
st.caption(
    'Signs that start the same way (like "a") get grouped into one PDF together. '
    "This list stays for your current visit - download your PDFs before you close the tab."
)

def _add_label_callback(sign_type):
    """
    Runs when "+ Add" is clicked, *before* the page redraws. Widget values
    can only be changed programmatically from inside a callback like this -
    doing it later in the main script body (after the widgets are already
    drawn) is what caused the crash.
    """
    prefix_key, start_key, end_key = f"prefix_{sign_type}", f"start_{sign_type}", f"end_{sign_type}"
    prefix_val = st.session_state.get(prefix_key, "").strip()
    start_val = st.session_state.get(start_key, "").strip()
    end_val = st.session_state.get(end_key, "").strip()

    if not prefix_val:
        st.session_state[f"warning_{sign_type}"] = 'Type or choose what the sign "starts with" first (e.g. "a").'
        return
    if not start_val:
        st.session_state[f"warning_{sign_type}"] = 'Type a number (e.g. "001").'
        return
    if not start_val.isdigit() or (end_val and not end_val.isdigit()):
        st.session_state[f"warning_{sign_type}"] = "The number field(s) should contain digits only, e.g. 001."
        return

    st.session_state[f"warning_{sign_type}"] = None
    token = f"{prefix_val}-{start_val}:{end_val}" if end_val else f"{prefix_val}-{start_val}"
    current_labels = get_labels(sign_type)
    if token not in current_labels:
        current_labels.append(token)

    if end_val:
        st.session_state[start_key] = increment_number(end_val)
        st.session_state[end_key] = ""
    else:
        st.session_state[start_key] = increment_number(start_val)


col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    prefix = st.text_input("Starts with", key=f"prefix_{sign_type}", placeholder="a")
with col2:
    start = st.text_input("Number", key=f"start_{sign_type}", placeholder="001")
with col3:
    end = st.text_input("Up to (optional)", key=f"end_{sign_type}", placeholder="010")
with col4:
    st.write("")
    st.write("")
    st.button(
        "+ Add", type="primary", use_container_width=True,
        on_click=_add_label_callback, args=(sign_type,),
    )

warning_message = st.session_state.get(f"warning_{sign_type}")
if warning_message:
    st.warning(warning_message)

if labels:
    st.write(f"**{len(labels)}** entr{'y' if len(labels) == 1 else 'ies'} added:")
    for token in labels:
        st.markdown(f"- {describe_token(token)}")

    remove_col, clear_col = st.columns([3, 1])
    with remove_col:
        to_remove = st.multiselect(
            "Remove specific entries",
            options=labels,
            format_func=describe_token,
            key=f"remove_select_{sign_type}",
        )
        if to_remove and st.button("Remove selected"):
            for token in to_remove:
                labels.remove(token)
            st.rerun()
    with clear_col:
        st.write("")
        if st.button("Remove all", use_container_width=True):
            labels.clear()
            st.rerun()
else:
    st.caption("No sign labels added yet.")

with st.expander("Advanced: paste a list instead"):
    pasted = st.text_area(
        "One label or range per line (commas also work)",
        placeholder="a-001\na-002\nc-001:004",
        key=f"paste_{sign_type}",
    )
    if st.button("Add pasted labels", key=f"add_pasted_{sign_type}"):
        pieces = [p for p in re.split(r"[,\s]+", pasted) if p.strip()]
        if not pieces:
            st.warning("Type or paste at least one label first.")
        else:
            for piece in pieces:
                if piece not in labels:
                    labels.append(piece)
            st.rerun()

st.divider()

# ------------------------------------------------------------ preview
st.subheader("2. Live preview")
st.caption("This is what one printed sign will actually look like, to scale.")

if labels:
    preview_label = first_label_of_token(labels[-1])
elif prefix.strip() and start.strip().isdigit():
    preview_label = f"{prefix.strip()}-{start.strip()}"
else:
    preview_label = "a-001"

st.caption(f"Showing: {preview_label}")

if PREVIEW_AVAILABLE:
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_path = module.build_pdf(preview_label, [preview_label], tmp_path)
            images = convert_from_path(str(pdf_path), dpi=150)
            preview_image = images[0]
            if sign_type == "Sticky Signs":
                # A single label only fills the top cell of the two-cell sheet;
                # crop tightly to that cell instead of showing a half-blank page.
                page_h_pt = sticky_signs_core.PAGE_SIZE[1]
                cell_top_pt = (sticky_signs_core.CELL_BORDER[1] + sticky_signs_core.CELL_Y_OFFSET
                               + sticky_signs_core.CELL_BORDER[3])
                cell_bottom_pt = sticky_signs_core.CELL_BORDER[1] + sticky_signs_core.CELL_Y_OFFSET
                top_frac = (page_h_pt - cell_top_pt) / page_h_pt
                bottom_frac = (page_h_pt - cell_bottom_pt) / page_h_pt
                w, h = preview_image.size
                preview_image = preview_image.crop(
                    (0, int(top_frac * h) - 5, w, int(bottom_frac * h) + 5)
                )
            st.image(preview_image, width="stretch" if sign_type == "Hanging Signs" else "content")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Couldn't render a preview for that label: {exc}")

st.caption(
    "Note: the barcode always prints at the same size, no matter how many digits the "
    "label has - longer labels just get thinner bars."
)

st.divider()

# ------------------------------------------------------------ generate
st.subheader("3. Create your signs")

if st.button("\U0001f5a8 Create My Signs", type="primary", disabled=not labels):
    with st.spinner("Creating your PDF files..."):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            try:
                out_dir, groups, total, skipped = module.generate_signs(
                    labels, tmp_path, run_name=module.RUN_FOLDER_NAME,
                    log=lambda _msg: None, overwrite=True,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Something went wrong: {exc}")
                groups = 0

            if groups:
                pdf_files = sorted(Path(out_dir).glob("*.pdf"))
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for pdf_file in pdf_files:
                        zf.write(pdf_file, arcname=pdf_file.name)
                zip_buffer.seek(0)

                st.success(f"All done! Created {groups} PDF file(s) for {total} sign(s).")
                st.download_button(
                    f"\u2b07\ufe0f Download {sign_type} ({len(pdf_files)} PDF file(s))",
                    data=zip_buffer,
                    file_name=f"{sign_type.replace(' ', '_')}.zip",
                    mime="application/zip",
                    type="primary",
                )
                if len(pdf_files) == 1:
                    st.download_button(
                        f"Or just download {pdf_files[0].name} directly",
                        data=pdf_files[0].read_bytes(),
                        file_name=pdf_files[0].name,
                        mime="application/pdf",
                    )
            else:
                st.warning("Nothing was created - double check the labels in your list.")
elif not labels:
    st.caption("Add at least one sign label above first.")