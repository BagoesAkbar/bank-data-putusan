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
st.markdown(
    """
    <style>

    .radar-hero {
        background: linear-gradient(135deg, #111111 0%, #242424 100%);
        color: #ffffff;
        border: 1px solid #3b3b3b;
        border-radius: 22px;
        padding: 2.2rem 2.3rem;
        margin: 0.25rem 0 1.2rem 0;
    }
    .radar-eyebrow {
        color: #c8c8c8;
        font-size: 0.78rem;
        letter-spacing: 0.13em;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }
    .radar-hero h1 {
        color: #ffffff;
        font-size: clamp(2rem, 4vw, 3rem);
        line-height: 1.12;
        letter-spacing: -0.035em;
        margin: 0 0 1rem 0;
    }
    .radar-hero p {
        color: #dddddd;
        font-size: 1rem;
        line-height: 1.7;
        max-width: 850px;
        margin: 0;
    }
    .radar-section-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin: 0.4rem 0 0.4rem 0;
    }
    .radar-link a { color: inherit; text-decoration: none; font-weight: 650; }
    #kategori-hukum { scroll-margin-top: 1rem; }

    /* =====================================================
       UPLOADER UTAMA
       ===================================================== */
    .st-key-upload_putusan
    [data-testid*="FileUploaderDropzoneInstructions"] {
        font-size: 0 !important;
    }
    .st-key-upload_putusan
    [data-testid*="FileUploaderDropzoneInstructions"] * {
        font-size: 0 !important;
        line-height: 0 !important;
        visibility: hidden !important;
    }
