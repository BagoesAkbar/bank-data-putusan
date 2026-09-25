import streamlit as st
from supabase import create_client, Client
import PyPDF2
import mimetypes
import io
import re
from pathlib import Path
from urllib.parse import urlparse, unquote


# =========================================================
# 1. KONFIGURASI
# =========================================================

URL = "https://fymgslpozaruhtbtbbre.supabase.co"
BUCKET = "dokumen-putusan"
ROOT_PATH = "public"

try:
    KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.stop()

supabase: Client = create_client(URL, KEY)


# =========================================================
# 2. JUDUL APLIKASI
# =========================================================

st.title("Bank Data Putusan Menarik")


# =========================================================
# 3. FUNGSI BANTU
# =========================================================

def clean_title(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem)
    return stem.strip()


def extract_case_number(file_name: str) -> str:
    patterns = [
        r"(?i)(\d+)[_\- ]+(Pdt\.G)[_\- ]+(\d{4})[_\- ]+([A-Za-z]{2,}(?:\.[A-Za-z0-9]+)+)",
        r"(?i)(\d+)[_\- ]+(Pdt\.G)[_\- ]+(\d{4})[_\- ]+([A-Za-z]{2,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, file_name)

        if match:
            return (
                f"{match.group(1)}/"
                f"{match.group(2)}/"
                f"{match.group(3)}/"
                f"{match.group(4)}"
            )

    return ""


def build_tags(file_name: str, extension: str) -> str:
    stem = Path(file_name).stem

    words = re.split(r"[^A-Za-z0-9]+", stem)
    words = [word.lower() for word in words if word]

    tags = ["storage sync"]

    if extension:
        tags.append(extension.lstrip(".").lower())

    tags.extend(words)

    result = []
    seen = set()

    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)

    return ", ".join(result[:80])


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))

        pages = []

        for page in reader.pages:
            text_page = page.extract_text()

            if text_page:
                pages.append(text_page)

        return "\n".join(pages).strip()

    except Exception:
        return ""


def storage_path_from_url(file_url: str) -> str:
    if not file_url:
        return ""

    parsed = urlparse(file_url)

    markers = [
        f"/object/public/{BUCKET}/",
        f"/object/sign/{BUCKET}/",
        f"/object/{BUCKET}/",
    ]

    for marker in markers:
        if marker in parsed.path:
            return unquote(
                parsed.path.split(marker, 1)[1]
            )

    return ""


def get_file_bytes(file_path: str) -> bytes:
    return (
        supabase
        .storage
        .from_(BUCKET)
        .download(file_path)
    )


def list_all_storage_files(root_path: str = ROOT_PATH):
    storage = supabase.storage.from_(BUCKET)
    files = []

    def walk(folder_path: str):
        offset = 0
        limit = 1000

        while True:
            items = storage.list(
                folder_path,
                {
                    "limit": limit,
                    "offset": offset,
                    "sortBy": {
                        "column": "name",
                        "order": "asc",
                    },
                },
            ) or []

            if not items:
                break

            for item in items:
                name = item.get("name")

                if not name:
                    continue

                full_path = f"{folder_path}/{name}"

                metadata = item.get("metadata")
                item_id = item.get("id")

                # File Storage umumnya mempunyai metadata/id.
                # Folder biasanya tidak mempunyai keduanya.
                is_file = (
                    metadata is not None
                    or item_id is not None
                )

                if is_file:
                    files.append(full_path)
                else:
                    walk(full_path)

            if len(items) < limit:
                break

            offset += len(items)

    walk(root_path)

    return files


def get_existing_paths_from_database():
    existing_paths = set()

    offset = 0
    limit = 1000

    while True:
        response = (
            supabase
            .table("putusan")
            .select("id,file_url")
            .range(
                offset,
                offset + limit - 1
            )
            .execute()
        )

        rows = response.data or []

        for row in rows:
            path = storage_path_from_url(
                row.get("file_url", "")
            )

            if path:
                existing_paths.add(path)

        if len(rows) < limit:
            break

        offset += limit

    return existing_paths


def safe_mime(file_name: str) -> str:
    mime = mimetypes.guess_type(file_name)[0]

    if mime:
        return mime

    extension = Path(file_name).suffix.lower()

    if extension == ".rtf":
        return "application/rtf"

    if extension == ".doc":
        return "application/msword"

    if extension == ".docx":
        return (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    if extension == ".pdf":
        return "application/pdf"

    return "application/octet-stream"


# =========================================================
# 4. MENU
# =========================================================

menu = [
    "Cari Putusan",
    "Upload Putusan",
    "Sinkronisasi Storage",
]

choice = st.sidebar.selectbox(
    "Pilih Menu",
    menu,
)


# =========================================================
# 5. UPLOAD PUTUSAN
# =========================================================

if choice == "Upload Putusan":

    st.subheader("Tambah Putusan Baru (Anonim)")

    judul = st.text_input("Judul Putusan")
    nomor = st.text_input("Nomor Putusan")

    kasus_posisi = st.text_area(
        "Ringkasan Kasus Posisi / Kata Kunci Bebas"
    )

    file_dokumen = st.file_uploader(
    "Upload putusan (Anonimisasi dianjurkan) — maksimal 500 KB per file",
    type=["pdf", "doc", "docx", "rtf"],
    max_upload_size=0.5,
)

    if st.button("Simpan"):

        if not file_dokumen or not judul or not nomor:
            st.error("Lengkapi semua data!")

        elif file_dokumen.size > 512000:
            st.error(
                "🚨 Gagal: Ukuran file terlalu besar. "
                "Batas maksimal adalah 500 KB."
            )

        else:

            with st.spinner("Sedang memproses..."):

                file_bytes = file_dokumen.getvalue()

                teks_putusan = ""

                if file_dokumen.name.lower().endswith(".pdf"):
                    teks_putusan = extract_pdf_text(
                        file_bytes
                    )

                if not teks_putusan:

                    extension = (
                        Path(file_dokumen.name)
                        .suffix
                        .upper()
                    )

                    teks_putusan = (
                        f"Dokumen "
                        f"{extension.lstrip('.') or 'FILE'} "
                        "tersimpan di Storage."
                    )

                nama_file_aman = (
                    file_dokumen
                    .name
                    .replace(" ", "_")
                )

                file_path = (
                    f"{ROOT_PATH}/"
                    f"{nama_file_aman}"
                )

                content_type = (
                    file_dokumen.type
                    or safe_mime(file_dokumen.name)
                )

                try:

                    supabase.storage.from_(
                        BUCKET
                    ).upload(
                        path=file_path,
                        file=file_bytes,
                        file_options={
                            "content-type": content_type,
                            "upsert": "true",
                        },
                    )

                    file_url = (
                        supabase
                        .storage
                        .from_(BUCKET)
                        .get_public_url(file_path)
                    )

                    data = {
                        "judul": judul,
                        "nomor": nomor,
                        "file_url": file_url,
                        "isi_teks": teks_putusan,
                        "tags": kasus_posisi,
                    }

                    (
                        supabase
                        .table("putusan")
                        .insert(data)
                        .execute()
                    )

                    st.success(
                        "✅ Dokumen berhasil diupload "
                        "dan dimasukkan ke mesin pencarian."
                    )

                except Exception as e:

                    st.error(
                        "❌ Gagal mengupload dokumen."
                    )

                    st.code(str(e))


# =========================================================
# 6. SINKRONISASI STORAGE
# =========================================================

elif choice == "Sinkronisasi Storage":

    st.subheader("🔄 Sinkronisasi File Storage")

    st.info(
        "Fitur ini mendaftarkan file yang sudah ada "
        "di Supabase Storage ke tabel 'putusan'. "
        "File asli tidak dihapus dan tidak di-upload ulang."
    )

    st.write(
        f"Lokasi yang diperiksa: "
        f"`{BUCKET}/{ROOT_PATH}/`"
    )

    if st.button(
        "🔄 Sinkronkan File Storage"
    ):

        with st.spinner(
            "Membaca file Storage..."
        ):

            try:

                storage_files = (
                    list_all_storage_files()
                )

                existing_paths = (
                    get_existing_paths_from_database()
                )

                added_count = 0
                skipped_count = 0
                failed_count = 0

                for file_path in storage_files:

                    # Sudah terdaftar → jangan dibuat lagi
                    if file_path in existing_paths:

                        skipped_count += 1
                        continue

                    file_name = (
                        Path(file_path).name
                    )

                    extension = (
                        Path(file_name)
                        .suffix
                        .lower()
                    )

                    judul_otomatis = (
                        clean_title(file_name)
                    )

                    nomor_otomatis = (
                        extract_case_number(
                            file_name
                        )
                    )

                    tags_otomatis = (
                        build_tags(
                            file_name,
                            extension
                        )
                    )

                    isi_teks = ""

                    # -------------------------------------
                    # PDF → ekstraksi teks
                    # -------------------------------------

                    if extension == ".pdf":

                        try:

                            file_bytes = (
                                get_file_bytes(
                                    file_path
                                )
                            )

                            isi_teks = (
                                extract_pdf_text(
                                    file_bytes
                                )
                            )

                        except Exception:

                            isi_teks = ""

                    # -------------------------------------
                    # Fallback
                    # -------------------------------------

                    if not isi_teks:

                        tipe = (
                            extension
                            .lstrip(".")
                            .upper()
                            or "DOKUMEN"
                        )

                        isi_teks = (
                            f"File {tipe} yang tersimpan "
                            "di Supabase Storage."
                        )

                    try:

                        file_url = (
                            supabase
                            .storage
                            .from_(BUCKET)
                            .get_public_url(
                                file_path
                            )
                        )

                        data = {
                            "judul": judul_otomatis,
                            "nomor": nomor_otomatis,
                            "file_url": file_url,
                            "isi_teks": isi_teks,
                            "tags": tags_otomatis,
                        }

                        (
                            supabase
                            .table("putusan")
                            .insert(data)
                            .execute()
                        )

                        existing_paths.add(
                            file_path
                        )

                        added_count += 1

                    except Exception:

                        failed_count += 1

                # -----------------------------------------
                # HASIL
                # -----------------------------------------

                st.success(
                    "✅ Sinkronisasi selesai!"
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Total File Storage",
                        len(storage_files)
                    )

                with col2:

                    st.metric(
                        "File Baru",
                        added_count
                    )

                with col3:

                    st.metric(
                        "Sudah Terdaftar",
                        skipped_count
                    )

                if failed_count > 0:

                    st.warning(
                        f"⚠️ {failed_count} file gagal "
                        "didaftarkan."
                    )

                else:

                    st.caption(
                        "Tidak ada file yang gagal diproses."
                    )

                # SENGAJA tidak menampilkan nama file
                if skipped_count > 0:

                    st.info(
                        f"ℹ️ {skipped_count} file sudah "
                        "terdaftar di database."
                    )

                if added_count > 0:

                    st.success(
                        f"✅ {added_count} file baru "
                        "berhasil ditambahkan ke database."
                    )

            except Exception as e:

                st.error(
                    "❌ Sinkronisasi gagal."
                )

                st.code(str(e))


# =========================================================
# 7. CARI PUTUSAN
# =========================================================

else:

    st.subheader(
        "Pencarian Putusan (Deep Search)"
    )

    query = st.text_input(
        "Masukkan kata kunci..."
    )

    if query:

        query = query.strip()

        if query:

            try:

                pattern = f"%{query}%"

                # -----------------------------------------
                # Pencarian terpisah
                # Tidak memakai .or_()
                # -----------------------------------------

                hasil_judul = (
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike(
                        "judul",
                        pattern
                    )
                    .execute()
                )

                hasil_nomor = (
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike(
                        "nomor",
                        pattern
                    )
                    .execute()
                )

                hasil_isi = (
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike(
                        "isi_teks",
                        pattern
                    )
                    .execute()
                )

                hasil_tags = (
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike(
                        "tags",
                        pattern
                    )
                    .execute()
                )

                # -----------------------------------------
                # Gabungkan
                # -----------------------------------------

                semua_data = []

                semua_data.extend(
                    hasil_judul.data or []
                )

                semua_data.extend(
                    hasil_nomor.data or []
                )

                semua_data.extend(
                    hasil_isi.data or []
                )

                semua_data.extend(
                    hasil_tags.data or []
                )

                # -----------------------------------------
                # Hilangkan duplikat
                # -----------------------------------------

                hasil_unik = []
                seen = set()

                for item in semua_data:

                    item_id = item.get("id")

                    if item_id is None:

                        item_id = (
                            item.get(
                                "file_url",
                                ""
                            ),
                            item.get(
                                "judul",
                                ""
                            ),
                            item.get(
                                "nomor",
                                ""
                            ),
                        )

                    if item_id not in seen:

                        seen.add(item_id)
                        hasil_unik.append(item)

                # -----------------------------------------
                # HASIL PENCARIAN
                # -----------------------------------------

                if hasil_unik:

                    st.success(
                        f"Ditemukan "
                        f"{len(hasil_unik)} putusan."
                    )

                    for item in hasil_unik:

                        judul_hasil = (
                            item.get("judul")
                            or "Tanpa Judul"
                        )

                        nomor_hasil = (
                            item.get("nomor")
                            or "-"
                        )

                        st.write(
                            f"### {judul_hasil}"
                        )

                        st.write(
                            f"**Nomor:** {nomor_hasil}"
                        )

                        if item.get("tags"):

                            st.info(
                                f"📝 {item['tags']}"
                            )

                        file_url = (
                            item.get("file_url")
                        )

                        if file_url:

                            try:

                                path_str = (
                                    storage_path_from_url(
                                        file_url
                                    )
                                )

                                if not path_str:

                                    raise ValueError(
                                        "Path file tidak dapat "
                                        "dibaca dari file_url."
                                    )

                                file_bytes = (
                                    get_file_bytes(
                                        path_str
                                    )
                                )

                                nama_download = (
                                    Path(
                                        path_str
                                    ).name
                                )

                                mime = safe_mime(
                                    nama_download
                                )

                                st.download_button(
                                    label="💾 Download Dokumen",
                                    data=file_bytes,
                                    file_name=nama_download,
                                    mime=mime,
                                    key=(
                                        "download_"
                                        f"{item.get('id', path_str)}"
                                    ),
                                )

                            except Exception as e:

                                st.error(
                                    "❌ Gagal menyiapkan "
                                    "file download."
                                )

                                st.code(
                                    str(e)
                                )

                        else:

                            st.warning(
                                "⚠️ File dokumen "
                                "tidak tersedia."
                            )

                        st.divider()

                else:

                    st.info(
                        "🔎 Dokumen tidak ditemukan."
                    )

            except Exception as e:

                st.error(
                    "❌ Terjadi kesalahan "
                    "saat pencarian."
                )

                st.code(
                    str(e)
                )

        else:

            st.info(
                "Masukkan kata kunci pencarian."
            )
