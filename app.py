import streamlit as st
from supabase import create_client, Client
import PyPDF2
import io

# 1. Konfigurasi Supabase
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
KEY = "sb_publishable_nGCEdSUv8NtFEY3xi-7UQg_O_kpX25y"
supabase: Client = create_client(URL, KEY)

st.title("Bank Data Putusan Menarik")

# Menu Navigasi
menu = ["Cari Putusan", "Upload Putusan"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru (Anonim)")
    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")
    
    kasus_posisi = st.text_area(
        "Ringkasan Kasus Posisi / Kata Kunci Bebas", 
        placeholder="Contoh: Sengketa tanah waris 2 hektar, bukti letter C, atau ketik kata kunci seperti: korupsi, dana desa, OTT..."
    )
    
    # Menerima format PDF, DOC, DOCX, dan RTF
    file_dokumen = st.file_uploader("Upload putusan (Anonimisasi dianjurkan)", type=['pdf', 'doc', 'docx', 'rtf'])

    if st.button("Simpan"):
        if file_dokumen and judul and nomor:
            
            # Satpam ukuran 500 KB
            if file_dokumen.size > 512000:
                st.error("🚨 Gagal: Ukuran file Anda terlalu besar! Batas maksimal adalah 500 KB.")
            else:
                with st.spinner("Sedang memproses dokumen..."):
                    # Ekstraksi Teks jika PDF
                    teks_putusan = ""
                    if file_dokumen.name.lower().endswith('.pdf'):
                        try:
                            pdf_reader = PyPDF2.PdfReader(file_dokumen)
                            for page in pdf_reader.pages:
                                text = page.extract_text()
                                if text: teks_putusan += text + "\n"
                        except: teks_putusan = "Gagal ekstraksi PDF"
                    else:
                        teks_putusan = "Dokumen Non-PDF."
                    
                    file_dokumen.seek(0) 

                    # Upload ke Storage dengan Content-Type yang benar
                    nama_file = file_dokumen.name.replace(" ", "_")
                    file_path = f"public/{nama_file}"
                    
                    # 🌟 KUNCI PERBAIKAN: Menyertakan content-type agar browser tidak salah baca format
                    supabase.storage.from_("dokumen-putusan").upload(
                        path=file_path,
                        file=file_dokumen.getvalue(),
                        file_options={"content-type": file_dokumen.type}
                    )
                    
                    file_url = supabase.storage.from_("dokumen-putusan").get_public_url(file_path)

                    # Simpan Metadata
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
        results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
        if results.data:
            for item in results.data:
                st.write(f"### {item['judul']}")
                st.info(f"📝 **Ringkasan:** {item['tags']}")
                st.link_button("Download/Lihat Dokumen", item['file_url'])
                st.divider()
