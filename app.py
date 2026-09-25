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
    ".stApp { background: #ffffff !important; color: #172033 !important; }",
    ".main .block-container { max-width: 1120px; padding-top: 2rem; padding-bottom: 3rem; }",
    "header[data-testid='stHeader'] { background: #ffffff !important; }",
    "[data-testid='stToolbar'] { visibility: hidden; }",
    ".site-header { border-bottom: 1px solid #e5e7eb; padding-bottom: 1rem; margin-bottom: 1.6rem; }",
    ".site-title { color: #172033; font-size: 1.65rem; font-weight: 700; letter-spacing: -0.025em; line-height: 1.25; }",
    ".site-subtitle { color: #667085; font-size: 0.88rem; margin-top: 0.3rem; }",
    ".hero { background: #f7f9fc; border: 1px solid #e2e7ee; border-radius: 14px; padding: 1.7rem 1.8rem; margin-bottom: 1.25rem; }",
    ".hero-title { color: #172033; font-size: 1.45rem; font-weight: 700; margin-bottom: 0.35rem; }",
    ".hero-text { color: #667085; font-size: 0.92rem; line-height: 1.6; }",
    "div[data-testid='stTextInput'] input, div[data-testid='stTextArea'] textarea { background: #ffffff !important; color: #172033 !important; border: 1px solid #cfd6df !important; border-radius: 9px !important; }",
    "div[data-testid='stSelectbox'] > div > div { background: #ffffff !important; color: #172033 !important; border-color: #cfd6df !important; border-radius: 9px !important; }",
    "div[data-testid='stButton'] > button, div[data-testid='stDownloadButton'] > button { background: #ffffff !important; color: #172033 !important; border: 1px solid #b8c2cf !important; border-radius: 8px !important; font-weight: 600 !important; }",
    "div[data-testid='stButton'] > button:hover, div[data-testid='stDownloadButton'] > button:hover { border-color: #1f4b7a !important; color: #1f4b7a !important; }",
    ".result-card { background: #ffffff; border: 1px solid #e1e5ea; border-radius: 12px; padding: 1.15rem 1.25rem; margin-bottom: 0.9rem; box-shadow: 0 2px 8px rgba(16, 24, 40, 0.035); }",
    ".result-number { color: #1f4b7a; font-size: 0.82rem; font-weight: 700; margin-bottom: 0.3rem; }",
    ".result-title { color: #172033; font-size: 1.08rem; font-weight: 700; line-height: 1.45; }",
    ".result-summary { color: #475467; font-size: 0.9rem; line-height: 1.65; margin-top: 0.65rem; }",
    ".tag { display: inline-block; color: #1f4b7a; background: #f0f5fa; border: 1px solid #dce7f1; border-radius: 999px; padding: 0.25rem 0.55rem; margin: 0.55rem 0.25rem 0 0; font-size: 0.72rem; font-weight: 600; }",
    ".info-box { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem 1.1rem; color: #475467; font-size: 0.9rem; line-height: 1.65; }",
    ".section-label { color: #172033; font-size: 1rem; font-weight: 700; margin: 1.2rem 0 0.65rem; }",
    ".builder { text-align: center; color: #98a2b3; font-size: 0.68rem; letter-spacing: 0.02em; margin-top: 2.6rem; padding-top: 0.9rem; border-top: 1px solid #edf0f2; }",
    "section[data-testid='stSidebar'] { background: #fafbfc !important; border-right: 1px solid #e5e7eb; }",
    "section[data-testid='stSidebar'] * { color: #172033 !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] { font-size: 0 !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] * { font-size: 0 !important; line-height: 0 !important; visibility: hidden !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions']::after { content: 'Maksimal 500 KB per file'; display: block !important; font-size: 0.75rem !important; line-height: 1.2 !important; color: #667085 !important; visibility: visible !important; }",
    "[data-testid='stDecoration'] { display: none; }",
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
    ext = FilePath(file_name).suffix.lower()
    if ext == ".rtf":
        return "application/rtf"
    if ext == ".doc":
        return "application/msword"
    if ext == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


def extract_pdf_text(file_bytes):
    try:
