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
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
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
# CSS KUSTOM (Tema Dashboard RADAR & Fix Uploader)
# =========================================================
css = chr(10).join([
    "<style>",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] { font-size: 0 !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions'] * { font-size: 0 !important; line-height: 0 !important; visibility: hidden !important; }",
    ".st-key-upload_putusan [data-testid*='FileUploaderDropzoneInstructions']::after { content: 'Maksimal 500 KB per file'; display: block !important; font-size: 0.75rem !important; line-height: 1.2 !important; color: #c8c8c8 !important; margin-top: 2px !important; visibility: visible !important; }",
    
    ".radar-header-container { display: flex; align-items: center; gap: 1.2rem; margin-bottom: 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #333; }",
    ".radar-logo-box { background-color: #1e1e1e; padding: 0.8rem; border-radius: 12px; border: 1px solid #333; display: flex; align-items: center; justify-content: center; }",
    ".radar-title { margin: 0; font-size: 1.6rem; font-weight: 800; color: #ffffff; letter-spacing: 0.5px; }",
    ".radar-subtitle { margin: 0; font-size: 0.95rem; color: #9ca3af; }",
    
    ".radar-hero-title { font-size: 1.8rem; font-weight: 700; color: #ffffff; margin-bottom: 0.8rem; letter-spacing: -0.5px; }",
    ".radar-hero-desc { font-size: 1.05rem; color: #9ca3af; margin-bottom: 2rem; line-height: 1.6; max-width: 900px; }",
    
    ".radar-stats-title { font-size: 1.1rem; font-weight: 700; color: #ffffff; margin: 2.5rem 0 1rem 0; }",
    ".radar-card { background-color: #000000; border: 1px solid #2a2a2a; border-radius: 12px; padding: 1.5rem; display: flex; flex-direction: column; justify-content: space-between; height: 100%; transition: border-color 0.2s; }",
    ".radar-card:hover { border-color: #555; }",
    ".radar-card-icon { color: #9ca3af; margin-bottom: 1.5rem; }",
    ".radar-card-value { font-size: 1.8rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem; }",
    ".radar-card-label { font-size: 0.85rem; color: #9ca3af; }",
    
    "[data-testid='stTextInput'] input { background-color: #ffffff !important; color: #000000 !important; border-radius: 8px !important; padding: 0.8rem 1rem !important; font-size: 1.05rem !important; }",
    "[data-testid='stTextInput'] input::placeholder { color: #6b7280 !important; }",
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
    pattern = re.compile(r"(?i)(\d+)[_\-\s]+(Pdt[.][A-Za-z]+(?:-[A-Za-z]+)?)[_\-\s]+(\d{4})[_\-\s]+([A-Za-z]{2,}(?:[.][A-Za-z0-9]+)*)")
    nama_tanpa_ekstensi = Path(file_name).stem
    match = pattern.search(nama_tanpa_ekstensi)
    if not match:
        return ""
    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}/{match.group(4)}"

def build_tags(file_name: str, extension: str) -> str:
    stem = Path(file_name).stem
    words = re.split(r"[^A-Za-z0-9]+", stem)
    words = [word.lower() for word in words if word]
    tags = ["storage sync"]
    if extension:
        tags.append(extension.lstrip(".").lower())
    tags.extend(words)
    return ", ".join(tags)

def storage_path_from_url(url: str) -> str:
    if not url: return ""
    path_str = url.split(f"{BUCKET}/")[-1]
    return unquote(path_str)

def get_file_bytes(path: str) -> bytes:
    return supabase.storage.from_(BUCKET).download(path)

def safe_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"

def get_total_documents() -> int:
    try:
        res = supabase.table("putusan").select("id").execute()
        return len(res.data) if res.data else 0
    except:
        return 0

# =========================================================
# NAVIGASI
# =========================================================
with st.sidebar:
    st.markdown("### Navigasi Menu")
    menu = ["Beranda (Pencarian)", "Upload Putusan Baru"]
    choice = st.radio("Pilih Menu:", menu)
    st.divider()
    st.caption("RADAR © 2024")

# =========================================================
# BERANDA (PENCARIAN)
# =========================================================
if choice == "Beranda (Pencarian)":
    
    header_html = """
    <div class="radar-header-container">
        <div class="radar-logo-box">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 3v18"/><path d="M3 10c0 3.3 2.7 6 6 6s6-2.7 6-6H3z"/><path d="M21 10c0 3.3-2.7 6-6 6s-6-2.7-6-6h12z"/><path d="M15 3h6"/><path d="M3 3h6"/>
            </svg>
        </div>
        <div>
            <h1 class="radar-title">RADAR</h1>
            <p class="radar-subtitle">Repositori Akses Data Andal dan Responsif</p>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    hero_html = """
    <div class="radar-hero-title">Temukan Putusan. Dalami Pertimbangan Hukumnya.</div>
    <div class="radar-hero-desc">Ruang kerja digital untuk menghimpun, menelusuri, dan mengelompokkan putusan pengadilan sebagai bahan kajian dan pengembangan pengetahuan hukum.</div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)
    
    query = st.text_input(
        "Cari", 
        label_visibility="collapsed", 
        placeholder="🔍 Cari nomor perkara, isu hukum, atau kata dalam putusan..."
    )
    
    col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 7])
    with col_btn1:
        st.button("Cari Putusan", use_container_width=True, type="primary")
    with col_btn2:
        st.button("Jelajahi Kategori", use_container_width=True)

    if query:
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            with st.spinner("Mencari dalam arsip RADAR..."):
                results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
                
                if results.data:
                    seen = set()
                    hasil_unik = []
                    for item in results.data:
                        item_id = item.get("id")
                        if item_id is None:
                            item_id = (item.get("file_url", ""), item.get("judul", ""), item.get("nomor", ""))
                        if item_id not in seen:
                            seen.add(item_id)
                            hasil_unik.append(item)
                    
                    if hasil_unik:
                        st.success(f"Ditemukan {len(hasil_unik)} putusan.")
                        for item in hasil_unik:
                            with st.container(border=True):
                                judul_hasil = item.get("judul") or "Tanpa Judul"
                                nomor_hasil = item.get("nomor") or "-"
                                
                                st.write(f"#### {judul_hasil}")
                                st.write(f"**Nomor:** {nomor_hasil}")
                                
                                if item.get("tags"):
                                    st.caption(f"🏷️ Kategori/Tags: {item['tags']}")
                                
                                file_url = item.get("file_url")
                                if file_url:
                                    try:
                                        path_str = storage_path_from_url(file_url)
                                        file_bytes = get_file_bytes(path_str)
                                        nama_download = Path(path_str).name
                                        mime = safe_mime(nama_download)
                                        
                                        st.download_button(
                                            label="💾 Unduh Dokumen Asli",
                                            data=file_bytes,
                                            file_name=nama_download,
                                            mime=mime,
                                            key=f"download_{item.get('id', path_str)}"
                                        )
                                    except Exception:
                                        st.error("Gagal menyiapkan file download.")
                                else:
                                    st.warning("File dokumen tidak tersedia.")
                else:
                    st.info("Dokumen tidak ditemukan.")
        except Exception as e:
            st.error("Terjadi kesalahan saat pencarian.")

    if not query:
        st.markdown("<div class='radar-stats-title'>Ringkasan koleksi — statistik arsip</div>", unsafe_allow_html=True)
        total_docs = get_total_documents()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='radar-card'>
                <div class='radar-card-icon'>
                    <svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'></path><polyline points='14 2 14 8 20 8'></polyline><line x1='16' y1='13' x2='8' y2='13'></line><line x1='16' y1='17' x2='8' y2='17'></line><polyline points='10 9 9 9 8 9'></polyline></svg>
                </div>
                <div>
                    <div class='radar-card-value'>{total_docs}</div>
                    <div class='radar-card-label'>Total putusan tersimpan</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class='radar-card'>
                <div class='radar-card-icon'>
                    <svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z'></path><line x1='7' y1='7' x2='7.01' y2='7'></line></svg>
                </div>
                <div>
                    <div class='radar-card-value'>12+</div>
                    <div class='radar-card-label'>Kategori hukum terdeteksi</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class='radar-card'>
                <div class='radar-card-icon'>
                    <svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='10'></circle><polyline points='12 6 12 12 16 14'></polyline></svg>
                </div>
                <div>
                    <div class='radar-card-value'>Hari Ini</div>
                    <div class='radar-card-label'>Pembaruan putusan terbaru</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# =========================================================
# UPLOAD PUTUSAN BARU
# =========================================================
elif choice == "Upload Putusan Baru":
    st.markdown("### Tambah Putusan Baru ke RADAR")
    st.caption("Unggah dokumen putusan untuk ditambahkan ke repositori pencarian.")
    st.divider()
    
    file_dokumen = st.file_uploader("Upload dokumen putusan", type=['pdf', 'doc', 'docx', 'rtf'], key="upload_putusan")
    
    judul_input = st.text_input("Judul Putusan", placeholder="Akan otomatis terisi jika file dipilih...")
    nomor_input = st.text_input("Nomor Putusan", placeholder="Akan otomatis terisi jika dikenali...")
    kasus_posisi = st.text_area("Ringkasan Tambahan (Kategori / Isu Hukum)", placeholder="Contoh: Wanprestasi, Sengketa Waris, dll.")
    
    if st.button("Simpan & Sinkronisasi", type="primary"):
        if file_dokumen and not judul_input:
            judul_input = clean_title(file_dokumen.name)
        if file_dokumen and not nomor_input:
            nomor_input = extract_case_number(file_dokumen.name)

        if file_dokumen and judul_input:
            if file_dokumen.size > 512000:
                st.error("🚨 Gagal: Ukuran file terlalu besar! Batas maksimal 500 KB.")
            else:
                with st.spinner("Sedang memproses & sinkronisasi..."):
                    teks_putusan = ""
                    ekstensi = Path(file_dokumen.name).suffix
                    
                    if file_dokumen.name.lower().endswith('.pdf'):
                        try:
                            pdf_reader = PyPDF2.PdfReader(file_dokumen)
                            for page in pdf_reader.pages:
                                extracted = page.extract_text()
                                if extracted: teks_putusan += extracted + "\n"
                        except Exception: 
                            pass
                    
                    file_dokumen.seek(0)
                    nama_file_aman = file_dokumen.name.replace(" ", "_")
                    file_path = f"{ROOT_PATH}/{nama_file_aman}"
                    
                    supabase.storage.from_(BUCKET).upload(
                        path=file_path, 
                        file=file_dokumen.getvalue(),
                        file_options={"content-type": safe_mime(file_dokumen.name), "upsert": "true"}
                    )
                    
                    file_url = supabase.storage.from_(BUCKET).get_public_url(file_path)
                    
                    auto_tags = build_tags(file_dokumen.name, ekstensi)
                    final_tags = f"{auto_tags}, {kasus_posisi}" if kasus_posisi else auto_tags

                    data = {
                        "judul": judul_input, 
                        "nomor": nomor_input, 
                        "file_url": file_url, 
                        "isi_teks": teks_putusan, 
                        "tags": final_tags
                    }
                    supabase.table("putusan").insert(data).execute()
                    st.success("✅ Dokumen berhasil diupload ke RADAR!")
        else:
            st.error("Harap pilih file dokumen terlebih dahulu!")
