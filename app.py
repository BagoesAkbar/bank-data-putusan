import streamlit as st
from supabase import create_client, Client
import PyPDF2
import mimetypes
import io
import re
from pathlib import Path
from urllib.parse import urlparse, unquote

st.set_page_config(
    page_title="RADAR | Repositori Akses Data Andal dan Responsif",
    page_icon="🔎",
    layout="wide",
)
# =========================================================
# KONFIGURASI
# =========================================================
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
BUCKET = "dokumen-putusan"
ROOT_PATH = "public"
try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.stop()
supabase: Client = create_client(URL, SUPABASE_KEY)
# =========================================================
# TAMPILAN
# =========================================================
# =========================================================
# CSS UPLOADER
# =========================================================
# CSS ini hanya berlaku untuk uploader dengan key
# "upload_putusan".
#
# Tujuannya menyembunyikan teks bawaan Streamlit:
# "1MB per file • PDF, DOC, DOCX, RTF"
#
# lalu menampilkan:
# "Maksimal 500 KB per file"
# =========================================================
css = chr(10).join([
    "<style>",
    ".radar-hero { background: linear-gradient(135deg, #111111 0%, #242424 100%); color: #ffffff; border: 1px solid #3b3b3b; border-radius: 22px; padding: 2.2rem 2.3rem; margin: 0.25rem 0 1.2rem 0; }",
    ".radar-eyebrow { color: #c8c8c8; font-size: 0.78rem; letter-spacing: 0.13em; font-weight: 700; text-transform: uppercase; margin-bottom: 0.8rem; }",
    ".radar-hero h1 { color: #ffffff; font-size: clamp(2rem, 4vw, 3rem); line-height: 1.12; letter-spacing: -0.035em; margin: 0 0 1rem 0; }",
    ".radar-hero p { color: #dddddd; font-size: 1rem; line-height: 1.7; max-width: 850px; margin: 0; }",
    ".radar-section-title { font-size: 1.1rem; font-weight: 700; margin: 0.4rem 0 0.4rem 0; }",
    ".radar-link a { color: inherit; text-decoration: none; font-weight: 650; }",
    "#kategori-hukum { scroll-margin-top: 1rem; }",
    ".st-key-upload_putusan [data-testid*=\"FileUploaderDropzoneInstructions\"] { font-size: 0 !important; }",
    ".st-key-upload_putusan [data-testid*=\"FileUploaderDropzoneInstructions\"] * { font-size: 0 !important; line-height: 0 !important; visibility: hidden !important; }",
    ".st-key-upload_putusan [data-testid*=\"FileUploaderDropzoneInstructions\"]::after { content: \"Maksimal 500 KB per file\"; display: block !important; font-size: 0.75rem !important; line-height: 1.2 !important; color: rgba(49, 51, 63, 0.60) !important; margin-top: 2px !important; visibility: visible !important; }",
    ".st-key-upload_putusan [data-testid=\"stFileUploaderDropzoneInstructions\"] { font-size: 0 !important; }",
    ".st-key-upload_putusan [data-testid=\"stFileUploaderDropzoneInstructions\"] * { font-size: 0 !important; line-height: 0 !important; visibility: hidden !important; }",
    ".st-key-upload_putusan [data-testid=\"stFileUploaderDropzoneInstructions\"]::after { content: \"Maksimal 500 KB per file\"; display: block !important; font-size: 0.75rem !important; line-height: 1.2 !important; color: rgba(49, 51, 63, 0.60) !important; margin-top: 2px !important; visibility: visible !important; }",
    "</style>",
])
st.markdown(css, unsafe_allow_html=True)
# =========================================================
# FUNGSI BANTU
# =========================================================
def clean_title(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem)
    return stem.strip()
def extract_case_number(file_name: str) -> str:
    # Ambil nomor perkara jika pola nomor dapat dikenali dari nama file.
    pattern = re.compile(
        r"(?i)(\d+)[_\-\s]+(Pdt[.][A-Za-z]+(?:-[A-Za-z]+)?)[_\-\s]+(\d{4})[_\-\s]+([A-Za-z]{2,}(?:[.][A-Za-z0-9]+)*)"
    )
    # Lepaskan ekstensi terlebih dahulu agar .pdf/.rtf tidak ikut nomor pengadilan.
    nama_tanpa_ekstensi = Path(file_name).stem
    match = pattern.search(nama_tanpa_ekstensi)
    if not match:
        return ""
    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}/{match.group(4)}"

def build_tags(file_name: str, extension: str) -> str:
    stem = Path(file_name).stem
    words = re.split(
        r"[^A-Za-z0-9]+",
        stem
    )
    words = [
        word.lower()
        for word in words
        if word
    ]
    tags = ["storage sync"]
    if extension:
        tags.append(
            extension.lstrip(".").lower()
        )
    tags.extend(words)
