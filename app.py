import streamlit as st
from supabase import create_client, Client
import PyPDF2  # Alat pembaca PDF
import io

# 1. Konfigurasi Supabase
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
KEY = "sb_publishable_nGCEdSUv8NtFEY3xi-7UQg_O_kpX25y"
supabase: Client = create_client(URL, KEY)

st.title("⚖️ Bank Data Putusan")

# Menu Navigasi
menu = ["Cari Putusan", "Upload Putusan", "Registrasi/Login"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru")
    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")
    
    # 🌟 FITUR BARU: ISIAN BEBAS UNTUK KASUS POSISI / KATA KUNCI 🌟
    kasus_posisi = st.text_area(
        "Ringkasan Kasus Posisi / Kata Kunci Bebas", 
        placeholder="Contoh: Sengketa tanah waris 2 hektar, bukti letter C, atau ketik kata kunci seperti: korupsi, dana desa, OTT..."
    )
    
    file_pdf = st.file_uploader("Pilih file PDF (Maksimal 500 KB)", type=['pdf'])

    if st.button("Simpan"):
        if file_pdf and judul and nomor:
            
            # --- SATPAM PENGECEK UKURAN (500 KB = 512.000 bytes) ---
            if file_pdf.size > 512000:
                st.error("🚨 Gagal: Ukuran file Anda terlalu besar! Batas maksimal hanya 500 KB.")
            else:
                with st.spinner("Sedang memproses dan menyimpan putusan..."):
                    # A. EKSTRAKSI TEKS DARI PDF
                    teks_putusan = ""
                    try:
                        pdf_reader = PyPDF2.PdfReader(file_pdf)
                        for page in pdf_reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                teks_putusan += extracted + "\n"
                    except Exception as e:
                        st.warning("Peringatan: Gagal membaca teks dari PDF. File tetap disimpan, tapi isinya tidak bisa dicari.")
                    
                    file_pdf.seek(0) 

                    # B. Upload File ke Storage
                    file_path = f"public/{file_pdf.name}"
                    supabase.storage.from_("dokumen-putusan").upload(file_path, file_pdf.getvalue())
                    
                    # C. Ambil URL File
                    file_url = supabase.storage.from_("dokumen-putusan").get_public_url(file_path)

                    # D. Simpan Metadata, Teks, & TAGS ke Database
                    data = {
                        "judul": judul, 
                        "nomor": nomor, 
                        "file_url": file_url,
                        "isi_teks": teks_putusan,
                        "tags": kasus_posisi # <-- Menyimpan ringkasan/tag bebas buatan user ke database
                    }
                    supabase.table("putusan").insert(data).execute()
                    
                    st.success("Putusan berhasil diupload beserta Ringkasan Kasusnya!")
        else:
            st.error("Lengkapi semua data (Judul, Nomor, dan File PDF)!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan (Deep Search)")
    query = st.text_input("Masukkan kata kunci (Judul, Nomor, Tags, atau Isi Putusan)")
    
    if query:
        # Cari di database berdasarkan judul, nomor, isi_teks, ATAU tags
        results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
        
        if results.data:
            st.success(f"Ditemukan {len(results.data)} putusan yang relevan")
            for item in results.data:
                st.write(f"### {item['judul']}")
                st.write(f"**Nomor:** {item['nomor']}")
                
                # Menampilkan Ringkasan Kasus jika ada isinya
                if item.get('tags'):
                    st.info(f"📝 **Ringkasan Kasus / Kata Kunci:** {item['tags']}")
                
                if item.get('isi_teks') and query.lower() in item['isi_teks'].lower():
                    st.caption("✨ Kata kunci ditemukan di dalam dokumen PDF.")
                    
                st.link_button("Lihat PDF", item['file_url'])
                st.divider()
        else:
            st.info("Putusan tidak ditemukan.")

# --- FITUR REGISTRASI ---
elif choice == "Registrasi/Login":
    st.subheader("Akun Member")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Daftar"):
        res = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Cek email Anda untuk konfirmasi!")
