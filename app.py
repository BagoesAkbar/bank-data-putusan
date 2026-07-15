import streamlit as st
from supabase import create_client, Client
import PyPDF2  # Alat pembaca PDF
import io

# 1. Konfigurasi Supabase
URL = "https://fymgslpozaruhtbtbbre.supabase.co"
KEY = "sb_publishable_nGCEdSUv8NtFEY3xi-7UQg_O_kpX25y"
supabase: Client = create_client(URL, KEY)

st.title("⚖️ Bank Data Putusan")

# Menu Navigasi (Fitur Login/Registrasi dihapus agar 100% Anonim)
menu = ["Cari Putusan", "Upload Putusan"]
choice = st.sidebar.selectbox("Pilih Menu", menu)

# --- FITUR UPLOAD ---
if choice == "Upload Putusan":
    st.subheader("Tambah Putusan Baru (Anonim)")
    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")
    
    # ISIAN BEBAS UNTUK KASUS POSISI / KATA KUNCI
    kasus_posisi = st.text_area(
        "Ringkasan Kasus Posisi / Kata Kunci Bebas", 
        placeholder="Contoh: Sengketa tanah waris 2 hektar, bukti letter C, atau ketik kata kunci seperti: korupsi, dana desa, OTT..."
    )
    
    # Menerima format PDF, DOC, DOCX, dan RTF dengan label anjuran anonimisasi
    file_dokumen = st.file_uploader("Upload putusan (Anonimisasi dianjurkan)", type=['pdf', 'doc', 'docx', 'rtf'])

    if st.button("Simpan"):
        if file_dokumen and judul and nomor:
            
            # --- SATPAM PENGECEK UKURAN (500 KB = 512.000 bytes) ---
            if file_dokumen.size > 512000:
                st.error("🚨 Gagal: Ukuran file Anda terlalu besar! Batas maksimal adalah 500 KB.")
            else:
                with st.spinner("Sedang memproses dan menyimpan dokumen..."):
                    # A. EKSTRAKSI TEKS (Hanya jika formatnya PDF)
                    teks_putusan = ""
                    if file_dokumen.name.lower().endswith('.pdf'):
                        try:
                            pdf_reader = PyPDF2.PdfReader(file_dokumen)
                            for page in pdf_reader.pages:
                                extracted = page.extract_text()
                                if extracted:
                                    teks_putusan += extracted + "\n"
                        except Exception as e:
                            st.warning("Peringatan: Gagal membaca teks dari PDF.")
                    else:
                        # Jika Word/RTF, kita andalkan tags/ringkasan kasus untuk pencarian
                        teks_putusan = "Dokumen Non-PDF. Pencarian mengandalkan Ringkasan Kasus."
                    
                    file_dokumen.seek(0) 

                    # B. Upload File ke Storage
                    # Pastikan nama file aman dari spasi agar URL tidak rusak
                    nama_file_aman = file_dokumen.name.replace(" ", "_")
                    file_path = f"public/{nama_file_aman}"
                    
                    supabase.storage.from_("dokumen-putusan").upload(file_path, file_dokumen.getvalue())
                    
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
                    
                    st.success("Dokumen berhasil diupload secara anonim!")
        else:
            st.error("Lengkapi semua data (Judul, Nomor, dan File)!")

# --- FITUR SEARCH ---
elif choice == "Cari Putusan":
    st.subheader("Pencarian Putusan (Deep Search)")
    query = st.text_input("Masukkan kata kunci (Judul, Nomor, Tags, atau Isi Putusan)")
    
    if query:
        # Cari di database berdasarkan judul, nomor, isi_teks, ATAU tags
        results = supabase.table("putusan").select("*").or_(f"judul.ilike.%{query}%,nomor.ilike.%{query}%,isi_teks.ilike.%{query}%,tags.ilike.%{query}%").execute()
        
        if results.data:
            st.success(f"Ditemukan {len(results.data)} dokumen yang relevan")
            for item in results.data:
                st.write(f"### {item['judul']}")
                st.write(f"**Nomor:** {item['nomor']}")
                
                # Menampilkan Ringkasan Kasus jika ada isinya
                if item.get('tags'):
                    st.info(f"📝 **Ringkasan Kasus / Kata Kunci:** {item['tags']}")
                
                if item.get('isi_teks') and query.lower() in item['isi_teks'].lower():
                    st.caption("✨ Kata kunci ditemukan di dalam dokumen PDF.")
                    
                # 🌟 PERBAIKAN: Tombol Pintar & Pemaksa Download 🌟
                if item['file_url'].lower().endswith('.pdf'):
                    st.link_button("📄 Lihat PDF", item['file_url'])
                else:
                    # Menambahkan '?download=' di ujung URL agar file otomatis terunduh!
                    st.link_button("💾 Download Dokumen (Buka di Word)", item['file_url'] + "?download=")
                    
                st.divider()
        else:
            st.info("Dokumen tidak ditemukan.")
