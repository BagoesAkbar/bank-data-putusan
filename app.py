import streamlit as st
from supabase import create_client, Client
import PyPDF2
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse, unquote
import io


# =========================================================
# 1. KONFIGURASI SUPABASE
# =========================================================

URL = "https://fymgslpozaruhtbtbbre.supabase.co"

# Lebih aman menggunakan Streamlit Secrets.
# Pada Streamlit Cloud:
# Settings > Secrets
#
# Isi:
# SUPABASE_KEY = "KEY_ANDA"
#
try:
    KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    KEY = "PASTE_PUBLISHABLE_KEY_ANDA"

if KEY == "PASTE_PUBLISHABLE_KEY_ANDA":
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.stop()

supabase: Client = create_client(URL, KEY)

BUCKET = "dokumen-putusan"
ROOT_PATH = "public"


# =========================================================
# 2. JUDUL APLIKASI
# =========================================================

st.title("Bank Data Putusan Menarik")


# =========================================================
# 3. FUNGSI BANTU
# =========================================================

def clean_title(file_name: str) -> str:
    """
    Mengubah nama file menjadi judul yang lebih mudah dibaca.
    Contoh:
    449_Pdt.G_2026_PA.Twg_file.pdf
    ->
    449 Pdt.G 2026 PA.Twg file
    """
    stem = Path(file_name).stem

    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem)

    return stem.strip()


def extract_case_number(file_name: str) -> str:
    """
    Mencoba membaca nomor perkara dari nama file.
    Tidak mengarang nomor bila pola tidak jelas.
    """

    patterns = [
        r"(?i)(\d+)[_\- ]+(Pdt\.G)[_\- ]+(\d{4})[_\- ]+([A-Z]{2,}(?:\.[A-Za-z0-9]+)+)",
        r"(?i)(\d+)[_\- ]+(Pdt\.G)[_\- ]+(\d{4})[_\- ]+([A-Z]{2,})",
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


def build_tags(file_name: str, ext: str) -> str:
    """
    Membuat kata kunci dasar dari nama file.
    """

    stem = Path(file_name).stem

    words = re.split(
        r"[^A-Za-z0-9]+",
        stem
    )

    words = [
        word.lower()
        for word in words
        if word
    ]

    tags = [
        "storage sync"
    ]

    if ext:
        tags.append(
            ext.lstrip(".").lower()
        )

    tags.extend(words)

    # Hilangkan duplikat
    result = []
    seen = set()

    for tag in tags:

        if tag not in seen:

            seen.add(tag)
            result.append(tag)

    return ", ".join(result[:80])


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Membaca teks dari PDF.
    Kalau PDF gagal dibaca, tidak menggagalkan proses sync.
    """

    try:

        reader = PyPDF2.PdfReader(
            io.BytesIO(file_bytes)
        )

        pages = []

        for page in reader.pages:

            text_page = page.extract_text()

            if text_page:

                pages.append(text_page)

        return "\n".join(pages).strip()

    except Exception:

        return ""


def list_all_storage_files(
    storage,
    root_path: str = ROOT_PATH
) -> list[str]:

    """
    Membaca semua file di dalam public/
    termasuk subfolder jika ada.
    """

    files = []

    def walk(path: str):

        offset = 0
        page_size = 1000

        while True:

            items = storage.list(
                path,
                {
                    "limit": page_size,
                    "offset": offset,
                    "sortBy": {
                        "column": "name",
                        "order": "asc"
                    },
                },
            ) or []

            if not items:
                break

            for item in items:

                name = item.get("name")

                if not name:
                    continue

                full_path = f"{path}/{name}"

                metadata = item.get("metadata")

                # File biasanya mempunyai metadata/id.
                is_file = (
                    metadata is not None
                    or item.get("id") is not None
                )

                if is_file:

                    files.append(full_path)

                else:

                    walk(full_path)

            if len(items) < page_size:
                break

            offset += len(items)

    walk(root_path)

    return files


def storage_path_from_url(
    file_url: str
) -> str:

    """
    Mengambil path file dari URL Supabase.
    """

    if not file_url:
        return ""

    parsed = urlparse(file_url)

    marker = (
        f"/object/public/{BUCKET}/"
    )

    if marker in parsed.path:

        return unquote(
            parsed.path.split(
                marker,
                1
            )[1]
        )

    # Fallback URL lama
    marker2 = f"{BUCKET}/"

    if marker2 in parsed.path:

        return unquote(
            parsed.path.split(
                marker2,
                1
            )[1]
        )

    return ""


def fetch_existing_file_paths() -> set[str]:

    """
    Membaca file_url yang sudah ada
    di tabel putusan agar tidak membuat
    duplikasi ketika Sync ditekan lagi.
    """

    existing_paths = set()

    offset = 0
    page_size = 1000

    while True:

        response = (
            supabase
            .table("putusan")
            .select("id,file_url")
            .range(
                offset,
                offset + page_size - 1
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

        if len(rows) < page_size:

            break

        offset += page_size

    return existing_paths


def get_file_bytes(
    file_path: str
) -> bytes:

    """
    Mengambil bytes file dari Storage.
    """

    return (
        supabase
        .storage
        .from_(BUCKET)
        .download(file_path)
    )


def escape_like(value: str) -> str:

    """
    Mencegah % dan _ menjadi wildcard
    ketika user melakukan pencarian.
    """

    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


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
    menu
)


# =========================================================
# 5. UPLOAD PUTUSAN
# =========================================================

if choice == "Upload Putusan":

    st.subheader(
        "Tambah Putusan Baru (Anonim)"
    )

    judul = st.text_input(
        "Judul Putusan"
    )

    nomor = st.text_input(
        "Nomor Putusan"
    )

    kasus_posisi = st.text_area(
        "Ringkasan Kasus Posisi / Kata Kunci Bebas"
    )

    file_dokumen = st.file_uploader(
        "Upload putusan (Anonimisasi dianjurkan)",
        type=[
            "pdf",
            "doc",
            "docx",
            "rtf"
        ]
    )

    if st.button("Simpan"):

        if not (
            file_dokumen
            and judul
            and nomor
        ):

            st.error(
                "Lengkapi semua data!"
            )

        elif file_dokumen.size > 512000:

            st.error(
                "🚨 Gagal: Ukuran file Anda terlalu besar! "
                "Batas maksimal adalah 500 KB."
            )

        else:

            with st.spinner(
                "Sedang memproses..."
            ):

                teks_putusan = ""

                if file_dokumen.name.lower().endswith(
                    ".pdf"
                ):

                    teks_putusan = extract_pdf_text(
                        file_dokumen.getvalue()
                    )

                if not teks_putusan:

                    ext = (
                        Path(file_dokumen.name)
                        .suffix
                        .upper()
                        .lstrip(".")
                    )

                    teks_putusan = (
                        f"Dokumen {ext or 'FILE'} "
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
                    or mimetypes.guess_type(
                        file_dokumen.name
                    )[0]
                    or "application/octet-stream"
                )

                try:

                    supabase.storage.from_(
                        BUCKET
                    ).upload(
                        path=file_path,
                        file=file_dokumen.getvalue(),
                        file_options={
                            "content-type": content_type,
                            "upsert": "true",
                        },
                    )

                    file_url = (
                        supabase
                        .storage
                        .from_(BUCKET)
                        .get_public_url(
                            file_path
                        )
                    )

                    data = {
                        "judul": judul,
                        "nomor": nomor,
                        "file_url": file_url,
                        "isi_teks": teks_putusan,
                        "tags": kasus_posisi,
                    }

                    supabase.table(
                        "putusan"
                    ).insert(
                        data
                    ).execute()

                    st.success(
                        "✅ Dokumen berhasil diupload!"
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

    st.subheader(
        "🔄 Sinkronisasi File Storage"
    )

    st.info(
        "Fitur ini hanya mendaftarkan file yang "
        "sudah ada di Supabase Storage ke tabel "
        "'putusan'. File asli tidak dihapus dan "
        "tidak di-upload ulang."
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

                storage = (
                    supabase
                    .storage
                    .from_(BUCKET)
                )

                # -----------------------------------------
                # Ambil semua file Storage
                # -----------------------------------------

                storage_files = (
                    list_all_storage_files(
                        storage,
                        ROOT_PATH
                    )
                )

                # -----------------------------------------
                # Ambil file yang sudah ada di database
                # -----------------------------------------

                existing_paths = (
                    fetch_existing_file_paths()
                )

                added = []
                skipped = []
                failed = []

                # -----------------------------------------
                # Proses masing-masing file
                # -----------------------------------------

                for file_path in storage_files:

                    # -------------------------------------
                    # Kalau sudah ada → jangan duplikat
                    # -------------------------------------

                    if file_path in existing_paths:

                        skipped.append(
                            file_path
                        )

                        continue

                    file_name = (
                        Path(file_path).name
                    )

                    ext = (
                        Path(file_name)
                        .suffix
                        .lower()
                    )

                    # -------------------------------------
                    # Buat metadata otomatis
                    # -------------------------------------

                    title = clean_title(
                        file_name
                    )

                    nomor = extract_case_number(
                        file_name
                    )

                    tags = build_tags(
                        file_name,
                        ext
                    )

                    isi_teks = ""

                    # -------------------------------------
                    # PDF → ambil isi teks
                    # -------------------------------------

                    if ext == ".pdf":

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
                    # Jika tidak bisa ekstrak
                    # -------------------------------------

                    if not isi_teks:

                        tipe = (
                            ext
                            .lstrip(".")
                            .upper()
                            or "DOKUMEN"
                        )

                        isi_teks = (
                            f"File {tipe} "
                            "yang tersimpan "
                            "di Supabase Storage."
                        )

                    try:

                        # ---------------------------------
                        # URL publik file yang SUDAH ADA
                        # ---------------------------------

                        file_url = (
                            storage
                            .get_public_url(
                                file_path
                            )
                        )

                        # ---------------------------------
                        # Masukkan metadata ke tabel
                        # ---------------------------------

                        data = {
                            "judul": title,
                            "nomor": nomor,
                            "file_url": file_url,
                            "isi_teks": isi_teks,
                            "tags": tags,
                        }

                        (
                            supabase
                            .table("putusan")
                            .insert(data)
                            .execute()
                        )

                        added.append(
                            file_path
                        )

                        # Supaya file tersebut
                        # tidak diproses lagi dalam
                        # satu sesi sync.
                        existing_paths.add(
                            file_path
                        )

                    except Exception as e:

                        failed.append(
                            (
                                file_path,
                                str(e)
                            )
                        )

                # -----------------------------------------
                # HASIL SINKRONISASI
                # -----------------------------------------

                st.success(
                    "✅ Sinkronisasi selesai!"
                )

                st.metric(
                    "Total file Storage",
                    len(storage_files)
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "File Baru",
                        len(added)
                    )

                with col2:

                    st.metric(
                        "Sudah Terdaftar",
                        len(skipped)
                    )

                with col3:

                    st.metric(
                        "Gagal",
                        len(failed)
                    )

                # -----------------------------------------
                # File baru
                # -----------------------------------------

                if added:

                    st.write(
                        "### ✅ File yang ditambahkan"
                    )

                    for path in added:

                        st.write(
                            f"✅ `{path}`"
                        )

                # -----------------------------------------
# File yang sudah terdaftar
# -----------------------------------------

if skipped:

    st.info(
        f"ℹ️ {len(skipped)} file sudah terdaftar "
        "di database."
    )

                # -----------------------------------------
                # File gagal
                # -----------------------------------------

                if failed:

                    st.error(
                        "Beberapa file gagal "
                        "didaftarkan:"
                    )

                    for path, error in failed:

                        st.write(
                            f"❌ `{path}`"
                        )

                        st.code(error)

            except Exception as e:

                st.error(
                    "❌ Sinkronisasi gagal."
                )

                st.code(str(e))


# =========================================================
# 7. PENCARIAN PUTUSAN
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

        if not query:

            st.info(
                "Masukkan kata kunci pencarian."
            )

        else:

            try:

                pattern = (
                    f"%{escape_like(query)}%"
                )

                # -----------------------------------------
                # Pencarian terpisah
                # Tidak lagi menggunakan .or_()
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

                for response in [
                    hasil_judul,
                    hasil_nomor,
                    hasil_isi,
                    hasil_tags,
                ]:

                    semua_data.extend(
                        response.data or []
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

                        hasil_unik.append(
                            item
                        )

                # -----------------------------------------
                # Tampilkan
                # -----------------------------------------

                if hasil_unik:

                    st.success(
                        f"Ditemukan "
                        f"{len(hasil_unik)} putusan."
                    )

                    for item in hasil_unik:

                        st.write(
                            "### "
                            f"{item.get('judul') or 'Tanpa Judul'}"
                        )

                        st.write(
                            "**Nomor:** "
                            f"{item.get('nomor') or '-'}"
                        )

                        if item.get("tags"):

                            st.info(
                                f"📝 {item['tags']}"
                            )

                        file_url = (
                            item.get(
                                "file_url"
                            )
                        )

                        if file_url:

                            try:

                                path_str = (
                                    storage_path_from_url(
                                        file_url
                                    )
                                )

                                file_bytes = (
                                    get_file_bytes(
                                        path_str
                                    )
                                )

                                nama_download = (
                                    Path(path_str).name
                                )

                                mime = (
                                    mimetypes.guess_type(
                                        nama_download
                                    )[0]
                                    or "application/octet-stream"
                                )

                                st.download_button(
                                    label="💾 Download Dokumen",
                                    data=file_bytes,
                                    file_name=nama_download,
                                    mime=mime,
                                    key=(
                                        f"download_"
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
                    "saat melakukan pencarian."
                )

                st.code(
                    str(e)
                )
