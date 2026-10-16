import streamlit as st
from supabase import create_client, Client
import PyPDF2
import io

st.set_page_config(
    page_title="Bank Data Putusan Menarik",
    page_icon="🔎",
    layout="wide",
)

# =========================================================
# KONFIGURASI
# =========================================================
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
BUCKET = "dokumen-putusan"

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.stop()
    
supabase: Client = create_client(URL, SUPABASE_KEY)

# =========================================================
# TAMPILAN
# =========================================================
st.title("Bank Data Putusan Menarik")

menu = ["Cari Putusan", "Upload Putusan"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru (Anonim)")
    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")
    kasus_posisi = st.text_area("Ringkasan Kasus Posisi / Kata Kunci Bebas")
    file_dokumen = st.file_uploader("Upload putusan (Anonimisasi dianjurkan)", type=['pdf', 'doc', 'docx', 'rtf'])

    if st.button("Simpan"):
        if file_dokumen and judul and nomor:
            if file_dokumen.size > 512000:
                st.error("🚨 Gagal: Ukuran file Anda terlalu besar! Batas maksimal adalah 500 KB.")
            else:
                with st.spinner("Sedang memproses..."):
                    teks_putusan = "Dokumen Non-PDF."
                    if file_dokumen.name.lower().endswith('.pdf'):
                        try:
                            pdf_reader = PyPDF2.PdfReader(file_dokumen)
                            for page in pdf_reader.pages:
                                extracted = page.extract_text()
                                if extracted:
                                    teks_putusan += extracted + "\n"
                        except Exception: 
                            pass
                    
                    file_dokumen.seek(0)
                    nama_file_aman = file_dokumen.name.replace(" ", "_")
                    file_path = f"public/{nama_file_aman}"
                    
                    # Upload ke Storage dengan Upsert & Content-Type
                    supabase.storage.from_(BUCKET).upload(
                        path=file_path, 
                        file=file_dokumen.getvalue(),
                        file_options={"content-type": file_dokumen.type, "upsert": "true"}
                    )
                    
                    file_url = supabase.storage.from_(BUCKET).get_public_url(file_path)

                    data = {
                        "judul": judul, 
                        "nomor": nomor, 
                        "file_url": file_url, 
                        "isi_teks": teks_putusan, 
                        "tags": kasus_posisi
                    }
                    supabase.table("putusan").insert(data).execute()
                    st.success("Dokumen berhasil diupload!")
        else:
            st.error("Lengkapi semua data!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan (Deep Search)")
    query = st.text_input("Masukkan kata kunci...")
    
    if query:
        try:
            results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
            
            if results.data:
                st.success(f"Ditemukan {len(results.data)} putusan.")
                for item in results.data:
                    st.write(f"### {item.get('judul', 'Tanpa Judul')}")
                    st.write(f"**Nomor:** {item.get('nomor', '-')}")
                    if item.get('tags'): 
                        st.info(f"📝 {item['tags']}")
                    
                    file_url = item.get('file_url', '')
                    if file_url:
                        path_str = file_url.split(f"{BUCKET}/")[-1]
                        
                        try:
                            # Sedot file ke memori Streamlit untuk dipaksa download
                            file_bytes = supabase.storage.from_(BUCKET).download(path_str)
                            nama_download = path_str.split("/")[-1]
                            
                            st.download_button(
                                label="💾 Download Dokumen",
                                data=file_bytes,
                                file_name=nama_download,
                                mime="application/octet-stream",
                                key=f"dl_{item.get('id', nama_download)}"
                            )
                        except Exception as e:
                            st.error("❌ Gagal menyiapkan file download.")
                            st.code(str(e))
                    else:
                        st.warning("⚠️ File dokumen tidak tersedia.")
                    st.divider()
            else:
                st.info("🔎 Dokumen tidak ditemukan.")
        except Exception as e:
            st.error("❌ Terjadi kesalahan saat pencarian.")
            st.code(str(e))
