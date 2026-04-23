import streamlit as st
from supabase import create_client, Client

# 1. Konfigurasi Supabase (Sudah diisi dengan data milik Anda)
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
KEY = "sb_publishable_nGCEdSUv8NtFEY3xi-7UQg_O_kpX25y"
supabase: Client = create_client(URL, KEY)

st.title("⚖️ Bank Data Putusan")

# Menu Navigasi Sederhana
menu = ["Cari Putusan", "Upload Putusan", "Registrasi/Login"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru")
    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")
    file_pdf = st.file_uploader("Pilih file PDF", type=['pdf'])

    if st.button("Simpan"):
        if file_pdf and judul and nomor:
            # A. Upload File ke Storage
            file_path = f"public/{file_pdf.name}"
            response_storage = supabase.storage.from_("dokumen-putusan").upload(file_path, file_pdf.getvalue())
            
            # B. Ambil URL File
            file_url = supabase.storage.from_("dokumen-putusan").get_public_url(file_path)

            # C. Simpan Metadata ke Database
            data = {"judul": judul, "nomor": nomor, "file_url": file_url}
            supabase.table("putusan").insert(data).execute()
            
            st.success("Putusan berhasil diupload!")
        else:
            st.error("Lengkapi semua data!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan")
    query = st.text_input("Masukkan kata kunci (Judul atau Nomor)")
    
    if query:
        # Cari di database berdasarkan judul atau nomor
        results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%").execute()
        
        if results.data:
            for item in results.data:
                st.write(f"### {item['judul']}")
                st.write(f"Nomor: {item['nomor']}")
                st.link_button("Lihat PDF", item['file_url'])
                st.divider()
        else:
            st.info("Putusan tidak ditemukan.")

# --- FITUR REGISTRASI (SEDERHANA) ---
elif choice == "Registrasi/Login":
    st.subheader("Akun Member")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Daftar"):
        res = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Cek email Anda untuk konfirmasi!")