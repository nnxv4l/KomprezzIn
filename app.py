import time
import os
from components.ui import render_results_header, render_error_card, render_file_card
import concurrent.futures

import streamlit as st
import streamlit.components.v1 as components

from engine import process_file
from engine.utils import (
    cleanup_temp_dir,
    create_temp_dir,
    create_zip_from_bytes,
    format_size,
)

# Session State for Theme
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "start_processing" not in st.session_state:
    st.session_state.start_processing = False
if "has_processed" not in st.session_state:
    st.session_state.has_processed = False
if "results" not in st.session_state:
    st.session_state.results = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "removed_upload_keys" not in st.session_state:
    st.session_state.removed_upload_keys = []
if "target_size_label" not in st.session_state:
    st.session_state.target_size_label = "Standar (< 2MB)"

# Target size mapping
TARGET_OPTIONS = {
    "Standar (< 2MB)": 2 * 1024 * 1024,
    "Ekstrem (< 1MB)": 1 * 1024 * 1024,
}


def get_uploaded_file_key(uploaded_file):
    return f"{uploaded_file.name}:{uploaded_file.size}"


def do_compress():
    st.session_state.results = []
    st.session_state.has_processed = False
    st.session_state.is_processing = True
    st.session_state.start_processing = True # Tandai mulai, tapi eksekusi setelah UI terkunci


def remove_uploaded_file(file_key):
    if file_key not in st.session_state.removed_upload_keys:
        st.session_state.removed_upload_keys.append(file_key)
    st.session_state.results = []
    st.session_state.has_processed = False
    st.session_state.is_processing = False


def do_reset():
    st.session_state.results = []
    st.session_state.has_processed = False
    st.session_state.is_processing = False
    st.session_state.uploader_key += 1
    st.session_state.removed_upload_keys = []


def toggle_theme():
    if st.session_state.theme == "dark":
        st.session_state.theme = "light"
    else:
        st.session_state.theme = "dark"


st.set_page_config(
    page_title="KomprezzIn", layout="centered", initial_sidebar_state="collapsed"
)

@st.cache_data
def load_css(theme: str) -> str:
    theme_file = "assets/theme_light.css" if theme == "light" else "assets/theme_dark.css"
    with open(theme_file, "r") as f:
        theme_css = f.read()
        
    with open("assets/main.css", "r") as f:
        main_css = f.read()
        
    return f"""<style>
{theme_css}
{main_css}
</style>"""

st.markdown(load_css(st.session_state.theme), unsafe_allow_html=True)

# Topbar and Hero
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown(
        """
    <div class="brand" style="margin-bottom: 4rem; padding-top: 5px;"><span class="sq"></span>komprezz.in</div>
    """,
        unsafe_allow_html=True,
    )
with c2:
    st.button(
        "LIGHT" if st.session_state.theme == "dark" else "DARK",
        key="theme_toggle",
        on_click=toggle_theme,
        disabled=st.session_state.is_processing,
    )

st.markdown(
    """
<div class="kicker" style="margin-top: 0;"><span class="pulse"></span>Kompres file &bull; maks 2 MB</div>
<div class="title">Komprezz<span class="hl">In</span></div>
<div class="subtitle">Kompres file PDF, Word, &amp; PPTX jadi <b>di bawah 2MB</b>.</div>

<div class="steps">
    <div class="step"><div class="n">01</div><div class="t">Siapkan</div><div class="s">PDF, Word, PPTX</div></div>
    <div class="step"><div class="n">02</div><div class="t">Unggah</div><div class="s">Tarik &amp; lepas / klik</div></div>
    <div class="step"><div class="n">03</div><div class="t">Proses</div><div class="s">Otomatis &amp; cepat</div></div>
    <div class="step"><div class="n">04</div><div class="t">Selesai</div><div class="s">Unduh &lt; 2MB</div></div>
</div>
""",
    unsafe_allow_html=True,
)

uploaded_files = [] # Inisialisasi awal default


# Tidak lagi menggunakan @st.fragment agar state removal dapat sinkron langsung dengan uploader utama
def render_uploaded_files_list(uploaded_files):
    # Membatasi maksimal 5 file
    file_limit_warning = ""
    if len(uploaded_files) > 5:
        uploaded_files = uploaded_files[:5]
        file_limit_warning = "<div style=\"background: var(--warn-bg); color: var(--warn); padding: 0.5rem 0.8rem; border-radius: 8px; font-size: 0.8rem; margin-top: -0.8rem; margin-bottom: 1rem; font-family: 'Space Grotesk', sans-serif; font-weight: 600; text-align: center; border: 1px solid var(--warn);\">Maksimal 5 file per sesi.</div>"

    if file_limit_warning:
        st.markdown(file_limit_warning, unsafe_allow_html=True)

    for idx, f in enumerate(uploaded_files):
        _fname = f.name
        _ext = _fname.rsplit(".", 1)[-1].upper() if "." in _fname else "FILE"
        _size_mb = f.size / (1024 * 1024)
        _size_str = f"{_size_mb:.1f} MB".replace(".", ",")
        file_key = get_uploaded_file_key(f)

        is_over_limit = f.size > 50 * 1024 * 1024  # 50 MB

        if is_over_limit:
            row_html = f"""<div style="display: flex; align-items: center; justify-content: space-between; background: var(--card-2); border: 1px dashed var(--line); border-radius: 6px; padding: 0.4rem 0.8rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; opacity: 0.6; min-height: 38px; box-sizing: border-box;"><div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden;"><span style="color: var(--warn); font-weight: 700;">[ {_ext} ]</span><span style="color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-decoration: line-through;">{_fname}</span></div><span style="color: var(--warn); flex-shrink: 0;">{_size_str} (Maks 50MB)</span></div>"""
        else:
            row_html = f"""<div style="display: flex; align-items: center; justify-content: space-between; background: var(--card-2); border: 1px solid var(--line); border-radius: 6px; padding: 0.4rem 0.8rem; font-family: 'Space Mono', monospace; font-size: 0.75rem; min-height: 38px; box-sizing: border-box;"><div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden;"><span style="color: var(--accent); font-weight: 700;">[{_ext}]</span><span style="color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{_fname}</span></div><span style="color: var(--muted); flex-shrink: 0;">{_size_str}</span></div>"""

        row_file, row_remove = st.columns([0.94, 0.06])
        with row_file:
            st.markdown(row_html, unsafe_allow_html=True)
        with row_remove:
            st.button(
                "×",
                key=f"remove_file_{idx}",
                help=f"Hapus {_fname}",
                on_click=remove_uploaded_file,
                args=(file_key,),
                disabled=st.session_state.is_processing,
            )
            
    st.markdown('<div style="height: 0.2rem;"></div>', unsafe_allow_html=True)


if not st.session_state.has_processed:
    st.markdown(
        """
    <div class="label" style="margin-top: 2rem;">// Unggah file</div>
    """,
        unsafe_allow_html=True,
    )

    # Native Streamlit File Uploader
    raw_uploaded_files = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=["pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls"],
        label_visibility="collapsed",
        key=f"uploader_{st.session_state.uploader_key}",
        disabled=st.session_state.is_processing,
    )

    if raw_uploaded_files:
        current_upload_keys = {get_uploaded_file_key(f) for f in raw_uploaded_files}
        st.session_state.removed_upload_keys = [
            key
            for key in st.session_state.removed_upload_keys
            if key in current_upload_keys
        ]
        uploaded_files = [
            f
            for f in raw_uploaded_files
            if get_uploaded_file_key(f) not in st.session_state.removed_upload_keys
        ]
    else:
        st.session_state.removed_upload_keys = []
        uploaded_files = []

    # Menampilkan Daftar File yang Terpilih menggunakan Fragment
    if uploaded_files:
        render_uploaded_files_list(uploaded_files)

        # Tombol aksi ketika ADA file yang diunggah
        st.markdown('<div style="height: 0.2rem;"></div>', unsafe_allow_html=True)
        col_text, col_gap1, col_cancel, col_gap2, col_btn = st.columns([1.6, 0.1, 0.8, 0.1, 1.2])
        with col_text:
            selected_target = st.selectbox(
                "Target Kompresi",
                options=list(TARGET_OPTIONS.keys()),
                index=list(TARGET_OPTIONS.keys()).index(st.session_state.target_size_label),
                label_visibility="collapsed",
                disabled=st.session_state.is_processing,
                key="target_selectbox",
            )
            st.session_state.target_size_label = selected_target
        with col_gap1:
            st.empty()
        with col_cancel:
            st.button(
                "Batal &#10005;",
                key="btn_cancel",
                use_container_width=True,
                on_click=do_reset,
                disabled=st.session_state.is_processing,
            )
        with col_gap2:
            st.empty()
        with col_btn:
            st.button(
                "Kompres Sekarang &rarr;",
                key="btn_compress",
                use_container_width=True,
                on_click=do_compress,
                disabled=st.session_state.is_processing,
            )
    else:
        # Tombol aksi ketika KOSONG (belum ada file)
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        col_text, col_gap, col_btn = st.columns([1.9, 0.1, 1.2])
        with col_text:
            selected_target = st.selectbox(
                "Target Kompresi",
                options=list(TARGET_OPTIONS.keys()),
                index=list(TARGET_OPTIONS.keys()).index(st.session_state.target_size_label),
                label_visibility="collapsed",
                disabled=st.session_state.is_processing,
                key="target_selectbox_empty",
            )
            st.session_state.target_size_label = selected_target
        with col_gap:
            st.empty()
        with col_btn:
            st.button(
                "Kompres Sekarang &rarr;",
                key="btn_compress_empty",
                use_container_width=True,
                on_click=do_compress,
                disabled=st.session_state.is_processing,
            )

# Eksekusi Kompresi

if st.session_state.is_processing and st.session_state.start_processing:
    if not uploaded_files:
        st.markdown(
            """
            <div style="background: var(--warn-bg); color: var(--warn); padding: 0.6rem; border-radius: 8px; font-size: 0.85rem; font-family: 'Space Grotesk', sans-serif; font-weight: 600; text-align: center; border: 1px solid var(--warn); margin-bottom: 15px;">
                ⚠️ Belum ada file yang dipilih
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Suntikkan CSS dinamis untuk membuat kotak dropzone jadi merah dan bergetar
        st.markdown(
            """
            <style>
            [data-testid="stFileUploaderDropzone"] {
                border-color: var(--warn) !important;
                background: var(--warn-bg) !important;
                animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both;
            }
            @keyframes shake {
                10%, 90% { transform: translate3d(-1px, 0, 0); }
                20%, 80% { transform: translate3d(2px, 0, 0); }
                30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
                40%, 60% { transform: translate3d(4px, 0, 0); }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.session_state.is_processing = False
    else:
        loading_placeholder = st.empty()
        stages = [
            ("menganalisis file", 18),
            ("mengompres gambar", 52),
            ("mengoptimalkan struktur", 80),
            ("finalisasi", 100),
        ]

        for text, percent in stages:
            loading_html = f"""
            <div style="display:block; border:1px solid var(--line); border-radius:14px; background:var(--card); padding:1.5rem; margin-top:1.6rem;">
                <div style="display:flex; align-items:center; gap:.9rem;">
                    <div style="width:24px; height:24px; border-radius:50%; border:3px solid var(--track); border-top-color:var(--accent); animation:spin .7s linear infinite; flex:none;"></div>
                    <div>
                        <div style="font-family:'Space Grotesk', sans-serif; font-weight:600;">Mengompres…</div>
                        <div style="color:var(--muted); font-size:.84rem; font-family:'Space Mono', monospace; margin-top:.15rem;">{text}</div>
                    </div>
                </div>
                <div style="height:5px; border-radius:3px; background:var(--track); margin-top:1rem; overflow:hidden;">
                    <span style="display:block; height:100%; width:{percent}%; background:var(--accent); border-radius:3px; transition:width .4s ease; box-shadow:0 0 12px var(--accent);"></span>
                </div>
            </div>
            """
            loading_placeholder.markdown(loading_html, unsafe_allow_html=True)
            time.sleep(0.4)

        temp_dir = create_temp_dir()

        try:
            # Eksekusi hanya maksimal 5 file sesuai filter di atas
            files_to_process = uploaded_files[:5]

            futures_to_file = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for file in files_to_process:
                    original_size = file.size

                    # Lewati file jika di atas 50MB
                    if original_size > 50 * 1024 * 1024:
                        st.session_state.results.append(
                            {
                                "success": False,
                                "filename": file.name,
                                "error": "Ukuran melebihi batas maksimal (50 MB)",
                            }
                        )
                        continue

                    # Simpan file secara bertahap langsung ke disk (tanpa membacanya sepenuhnya ke memori)
                    input_path = os.path.join(temp_dir, f"in_{file.name}")
                    with open(input_path, "wb") as f:
                        f.write(file.getbuffer())

                    future = executor.submit(
                        process_file,
                        temp_dir,
                        file.name,
                        input_path,
                        TARGET_OPTIONS[st.session_state.target_size_label],
                    )
                    futures_to_file[future] = file.name

                for future in concurrent.futures.as_completed(futures_to_file):
                    try:
                        res = future.result()
                        st.session_state.results.append(res)
                    except Exception as e:
                        st.session_state.results.append(
                            {
                                "success": False,
                                "filename": futures_to_file[future],
                                "error": f"Error internal kompresi: {str(e)}",
                            }
                        )
        finally:
            cleanup_temp_dir(temp_dir)
            
        st.session_state.is_processing = False
        st.session_state.has_processed = True
        st.session_state.start_processing = False # Matikan tanda eksekusi

        # Hapus loading indicator
        loading_placeholder.empty()

        # Paksa rerun agar komponen uploader di atas benar-benar menghilang
        st.rerun()

# Menampilkan Hasil Kompresi Dinamis
if st.session_state.has_processed and st.session_state.results:
    total_files = len(st.session_state.results)
    success_files = sum(1 for r in st.session_state.results if r.get("success", False))

    html_out = render_results_header(total_files, success_files)

    for r in st.session_state.results:
        fname = r.get("filename", "Unknown")
        ext = fname.split(".")[-1].lower() if "." in fname else ""

        if ext == "pdf":
            icon_cls = "pdf"
            icon_text = "PDF"
        elif ext in ["docx", "doc"]:
            icon_cls = "doc"
            icon_text = "DOC"
        elif ext in ["pptx", "ppt"]:
            icon_cls = "ppt"
            icon_text = "PPT"
        elif ext in ["xlsx", "xls"]:
            icon_cls = "xls"
            icon_text = "XLS"
        else:
            icon_cls = "doc"
            icon_text = ext.upper()[:3]

        if not r.get("success", False):
            err_msg = r.get("error", "Gagal memproses")
            html_out += render_error_card(fname, icon_cls, icon_text, err_msg)
        else:
            orig_size = r["original_size"]
            final_size = r["final_size"]
            status = r["status"]

            saving_pct = 0
            if orig_size > 0:
                saving_pct = int(((orig_size - final_size) / orig_size) * 100)
                if saving_pct < 0:
                    saving_pct = 0

            orig_str = format_size(orig_size)
            final_str = format_size(final_size)

            tag_cls = "ok" if status == "ok" else "warn"
            bar_cls = "" if status == "ok" else " warnbar"

            # Buat label target dinamis untuk pesan peringatan
            target_label = "2MB" if st.session_state.target_size_label == "Standar (< 2MB)" else "1MB"
            target_limit_bytes = TARGET_OPTIONS[st.session_state.target_size_label]

            hint_html = ""
            if status == "warn":
                hint_html = f'<div class="hint">Belum di bawah {target_label}. Saran: kecilkan resolusi gambar atau pecah file.</div>'
            elif final_size == orig_size and orig_size <= target_limit_bytes:
                hint_html = '<div class="hint" style="color:var(--muted)">Ukuran file asli sudah kecil.</div>'

            html_out += render_file_card(fname, orig_str, final_str, saving_pct, status, hint_html, icon_cls, icon_text)

    html_out += "</div>"
    st.markdown(html_out, unsafe_allow_html=True)


# Tombol Aksi Bawah (Unduh Semua & Reset) - HANYA MUNCUL JIKA SUDAH DIPROSES
if st.session_state.has_processed and st.session_state.results:
    success_results = [r for r in st.session_state.results if r.get("success", False)]
    n_files = len(success_results)

    dl_data = b""
    dl_filename = "komprezz_output"
    dl_label = "&#8595; Unduh File"

    if n_files >= 2:
        dl_label = "&#8595; Unduh Semua (ZIP)"
        dl_filename = "komprezz.zip"
        dl_data = create_zip_from_bytes(
            [(r["filename"], r["bytes"]) for r in success_results]
        )
    elif n_files == 1:
        _name = success_results[0]["filename"]
        _ext = _name.rsplit(".", 1)[-1].upper() if "." in _name else "File"
        dl_label = f"&#8595; Unduh {_ext}"
        dl_filename = _name
        dl_data = success_results[0]["bytes"]

    with st.container(key="action_buttons"):
        col_dl, col_reset = st.columns([1, 1])
        with col_dl:
            if n_files > 0:
                st.download_button(
                    dl_label,
                    data=dl_data,
                    file_name=dl_filename,
                    key="btn_download",
                    width="stretch",
                )
            else:
                st.button(
                    "Gagal Diproses",
                    disabled=True,
                    width="stretch",
                    key="btn_download_err",
                )
        with col_reset:
            st.button(
                "&#8635; Kompres File Lain",
                key="btn_reset",
                width="stretch",
                on_click=do_reset,
            )

st.markdown(
    """
<div class="foot">[ <b>privasi</b> ] file diproses sementara &amp; dihapus otomatis setelah selesai.</div>
<div style="text-align: center; margin-bottom: 4rem;">
    <a href="https://github.com/nnxv4l" target="_blank" rel="noopener" class="creator-badge">
        <img src="https://github.com/nnxv4l.png" alt="M Naufal Sinambela" class="creator-img">
        <span class="creator-text">Dibuat oleh <span class="creator-name">M Naufal Sinambela</span></span>
    </a>
</div>
""",
    unsafe_allow_html=True,
)

# Injeksi JavaScript Pintar: Hanya cegah refresh jika ada file aktif
if uploaded_files or st.session_state.results:
    components.html(
        """
        <script>
            window.parent.onbeforeunload = function(e) {
                e.preventDefault();
                e.returnValue = '';
                return '';
            };
        </script>
        """,
        height=0,
        width=0,
    )
else:
    components.html(
        """
        <script>
            window.parent.onbeforeunload = null;
        </script>
        """,
        height=0,
        width=0,
    )
