import streamlit as st
from supabase import create_client, Client
import PyPDF2
import io
import mimetypes

# 1. Konfigurasi Supabase
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
KEY = "sb_publishable_nGCEdSUv8NtFEY3xi-7UQg_O_kpX25y"
supabase: Client = create_client(URL, KEY)

st.title("⚖️ Bank Data Putusan")

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
                                if page.extract_text(): teks_putusan += page.extract_text() + "\n"
                        except: pass
                    
                    file_dokumen.seek(0)
                    nama_file_aman = file_dokumen.name.replace(" ", "_")
                    file_path = f"public/{nama_file_aman}"
                    
                    supabase.storage.from_("dokumen-putusan").upload(
                        path=file_path, 
                        file=file_dokumen.getvalue(),
                        file_options={"content-type": file_dokumen.type, "upsert": "true"}
                    )
                    
                    file_url = supabase.storage.from_("dokumen-putusan").get_public_url(file_path)

                    data = {"judul": judul, "nomor": nomor, "file_url": file_url, "isi_teks": teks_putusan, "tags": kasus_posisi}
                    supabase.table("putusan").insert(data).execute()
                    st.success("Dokumen berhasil diupload!")
        else:
            st.error("Lengkapi semua data!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan (Deep Search)")
    query = st.text_input("Masukkan kata kunci...")
    
    if query:
        results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
        
        if results.data:
            for item in results.data:
                st.write(f"### {item['judul']}")
                st.write(f"**Nomor:** {item['nomor']}")
                if item.get('tags'): st.info(f"📝 {item['tags']}")
                
                # Mengambil Path dari URL agar bisa diunduh
                path_str = item['file_url'].split("dokumen-putusan/")[-1]
                
                try:
                    file_bytes = supabase.storage.from_("dokumen-putusan").download(path_str)
                    st.download_button(
                        label="💾 Download Dokumen",
                        data=file_bytes,
                        file_name=path_str.split("/")[-1],
                        mime="application/octet-stream"
                    )
                except Exception as e:
                    st.error("Gagal menyiapkan file download.")
                st.divider()
        else:
            st.info("Dokumen tidak ditemukan.")
