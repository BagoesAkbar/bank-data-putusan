import io
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import PyPDF2
import streamlit as st
from supabase import Client, create_client

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
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".rtf"}
MAX_FILE_BYTES = 512_000  # batas aplikasi: 500 KB
PAGE_SIZE = 1000

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.info("Buka Settings → Secrets pada aplikasi Streamlit, lalu pastikan SUPABASE_KEY tersedia.")
    st.stop()

supabase: Client = create_client(URL, SUPABASE_KEY)

# =========================================================
# CSS - dibuat sebagai daftar string supaya tidak tergantung
# pada blok triple-quote saat kode disalin ke GitHub.
# =========================================================
CSS = "\n".join([
    "<style>",
    ".stApp { background: #0e1117; color: #f0f2f6; }",
    "[data-testid='stSidebar'] { background: #11151c; }",
    ".radar-hero { background: linear-gradient(135deg, #111111 0%, #242424 100%); color: #ffffff; border: 1px solid #3b3b3b; border-radius: 22px; padding: 2rem 2.2rem; margin: 0.25rem 0 1.2rem 0; }",
    ".radar-eyebrow { color: #c8c8c8; font-size: 0.78rem; letter-spacing: 0.13em; font-weight: 700; text-transform: uppercase; margin-bottom: 0.8rem; }",
    ".radar-hero h1 { color: #ffffff; font-size: clamp(2rem, 4vw, 3rem); line-height: 1.12; letter-spacing: -0.035em; margin: 0 0 0.75rem 0; }",
    ".radar-hero p { color: #dddddd; font-size: 1rem; line-height: 1.7; max-width: 900px; margin: 0; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] { font-size: 0 !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] * { font-size: 0 !important; line-height: 0 !important; visibility: hidden !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions']::after { content: 'Maksimal 500 KB per file'; display: block !important; font-size: 0.75rem !important; line-height: 1.2 !important; color: #b7bbc4 !important; margin-top: 2px !important; visibility: visible !important; }",
    "[data-testid='stMetric'] { background: #151a22; border: 1px solid #2a303b; padding: 0.8rem 1rem; border-radius: 12px; }",
    "</style>",
])
st.markdown(CSS, unsafe_allow_html=True)

# =========================================================
# FUNGSI BANTU - berasal dari alur aplikasi sebelumnya
# =========================================================
def clean_title(file_name: str) -> str:
    stem = Path(file_name).stem.replace("_", " ")
    return re.sub(r"\s+", " ", stem).strip()


def extract_case_number(file_name: str) -> str:
    # Mencoba mengenali nomor perkara pada nama file.
    stem = Path(file_name).stem
    pattern = re.compile(
        r"(?i)(\d+)[_\-\s]+(Pdt\.[A-Za-z]+(?:-[A-Za-z]+)?)[_\-\s]+"
        r"(\d{4})[_\-\s]+([A-Za-z]{2,}(?:\.[A-Za-z0-9]+)*)"
    )
    match = pattern.search(stem)
    if not match:
        return ""
    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}/{match.group(4)}"


def build_tags(file_name: str, extension: str, add_sync_tag: bool = False) -> str:
    stem = Path(file_name).stem
    words = [word.lower() for word in re.split(r"[^A-Za-z0-9]+", stem) if word]
    tags = []
    if add_sync_tag:
        tags.append("storage sync")
    if extension:
        tags.append(extension.lstrip(".").lower())
    tags.extend(words)

    unique_tags = []
    seen = set()
    for tag in tags:
        tag = tag.strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            unique_tags.append(tag)
    return ", ".join(unique_tags[:80])

