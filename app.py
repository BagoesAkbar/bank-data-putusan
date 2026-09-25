import io
import mimetypes
import re
from pathlib import Path as FilePath
from urllib.parse import unquote, urlparse

import PyPDF2
import streamlit as st
from supabase import Client, create_client

# =========================================================
# KONFIGURASI
# =========================================================
st.set_page_config(
    page_title="Bank Data Putusan Menarik",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUPABASE_URL = "https://fymgslpozaruhtbtbbre.supabase.co"
SUPABASE_BUCKET = "dokumen-putusan"
SUPABASE_ROOT = "public"

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# TAMPILAN
# Tidak menggunakan triple-quoted string agar aman dari
# SyntaxError 'unterminated triple-quoted string literal'.
# =========================================================
CSS = "\n".join([
    "html, body, .stApp { background: #0b0f14 !important; color: #f3f4f6 !important; }",
    "[data-testid='stAppViewContainer'] { background: #0b0f14 !important; }",
    "[data-testid='stHeader'] { background: #0b0f14 !important; border-bottom: 1px solid #202938 !important; }",
    "[data-testid='stToolbar'] { visibility: hidden; }",
    "[data-testid='stDecoration'] { display: none; }",
    ".main .block-container { max-width: 1120px; padding-top: 2rem; padding-bottom: 3rem; }",
    ".site-header { border-bottom: 1px solid #202938; padding-bottom: 1rem; margin-bottom: 1.6rem; }",
    ".site-title { color: #f3f4f6; font-size: 1.65rem; font-weight: 700; letter-spacing: -0.025em; line-height: 1.25; }",
    ".site-subtitle { color: #9aa4b2; font-size: 0.88rem; margin-top: 0.3rem; }",
    ".hero, .result-card, .info-box { background: #111722 !important; border: 1px solid #273142 !important; border-radius: 12px; }",
    ".hero { padding: 1.7rem 1.8rem; margin-bottom: 1.25rem; }",
    ".hero-title { color: #f3f4f6; font-size: 1.45rem; font-weight: 700; margin-bottom: 0.35rem; }",
    ".hero-text { color: #aab4c2; font-size: 0.92rem; line-height: 1.6; }",
    ".result-card { padding: 1.15rem 1.25rem; margin-bottom: 0.9rem; box-shadow: 0 2px 12px rgba(0,0,0,.18); }",
    ".result-number { color: #79b8ff; font-size: 0.82rem; font-weight: 700; margin-bottom: 0.3rem; }",
    ".result-title { color: #f3f4f6; font-size: 1.08rem; font-weight: 700; line-height: 1.45; }",
    ".result-summary { color: #b7c0cc; font-size: 0.9rem; line-height: 1.65; margin-top: 0.65rem; }",
    ".tag { display: inline-block; color: #9cc7ff; background: #182437; border: 1px solid #2a4668; border-radius: 999px; padding: 0.25rem 0.55rem; margin: 0.55rem 0.25rem 0 0; font-size: 0.72rem; font-weight: 600; }",
    ".info-box { padding: 1rem 1.1rem; color: #b7c0cc; font-size: 0.9rem; line-height: 1.65; }",
    ".section-label { color: #f3f4f6; font-size: 1rem; font-weight: 700; margin: 1.2rem 0 0.65rem; }",
    ".builder { text-align: center; color: #6f7b8c; font-size: 0.68rem; letter-spacing: 0.02em; margin-top: 2.6rem; padding-top: 0.9rem; border-top: 1px solid #202938; }",
    "section[data-testid='stSidebar'] { background: #0a0e13 !important; border-right: 1px solid #202938 !important; }",
    "section[data-testid='stSidebar'] * { color: #e6e9ee !important; }",
    "section[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] p { color: #e6e9ee !important; }",
    "div[data-testid='stTextInput'] input, div[data-testid='stTextArea'] textarea { background: #111722 !important; color: #f3f4f6 !important; border: 1px solid #344054 !important; border-radius: 8px !important; }",
    "div[data-testid='stTextInput'] input::placeholder, div[data-testid='stTextArea'] textarea::placeholder { color: #778295 !important; opacity: 1 !important; }",
    "div[data-testid='stSelectbox'] > div > div { background: #111722 !important; color: #f3f4f6 !important; border: 1px solid #344054 !important; border-radius: 8px !important; }",
    "div[data-baseweb='popover'] { background: #111722 !important; }",
    "div[role='listbox'], div[role='option'] { background: #111722 !important; color: #f3f4f6 !important; }",
    "div[role='option']:hover { background: #1b2636 !important; }",
    "div[data-testid='stButton'] > button, div[data-testid='stDownloadButton'] > button { background: #111722 !important; color: #f3f4f6 !important; border: 1px solid #344054 !important; border-radius: 8px !important; font-weight: 600 !important; }",
    "div[data-testid='stButton'] > button:hover, div[data-testid='stDownloadButton'] > button:hover { background: #182437 !important; border-color: #5b9ee8 !important; color: #ffffff !important; }",
    "div[data-testid='stFileUploader'] { background: #111722 !important; border: 1px solid #273142 !important; border-radius: 10px !important; padding: .4rem !important; }",
    "div[data-testid='stFileUploaderDropzone'] { background: #0f141d !important; border: 1px dashed #344054 !important; }",
    "div[data-testid='stFileUploaderDropzone'] * { color: #d6dbe3 !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] { font-size: 0 !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] * { font-size: 0 !important; line-height: 0 !important; visibility: hidden !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions']::after { content: 'Maksimal 500 KB per file'; display: block !important; font-size: 0.75rem !important; line-height: 1.2 !important; color: #9aa4b2 !important; visibility: visible !important; }",
    "div[data-testid='stCaptionContainer'], .stCaption { color: #8d99a8 !important; }",
    "label, .stMarkdown, .stText, [data-testid='stMetricLabel'], [data-testid='stMetricValue'] { color: #e6e9ee !important; }",
    "hr { border-color: #202938 !important; }",
    "a { color: #79b8ff !important; }",
])
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)

# =========================================================
# FUNGSI BANTU
# =========================================================
def clean_title(file_name):
    stem = FilePath(file_name).stem
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem)
    return stem.strip()


def safe_mime(file_name):
    mime = mimetypes.guess_type(file_name)[0]
    if mime:
        return mime
