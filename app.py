import streamlit as st
from supabase import create_client, Client
import PyPDF2
import mimetypes
import io
import re
from pathlib import Path as FilePath
from urllib.parse import urlparse, unquote


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

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# TAMPILAN
# =========================================================

st.markdown(
    """
    <style>
    /* -----------------------------------------------------
       TEMA TERANG
       ----------------------------------------------------- */

    .stApp {
        background: #ffffff;
        color: #172033;
    }

    .main .block-container {
        max-width: 1120px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Header */
    .site-header {
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 1rem;
        margin-bottom: 1.6rem;
    }

    .site-title {
        color: #172033;
        font-size: 1.65rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        line-height: 1.25;
    }

    .site-subtitle {
        color: #667085;
        font-size: 0.88rem;
        margin-top: 0.3rem;
    }

    /* Hero */
    .hero {
        background: #f7f9fc;
        border: 1px solid #e2e7ee;
        border-radius: 14px;
        padding: 1.7rem 1.8rem;
        margin-bottom: 1.25rem;
    }

    .hero-title {
        color: #172033;
        font-size: 1.45rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .hero-text {
