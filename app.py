import streamlit as st
from supabase import create_client, Client
import PyPDF2
import io

# 1. Konfigurasi Supabase
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
KEY = "sb_publishable_nGCEdSUv8NtFEY3xi-7UQg_O_kpX25y"
supabase: Client = create_client(URL, KEY)

st.title("⚖️ Bank Data Putusan")

# Menu Navigasi
menu = ["Cari Putusan", "Upload Putusan"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru (Anonim)")
    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")
    kasus_posisi = st.text_area("Ringkasan Kasus Posisi / Kata Kunci Bebas")
    file_dokumen = st.file_uploader("Upload putusan (Anonimisasi dianjurkan, maks 500 KB)", type=['pdf', 'doc', 'docx', 'rtf'])

    if st.button("Simpan"):
        if file_dokumen and judul and nomor:
            if file_dokumen.size > 512000:
                st.error("🚨 Gagal: Ukuran file di atas 500 KB.")
            else:
                with st.spinner("Menyimpan..."):
                    # Simpan file dengan nama asli
                    file_path = f"public/{file_dokumen.name}"
                    
                    # Upload ke Storage Supabase
                    supabase.storage.from_("dokumen-putusan").upload(
                        path=file_path, 
                        file=file_dokumen.getvalue(),
                        file_options={"content-type": file_dokumen.type}
                    )
                    
                    # Dapatkan URL Publik
                    file_url = supabase.storage.from_("dokumen-putusan").get_public_url(file_path)
                    
                    # Simpan data ke database
                    data = {
                        "judul": judul, 
                        "nomor": nomor, 
                        "file_url": file_url,
                        "isi_teks": "Data dokumen", 
                        "tags": kasus_posisi
                    }
                    supabase.table("putusan").insert(data).execute()
                    st.success("Berhasil disimpan!")
        else:
            st.error("Lengkapi semua data!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan")
    query = st.text_input("Cari judul/nomor/tags...")
    
    if query:
        results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,tags.ilike.%{query}%").execute()
        
        if results.data:
            for item in results.data:
                st.write(f"### {item['judul']}")
                st.info(f"🏷️ {item['tags']}")
                
                # Gunakan link_button agar langsung mengunduh/membuka file asli
                # Ini menghindari error "Gagal mengambil file"
                st.link_button(f"💾 Download {item['judul']}", item['file_url'])
                st.divider()
        else:
            st.info("Tidak ditemukan.")
