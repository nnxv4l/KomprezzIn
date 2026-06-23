import textwrap
import time
import os
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

css_dark = """
:root {
  --bg:#0a0b0e;--card:#121419;--card-2:#171a21;--line:#242833;--line-2:#30343f;
  --ink:#f3f4f6;--muted:#8b8f9a;--accent:#c8ff4d;--accent-ink:#0a0b0e;--accent-dim:rgba(200,255,77,.14);
  --ok:#3ddc84;--ok-bg:rgba(61,220,132,.12);--warn:#ffb020;--warn-bg:rgba(255,176,32,.12);--track:#22252e;
  --grid:rgba(255,255,255,.025);--glow:rgba(200,255,77,.10);
  --toggle-ink:#f3f4f6;
  --toggle-border:rgba(255,255,255,.28);
}
"""

css_light = """
:root {
  --bg:#f3f3ef;--card:#ffffff;--card-2:#fafaf7;--line:#e3e1d8;--line-2:#d4d2c8;
  --ink:#15161a;--muted:#6c6d6a;--accent:#3a7d12;--accent-ink:#ffffff;--accent-dim:rgba(58,125,18,.10);
  --ok:#15803d;--ok-bg:rgba(21,128,61,.10);--warn:#9a5b0a;--warn-bg:rgba(154,91,10,.12);--track:#e9e7df;
  --grid:rgba(0,0,0,.025);--glow:rgba(58,125,18,.06);
  --toggle-ink:#15161a;
  --toggle-border:rgba(0,0,0,.28);
}
"""

theme_css = css_light if st.session_state.theme == "light" else css_dark

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

{theme_css}

/* Hide Streamlit components */
#MainMenu {{visibility: hidden;}}
header {{visibility: hidden;}}
footer {{visibility: hidden;}}
.stApp > header {{display: none;}}
.stDeployButton {{display: none;}}

/* Global Body Styling */
.stApp {{
    background: var(--bg) !important;
    color: var(--ink) !important;
    font-family: 'Inter', sans-serif !important;
}}

/* Background effects */
.stApp::before {{
    content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
    background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:46px 46px;
}}
.stApp::after {{
    content:""; position:fixed; top:-160px; left:50%; transform:translateX(-50%); width:680px; height:420px; z-index:0;
    pointer-events:none; background:radial-gradient(circle,var(--glow),transparent 68%);
}}

.block-container {{
    padding-top: 3.5rem !important; /* Push container down into the grid box */
    padding-bottom: 70px !important;
    max-width: 740px !important;
    z-index: 1;
    position: relative;
}}

/* Streamlit Layout Overrides to tighten spacing */
[data-testid="stVerticalBlock"] {{
    gap: 0.8rem !important;
}}
[data-testid="stColumn"] {{
    padding-left: 0 !important;
    padding-right: 0 !important;
}}
[data-testid="column"] {{
    padding: 0 !important;
}}
/* Override Streamlit Column gap that breaks alignment */
[data-testid="stHorizontalBlock"] {{
    gap: 0 !important;
}}

/* Topbar Container Trick */
.topbar-container {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
}}
.brand{{font-family:'Space Mono',monospace;font-weight:700;font-size:.86rem;letter-spacing:.02em;
  display:flex;align-items:center;gap:.5rem;color:var(--ink);flex-shrink:0;}}
.brand .sq{{width:11px;height:11px;background:var(--accent);border-radius:2px;box-shadow:0 0 12px var(--accent);flex-shrink:0;}}

/* Theme Toggle Button via Key Class */
div.st-key-theme_toggle {{
    display: flex;
    justify-content: flex-end;
    width: 100%;
    margin-right: 0 !important;
}}
div.st-key-theme_toggle > div {{
    display: flex;
    justify-content: flex-end;
    width: 100%;
}}
div.st-key-theme_toggle button {{
    background: transparent !important;
    border: 1px solid var(--toggle-border) !important;
    color: var(--toggle-ink) !important;
    box-shadow: none !important;
    font-family: 'Space Mono', monospace !important;
    text-transform: uppercase !important;
    font-size: .72rem !important;
    font-weight: 700 !important;
    padding: .1rem .72rem !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: .15s !important;
    letter-spacing: .05em !important;
    min-height: 32px !important;
    width: fit-content !important;
    margin-top: 0;
    margin-left: auto !important;
    position: relative !important;
    right: 0 !important; /* Force shift to the right to align perfectly */
}}
div.st-key-theme_toggle button:hover {{
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: transparent !important;
    box-shadow: none !important;
    transform: none !important;
}}
div.st-key-theme_toggle button:active {{
    background: transparent !important;
    color: var(--accent) !important;
    border-color: var(--accent) !important;
}}
div.st-key-theme_toggle button p {{
    font-size: .72rem !important;
    font-weight: 700 !important;
}}

/* Hero */
@keyframes spin {{
    to {{ transform: rotate(360deg); }}
}}
.kicker{{display:inline-flex;align-items:center;gap:.5rem;font-family:'Space Mono',monospace;font-size:.72rem;font-weight:700;
  letter-spacing:.18em;text-transform:uppercase;color:var(--accent);background:var(--accent-dim);
  padding:.34rem .7rem;border-radius:6px;border:1px solid var(--line-2);margin-bottom:0.8rem;margin-top:0.4rem;}}
.kicker .pulse{{width:7px;height:7px;border-radius:50%;background:var(--accent);animation:pulse 1.4s infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;}}50%{{opacity:.25;}}}}
.title{{font-family:'Space Grotesk',sans-serif;font-size:4rem;font-weight:700;letter-spacing:-2px;line-height:.98;color:var(--ink);}}
.title .hl{{color:var(--accent);}}
.subtitle{{font-size:1.1rem;color:var(--muted);margin-top:0.6rem;max-width:32rem;}}
.subtitle b{{color:var(--ink);font-weight:600;}}

/* Steps */
.steps{{display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin:1.6rem 0 1.6rem 0;}}
.step{{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:1.1rem 1rem;transition:.18s;cursor:default;}}
.step:hover{{border-color:var(--accent);transform:translateY(-3px);}}
.step .n{{font-family:'Space Mono',monospace;font-size:.82rem;font-weight:700;color:var(--accent);}}
.step .t{{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:.96rem;margin-top:.6rem;color:var(--ink);}}
.step .s{{font-size:.79rem;color:var(--muted);margin-top:.2rem;}}
@media(max-width:620px){{.steps{{grid-template-columns:repeat(2,1fr);}}}}

/* Label */
.label{{font-family:'Space Mono',monospace;font-size:.72rem;font-weight:700;letter-spacing:.14em;
  text-transform:uppercase;color:var(--muted);margin-bottom:1.5rem;}}

/* Native Streamlit Uploader Styling */
[data-testid="stFileUploader"] {{
    margin-top: -5px;
    margin-bottom: 0.8rem;
}}
[data-testid="stFileUploaderDropzone"] {{
    border: 1.5px dashed var(--line-2) !important;
    border-radius: 14px !important;
    background: var(--card) !important;
    padding: 0 !important;
    min-height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: .18s !important;
    position: relative;
    overflow: hidden;
}}
[data-testid="stFileUploaderDropzone"]:hover {{
    border-color: var(--accent) !important;
    background: var(--card-2) !important;
}}

/* Hide default streamlit texts and buttons inside dropzone */
[data-testid="stFileUploaderDropzone"] button {{
    display: none !important;
}}
[data-testid="stFileUploaderDropzone"] svg {{
    display: none !important;
}}
[data-testid="stFileUploaderDropzone"] > div {{
    /* Make the invisible interactive layer fill the entire box */
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    width: 100%; height: 100%;
    opacity: 0 !important;
    z-index: 10;
}}

/* Inject custom icon and text via pseudo-elements */
[data-testid="stFileUploaderDropzone"]::before {{
    content: "[ + ]\\A Tarik & lepas file di sini\\A atau klik untuk memilih - PDF / DOCX / PPTX - maks 50MB";
    white-space: pre-wrap;
    text-align: center;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--ink);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 1;
    line-height: 1.6;
}}
[data-testid="stFileUploaderDropzone"]::first-line {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
}}
/* Replicating the dot-ic float effect on hover */
[data-testid="stFileUploaderDropzone"]:hover::before {{
    transform: translateY(-4px);
    transition: transform 0.2s ease;
}}

/* Target & Button Row */
.target{{display:flex;align-items:center;height:48px;font-size:.85rem;color:var(--muted);font-family:'Space Mono',monospace;white-space:nowrap;margin:0;}}
.target b{{color:var(--accent);}}

/* Custom Selectbox Styling for Target */
[data-testid="stSelectbox"] label {{display: none !important;}}
[data-testid="stSelectbox"] {{
    margin-top: 5px;
    height: 48px !important;
}}
[data-testid="stSelectbox"] > div[data-baseweb="select"] {{
    height: 48px !important;
}}
[data-testid="stSelectbox"] > div[data-baseweb="select"] > div {{
    background: transparent !important;
    border: 1px dashed var(--line-2) !important;
    border-radius: 10px !important;
    min-height: 48px !important;
    height: 48px !important;
    padding-left: 10px !important;
    display: flex;
    align-items: center;
    box-sizing: border-box !important;
}}
[data-testid="stSelectbox"] > div[data-baseweb="select"] > div:hover {{
    border-color: var(--accent) !important;
}}
[data-testid="stSelectbox"] * {{
    font-family: 'Space Mono', monospace !important;
    font-size: 0.85rem !important;
    color: var(--ink) !important;
}}

/* Native Streamlit Button Styling */
[data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) {{
    align-items: center;
    gap: 0.35rem !important;
    margin-bottom: 0.4rem;
}}
[data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) [data-testid="stColumn"],
[data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) .element-container,
[data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) [data-testid="stElementContainer"] {{
    padding: 0 !important;
    margin: 0 !important;
}}
div[class*="st-key-remove_file_"] {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
    height: 38px;
    transform: translateY(7px);
}}
div[class*="st-key-remove_file_"] button {{
    width: 38px !important;
    min-width: 38px !important;
    height: 38px !important;
    min-height: 38px !important;
    padding: 0 !important;
    border: 1px solid var(--line-2) !important;
    border-radius: 8px !important;
    background: var(--card-2) !important;
    color: var(--muted) !important;
    box-shadow: none !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    cursor: pointer !important;
    transition: .15s !important;
}}
div[class*="st-key-remove_file_"] button:hover {{
    border-color: var(--warn) !important;
    color: var(--warn) !important;
    background: var(--warn-bg) !important;
    box-shadow: none !important;
    transform: none !important;
}}
div[class*="st-key-remove_file_"] button:active {{
    background: var(--warn-bg) !important;
    color: var(--warn) !important;
    border-color: var(--warn) !important;
}}
div[class*="st-key-remove_file_"] button p {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
}}

[data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress),
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress_empty) {{
    margin-bottom: 0.5rem;
    align-items: center;
}}
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress) > [data-testid="stColumn"]:nth-child(2),
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress_empty) > [data-testid="stColumn"]:nth-child(2) {{
    display: flex;
    justify-content: flex-end;
}}
div.st-key-btn_cancel button {{
    height: 48px !important;
    min-height: 48px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: .95rem !important;
    font-weight: 700 !important;
    border: 1px solid var(--line-2) !important;
    border-radius: 10px !important;
    background: transparent !important;
    color: var(--muted) !important;
    cursor: pointer !important;
    transition: .15s !important;
    width: 100% !important;
    margin-top: 5px !important;
    box-sizing: border-box !important;
    padding: 0 !important;
    display: flex;
    align-items: center;
    justify-content: center;
}}
div.st-key-btn_cancel button:hover {{
    border-color: var(--warn) !important;
    color: var(--warn) !important;
}}
div.st-key-btn_cancel button:active {{
    background: transparent !important;
}}
div.st-key-btn_cancel button p {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: .95rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
}}
div.st-key-btn_compress button,
div.st-key-btn_compress_empty button {{
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: .95rem !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0 1.4rem !important;
    cursor: pointer !important;
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
    transition: .15s !important;
    letter-spacing: .01em !important;
    min-height: 48px !important;
    height: 48px !important;
    width: 100% !important;
    white-space: nowrap !important;
    margin-top: 5px !important;
    box-sizing: border-box !important;
    display: flex;
    align-items: center;
    justify-content: center;
}}
div.st-key-btn_compress,
div.st-key-btn_compress_empty {{
    display: flex;
    justify-content: flex-end;
    width: 100%;
}}
div.st-key-btn_compress button:hover,
div.st-key-btn_compress_empty button:hover {{
    box-shadow: 0 0 22px var(--accent-dim) !important;
    transform: translateY(-1px) !important;
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
}}
div.st-key-btn_compress button:active,
div.st-key-btn_compress_empty button:active {{
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
}}
div.st-key-btn_compress button p,
div.st-key-btn_compress_empty button p {{
    font-weight: 700 !important;
    font-size: .95rem !important;
    white-space: nowrap !important;
}}

div.st-key-btn_download button, div.st-key-btn_reset button {{
    height: 56px !important;
    min-height: 56px !important;
    padding: 0 16px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    border-radius: 10px !important;
    cursor: pointer !important;
    transition: .15s !important;
    letter-spacing: .01em !important;
    width: 100% !important;
    max-width: none !important;
}}
/* Tombol Unduh ZIP (Primary) */
div.st-key-btn_download {{
    margin-top: 1.6rem !important;
    padding-right: 0.5rem !important;
}}
div.st-key-btn_download button {{
    border: none !important;
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
}}
div.st-key-btn_download button:hover {{
    box-shadow: 0 0 22px var(--accent-dim) !important;
    transform: translateY(-1px) !important;
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
}}
div.st-key-btn_download button:active {{
    background: var(--accent) !important;
    color: var(--accent-ink) !important;
}}
div.st-key-btn_download button p, div.st-key-btn_reset button p {{
    font-size: 15px !important;
    font-weight: 600 !important;
    margin: 0 !important;
    text-align: center !important;
    width: 100% !important;
}}

/* Removed rules modifying stHorizontalBlock inside specific download container width to let use_container_width=True work */
div.st-key-btn_reset {{
    margin-top: 1.6rem !important;
    padding-left: 0.5rem !important;
}}
div.st-key-btn_reset button {{
    border: 1px solid var(--line-2) !important;
    background: transparent !important;
    color: var(--ink) !important;
}}
div.st-key-btn_reset button:hover {{
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: none !important;
}}
div.st-key-btn_reset button:active {{
    background: transparent !important;
    color: var(--accent) !important;
    border-color: var(--accent) !important;
}}
/* Removed old div.st-key-btn_reset button p block that overridden the global one */

/* Results */
.reshead{{display:flex;align-items:center;justify-content:space-between;margin:0 0 1.2rem;}}
.reshead .meta{{font-family:'Space Mono',monospace;font-size:.78rem;color:var(--accent);background:var(--accent-dim);padding:.26rem .6rem;border-radius:6px;}}
.fcard{{border:1px solid var(--line);border-radius:13px;background:var(--card);padding:1.1rem 1.15rem;margin-bottom:.8rem;transition:.18s;}}
.fcard:hover{{border-color:var(--line-2);transform:translateX(3px);}}
.fcard-top{{display:flex;align-items:center;gap:.85rem;}}
.ficon{{width:42px;height:42px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-family:'Space Mono',monospace;font-weight:700;font-size:.66rem;color:#fff;flex:none;}}
.pdf{{background:#d9472f;}}.doc{{background:#2f6bd9;}}.ppt{{background:#d97a1c;}}
.fname{{font-family:'Space Grotesk', sans-serif;font-weight:600;font-size:.98rem;color:var(--ink);}}
.fmeta{{font-size:.8rem;color:var(--muted);font-family:'Space Mono',monospace;margin-top:.12rem;}}
.tag{{margin-left:auto;font-family:'Space Mono',monospace;font-size:.76rem;font-weight:700;padding:.3rem .65rem;border-radius:7px;flex:none;}}
.tag.ok{{background:var(--ok-bg);color:var(--ok);}}.tag.warn{{background:var(--warn-bg);color:var(--warn);}}
.bar{{height:6px;border-radius:3px;background:var(--track);margin:1rem 0 .5rem;overflow:hidden;}}
.bar>span{{display:block;height:100%;border-radius:3px;background:var(--ok);}}
.bar.warnbar>span{{background:var(--warn);}}
.barlabel{{display:flex;justify-content:space-between;font-size:.79rem;color:var(--muted);font-family:'Space Mono',monospace;}}
.barlabel b{{color:var(--ink);}}
.hint{{font-size:.82rem;color:var(--warn);margin-top:.6rem;}}
.foot{{font-family:'Space Mono',monospace;color:var(--muted);font-size:.77rem;margin-top:2.5rem;padding-top:1.5rem;border-top:1px solid var(--line);}}
.foot b{{color:var(--ok);}}
/* Creator Badge Styling */
.creator-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 40px;
    padding: 0.35rem 0.9rem 0.35rem 0.35rem;
    text-decoration: none !important;
    transition: 0.2s ease;
    margin-top: 2rem;
}}
.creator-badge:hover {{
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px var(--accent-dim);
    text-decoration: none !important;
}}
.creator-img {{
    width: 26px;
    height: 26px;
    border-radius: 50%;
    object-fit: cover;
    border: 1px solid var(--line-2);
}}
.creator-text {{
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted) !important;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    text-decoration: none !important;
}}
.creator-name {{
    color: var(--accent) !important;
    font-weight: 700;
    text-decoration: none !important;
}}
/* Responsive Styles */
@media(max-width:640px) {{
    .block-container {{
        padding-top: 3.5rem !important;
        padding-bottom: 40px !important;
    }}
    /* Fix topbar alignment on mobile */
    /* Target the first horizontal block assuming it contains topbar */
    [data-testid="stHorizontalBlock"]:first-of-type {{
        flex-direction: row;
        flex-wrap: nowrap;
        gap: 0;
        align-items: center;
        width: 100%;
        overflow: visible;
        margin-bottom: 2rem !important;
    }}
    [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:nth-child(1) {{
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 0;
    }}
    [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:nth-child(2) {{
        width: auto !important;
        flex: 0 0 auto !important;
        display: flex;
        justify-content: flex-end;
    }}
    div.st-key-theme_toggle {{
        justify-content: flex-end;
        margin-top: 9px !important;
        margin-right: 0 !important; /* Prevent offside */
        margin-bottom: 1.5rem !important;
    }}
    div.st-key-theme_toggle button {{
        margin-top: 0;
        margin-right: 0 !important; /* Prevent offside */
    }}
    .brand {{
        margin-bottom: 1.5rem !important;
        padding-top: 0 !important;
    }}
    /* Make title standout */
    .title {{
        font-size: 3.8rem;
    }}
    .subtitle {{
        font-size: 0.95rem;
    }}
    .steps {{
        grid-template-columns: repeat(2, 1fr);
        gap: 0.6rem;
        margin: 2.4rem 0 2rem 0;
    }}

    /* Fix for file list and remove button alignment on mobile */
    [data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        margin-bottom: 0.1rem !important;
    }}
    [data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) > [data-testid="stColumn"]:nth-child(1) {{
        width: auto !important;
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(div[class*="st-key-remove_file_"]) > [data-testid="stColumn"]:nth-child(2) {{
        width: auto !important;
        flex: 0 0 38px !important;
        min-width: 38px !important;
        margin-left: 0.35rem !important;
    }}

    /* Target & Button Row Mobile Layout */
    [data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress),
    [data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress_empty) {{
        display: flex !important;
        flex-direction: column !important;
        gap: 0.5rem !important;
        margin-bottom: 0 !important;
    }}
    [data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has(div.st-key-btn_compress_empty) > [data-testid="stColumn"] {{
        width: 100% !important;
        min-width: 100% !important;
        flex: 1 1 100% !important;
    }}
    div.st-key-btn_cancel button {{
    height: 48px !important;
    min-height: 48px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: .95rem !important;
    font-weight: 600 !important;
    border: 1px solid var(--line-2) !important;
    border-radius: 10px !important;
    background: transparent !important;
    color: var(--muted) !important;
    cursor: pointer !important;
    transition: .15s !important;
    width: 100% !important;
    margin-top: 0 !important;
}}
div.st-key-btn_cancel button:hover {{
    border-color: var(--warn) !important;
    color: var(--warn) !important;
}}
div.st-key-btn_cancel button:active {{
    background: transparent !important;
}}
div.st-key-btn_cancel button p {{
    margin: 0 !important;
}}
div.st-key-btn_compress button,
div.st-key-btn_compress_empty button {{
        width: 100% !important;
        margin-top: 0 !important;
    }}
    .target {{
        display: flex !important;
        align-items: center;
        height: 48px; /* match button height */
        margin-bottom: 0.5rem !important;
        padding-top: 0 !important;
        white-space: nowrap;
    }}
    /* Enlarge Uploader on mobile */
    [data-testid="stFileUploaderDropzone"] {{
        padding: 3.5rem 1.5rem !important;
        min-height: 180px;
    }}
    [data-testid="stFileUploaderDropzone"]::before {{
        font-size: 1rem;
        line-height: 1.6;
        top: 0;
    }}
    [data-testid="stFileUploaderDropzone"]::first-line {{
        font-size: 1.8rem;
    }}

    /* Fix badge alignment in Results Header */
    .reshead {{
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        gap: 0;
    }}
    .reshead .meta {{
        margin-left: auto;
        margin-top: 0;
    }}
    .fcard-top {{
        flex-wrap: nowrap !important; /* Force items to stay in one row */
    }}
    .fcard-top > div:nth-child(2) {{
        min-width: 0;
        flex: 1;
    }}
    .fname {{
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }}

    }}
    /* Make actions buttons side-by-side */
/* Removed conflicting width rules to let use_container_width control the width */
/* Removed old btn_download and reset media query CSS */
/* CSS Khusus container action_buttons (CSS GRID - bulletproof equal) */
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) {{
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
    gap: 12px !important;
    width: 100% !important;
}}
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) > div,
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) > [data-testid="stColumn"] {{
    width: 100% !important;
    min-width: 0 !important;
    max-width: none !important;
}}
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) [data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) .stElementContainer,
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) .element-container,
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) [data-testid="stDownloadButton"],
[data-testid="stHorizontalBlock"]:has(div.st-key-btn_reset) [data-testid="stButton"] {{
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
}}
div.st-key-btn_download button,
div.st-key-btn_reset button {{
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    display: block !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

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

uploaded_files = [] # Inisialisasi awal agar tidak memicu UnboundLocalError di bagian bawah file

if not st.session_state.has_processed:
    st.markdown(
        """
    <div class="label" style="margin-top: 2rem;">// Unggah file</div>
    """,
        unsafe_allow_html=True,
    )

    # Native Streamlit File Uploader
    uploaded_files = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=["pdf", "docx", "doc", "pptx", "ppt"],
        label_visibility="collapsed",
        key=f"uploader_{st.session_state.uploader_key}",
        disabled=st.session_state.is_processing,
    )

    if uploaded_files:
        current_upload_keys = {get_uploaded_file_key(f) for f in uploaded_files}
        st.session_state.removed_upload_keys = [
            key
            for key in st.session_state.removed_upload_keys
            if key in current_upload_keys
        ]
        uploaded_files = [
            f
            for f in uploaded_files
            if get_uploaded_file_key(f) not in st.session_state.removed_upload_keys
        ]
    else:
        st.session_state.removed_upload_keys = []

    # Membatasi maksimal 5 file
    file_limit_warning = ""
    if uploaded_files and len(uploaded_files) > 5:
        uploaded_files = uploaded_files[:5]
        file_limit_warning = "<div style=\"background: var(--warn-bg); color: var(--warn); padding: 0.5rem 0.8rem; border-radius: 8px; font-size: 0.8rem; margin-top: -0.8rem; margin-bottom: 1rem; font-family: 'Space Grotesk', sans-serif; font-weight: 600; text-align: center; border: 1px solid var(--warn);\">Maksimal 5 file per sesi.</div>"

    # Menampilkan Daftar File yang Terpilih (Sebelum Dikompres)
    if uploaded_files:
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

if st.session_state.is_processing:
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

        # Hapus loading indicator
        loading_placeholder.empty()

# Menampilkan Hasil Kompresi Dinamis
if st.session_state.has_processed and st.session_state.results:
    total_files = len(st.session_state.results)
    success_files = sum(1 for r in st.session_state.results if r.get("success", False))

    html_out = f'<div id="results"><div class="reshead" style="margin-top: 2rem;"><div class="label" style="margin:0">// Hasil kompres</div><div class="meta">{total_files} file &bull; {success_files} diproses</div></div>'

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
        else:
            icon_cls = "doc"
            icon_text = ext.upper()[:3]

        if not r.get("success", False):
            err_msg = r.get("error", "Gagal memproses")
            html_out += textwrap.dedent(f"""
            <div class="fcard">
                <div class="fcard-top"><div class="ficon {icon_cls}">{icon_text}</div>
                <div><div class="fname">{fname}</div><div class="fmeta">Gagal diproses</div></div>
                <span class="tag warn">Error</span></div>
                <div class="hint">{err_msg}</div>
            </div>""")
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

            hint_html = ""
            if status == "warn":
                hint_html = '<div class="hint">Belum di bawah 2MB. Saran: kecilkan resolusi gambar atau pecah file.</div>'
            elif final_size == orig_size and orig_size <= (2 * 1024 * 1024):
                hint_html = '<div class="hint" style="color:var(--muted)">Ukuran file asli sudah kecil.</div>'

            html_out += textwrap.dedent(f"""
            <div class="fcard">
                <div class="fcard-top"><div class="ficon {icon_cls}">{icon_text}</div>
                <div><div class="fname">{fname}</div><div class="fmeta">{orig_str} &rarr; {final_str}</div></div>
                <span class="tag {tag_cls}">{final_str}</span></div>
                <div class="bar{bar_cls}"><span style="width: {saving_pct}%;"></span></div>
                <div class="barlabel"><span>penghematan</span><b class="cnt">{saving_pct}%</b></div>
                {hint_html}
            </div>""")

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
