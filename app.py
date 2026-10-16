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
# CSS UPLOADER
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
# FUNGSI BANTU (RADAR & STORAGE SYNC)
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
    # Sedot file dari brankas untuk fitur download paksa
    return supabase.storage.from_(BUCKET).download(path)

def safe_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"

# =========================================================
# TAMPILAN UTAMA
# =========================================================
st.markdown('<div class="radar-hero"><div class="radar-eyebrow">SISTEM INFORMASI ARSIP</div><h1>RADAR</h1><p>Repositori Akses Data Andal dan Responsif</p></div>', unsafe_allow_html=True)

menu = ["Cari Putusan", "Upload Putusan"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru")
    
    # Kunci "upload_putusan" menghubungkan uploader ini dengan CSS khusus di atas
    file_dokumen = st.file_uploader("Upload putusan", type=['pdf', 'doc', 'docx', 'rtf'], key="upload_putusan")
    
    judul_input = st.text_input("Judul Putusan", placeholder="Akan otomatis terisi jika file dipilih...")
    nomor_input = st.text_input("Nomor Putusan", placeholder="Akan otomatis terisi jika dikenali...")
    kasus_posisi = st.text_area("Ringkasan Tambahan (Opsional)")
    
    if st.button("Simpan"):
        # Auto-fill judul & nomor jika pengguna lupa mengisi tapi file sudah diupload
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
                    
                    # Upload ke Supabase
                    supabase.storage.from_(BUCKET).upload(
                        path=file_path, 
                        file=file_dokumen.getvalue(),
                        file_options={"content-type": safe_mime(file_dokumen.name), "upsert": "true"}
                    )
                    
                    file_url = supabase.storage.from_(BUCKET).get_public_url(file_path)
                    
                    # Generate tag dengan label 'storage sync'
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
                    st.success("Dokumen berhasil diupload ke RADAR!")
        else:
            st.error("Harap pilih file dokumen terlebih dahulu!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan")
    query = st.text_input("Masukkan kata kunci...")
    
    if query:
        try:
            results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
            
            if results.data:
                # Logika Deduplikasi Milik Bapak Hakim
                seen = set()
                hasil_unik = []
                for item in results.data:
                    item_id = item.get("id")
                    if item_id is None:
                        item_id = (item.get("file_url", ""), item.get("judul", ""), item.get("nomor", ""))
                    
                    if item_id not in seen:
                        seen.add(item_id)
                        hasil_unik.append(item)
                
                # Menampilkan Hasil
                if hasil_unik:
                    st.success(f"Ditemukan {len(hasil_unik)} putusan.")
                    for item in hasil_unik:
                        judul_hasil = item.get("judul") or "Tanpa Judul"
                        nomor_hasil = item.get("nomor") or "-"
                        
                        st.write(f"### {judul_hasil}")
                        st.write(f"**Nomor:** {nomor_hasil}")
                        
                        if item.get("tags"):
                            st.info(f"📝 {item['tags']}")
                        
                        file_url = item.get("file_url")
                        if file_url:
                            try:
                                path_str = storage_path_from_url(file_url)
                                if not path_str:
                                    raise ValueError("Path file tidak dapat dibaca dari file_url.")
                                
                                # Mengambil file untuk diunduh langsung (Mencegah RTF terbuka sebagai .txt)
                                file_bytes = get_file_bytes(path_str)
                                nama_download = Path(path_str).name
                                mime = safe_mime(nama_download)
                                
                                st.download_button(
                                    label="💾 Download Dokumen",
                                    data=file_bytes,
                                    file_name=nama_download,
                                    mime=mime,
                                    key=f"download_{item.get('id', path_str)}"
                                )
                            except Exception as e:
                                st.error("❌ Gagal menyiapkan file download.")
                        else:
                            st.warning("⚠️ File dokumen tidak tersedia.")
                        st.divider()
            else:
                st.info("🔎 Dokumen tidak ditemukan.")
        except Exception as e:
            st.error("❌ Terjadi kesalahan saat pencarian.")
