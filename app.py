import streamlit as st
from supabase import create_client, Client
import PyPDF2
import mimetypes
import io
import re
from pathlib import Path as FilePath
from urllib.parse import urlparse, unquote


# =========================================================
# KONFIGURASI
# =========================================================

SUPABASE_URL = "https://fymgslpozaruhtbtbbre.supabase.co"
SUPABASE_BUCKET = "dokumen-putusan"
SUPABASE_ROOT = "public"

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("SUPABASE_KEY belum diatur di Streamlit Secrets.")
    st.stop()

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

st.set_page_config(
    page_title="Bank Data Putusan Menarik",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
    :root {
        --ink: #172033;
        --muted: #667085;
        --line: #e5e7eb;
        --soft: #f8fafc;
        --panel: #ffffff;
        --accent: #1f4b7a;
        --accent-soft: #eef4fb;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }

    .brand {
        border-bottom: 1px solid var(--line);
        padding-bottom: 1.15rem;
        margin-bottom: 1.4rem;
    }

    .brand-title {
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--ink);
        margin-bottom: 0.25rem;
    }

    .brand-subtitle {
        color: var(--muted);
        font-size: 0.95rem;
    }

    .hero {
        background: linear-gradient(
            135deg,
            #f8fafc 0%,
            #eef4fb 100%
        );
        border: 1px solid #dbe4ef;
        border-radius: 16px;
        padding: 2rem 2rem 1.65rem 2rem;
        margin-bottom: 1.4rem;
    }

    .hero-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 0.45rem;
        letter-spacing: -0.02em;
    }

    .hero-copy {
        color: var(--muted);
        font-size: 0.98rem;
        margin-bottom: 1.2rem;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 10px;
        min-height: 2.9rem;
        border: 1px solid #cfd6df;
    }

    div[data-testid="stSelectbox"] > div > div {
        border-radius: 10px;
    }

    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 9px;
        border: 1px solid #b8c4d2;
        background: #ffffff;
        color: var(--ink);
        font-weight: 600;
    }

    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        border-color: var(--accent);
        color: var(--accent);
    }

    .result-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.2rem 1.25rem 1.1rem 1.25rem;
        margin: 0 0 1rem 0;
        box-shadow: 0 2px 8px rgba(16, 24, 40, 0.035);
    }

    .result-number {
        color: var(--accent);
        font-size: 0.86rem;
        font-weight: 700;
        letter-spacing: 0.015em;
        margin-bottom: 0.35rem;
    }

    .result-title {
        color: var(--ink);
        font-size: 1.18rem;
        font-weight: 700;
        line-height: 1.42;
        margin-bottom: 0.55rem;
    }

    .meta {
        color: var(--muted);
        font-size: 0.88rem;
        margin-bottom: 0.7rem;
    }

    .tag {
        display: inline-block;
        padding: 0.32rem 0.58rem;
        margin: 0 0.35rem 0.35rem 0;
        background: var(--accent-soft);
        border: 1px solid #d9e5f3;
        border-radius: 999px;
        color: var(--accent);
        font-size: 0.74rem;
        font-weight: 600;
    }

    .summary {
        color: #344054;
        font-size: 0.94rem;
        line-height: 1.7;
        margin-top: 0.35rem;
        margin-bottom: 1rem;
    }

    .section-title {
        color: var(--ink);
        font-size: 1.05rem;
        font-weight: 700;
        margin: 1.3rem 0 0.75rem 0;
    }

    .metric-box {
        border: 1px solid var(--line);
        background: var(--panel);
        border-radius: 12px;
        padding: 0.9rem 1rem;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.78rem;
        margin-bottom: 0.2rem;
    }

    .metric-value {
        color: var(--ink);
        font-size: 1.25rem;
        font-weight: 700;
    }

    .info-panel {
        border: 1px solid var(--line);
        border-radius: 12px;
        background: #fafbfc;
        padding: 1rem 1.05rem;
        color: #475467;
        line-height: 1.65;
    }

    section[data-testid="stSidebar"] {
        border-right: 1px solid var(--line);
    }

    /* File uploader: usahakan tidak menonjolkan teks bawaan */
    .st-key-upload_putusan [data-testid*="FileUploaderDropzoneInstructions"] {
        font-size: 0 !important;
    }

    .st-key-upload_putusan [data-testid*="FileUploaderDropzoneInstructions"] * {
        font-size: 0 !important;
        line-height: 0 !important;
        visibility: hidden !important;
    }

    .st-key-upload_putusan [data-testid*="FileUploaderDropzoneInstructions"]::after {
        content: "Maksimal 500 KB per file";
        display: block !important;
        font-size: 0.75rem !important;
        line-height: 1.2 !important;
        color: rgba(49, 51, 63, 0.60) !important;
        visibility: visible !important;
        margin-top: 2px !important;
    }

    .footer-note {
        color: #98a2b3;
        font-size: 0.78rem;
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--line);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# FUNGSI BANTU
# =========================================================

def clean_title(file_name: str) -> str:
    stem = FilePath(file_name).stem
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem)
    return stem.strip()


def safe_mime(file_name: str) -> str:
    mime = mimetypes.guess_type(file_name)[0]
    if mime:
        return mime

    ext = FilePath(file_name).suffix.lower()

    if ext == ".rtf":
        return "application/rtf"
    if ext == ".doc":
        return "application/msword"
    if ext == ".docx":
        return (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    if ext == ".pdf":
        return "application/pdf"

    return "application/octet-stream"


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages).strip()
    except Exception:
        return ""


def case_number_from_name(file_name: str) -> str:
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


def tags_from_name(file_name: str) -> str:
    stem = FilePath(file_name).stem
    words = re.split(r"[^A-Za-z0-9]+", stem)
    words = [w.lower() for w in words if w]

    seen = set()
    result = []

    for word in words:
        if word not in seen:
            seen.add(word)
            result.append(word)

    return ", ".join(result[:60])


def storage_path_from_url(file_url: str) -> str:
    if not file_url:
        return ""

    parsed = urlparse(file_url)

    markers = [
        f"/object/public/{SUPABASE_BUCKET}/",
        f"/object/{SUPABASE_BUCKET}/",
        f"/object/sign/{SUPABASE_BUCKET}/",
    ]

    for marker in markers:
        if marker in parsed.path:
            return unquote(
                parsed.path.split(marker, 1)[1]
            )

    return ""


def list_all_storage_files(root_path: str = SUPABASE_ROOT):
    storage = supabase.storage.from_(SUPABASE_BUCKET)
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

                if metadata is not None or item_id is not None:
                    files.append(full_path)
                else:
                    walk(full_path)

            if len(items) < limit:
                break

            offset += len(items)

    walk(root_path)
    return files


def existing_file_paths() -> set[str]:
    existing = set()
    offset = 0
    limit = 1000

    while True:
        response = (
            supabase
            .table("putusan")
            .select("id,file_url")
            .range(offset, offset + limit - 1)
            .execute()
        )

        rows = response.data or []

        for row in rows:
            path = storage_path_from_url(
                row.get("file_url", "")
            )
            if path:
                existing.add(path)

        if len(rows) < limit:
            break

        offset += limit

    return existing


def format_tags(raw: str) -> str:
    if not raw:
        return ""

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return ""

    return "".join(
        f'<span class="tag">{p}</span>'
        for p in parts[:12]
    )


def truncate(text: str, limit: int = 320) -> str:
    if not text:
        return ""

    clean = " ".join(text.split())

    if len(clean) <= limit:
        return clean

    return clean[:limit].rstrip() + "..."


def download_supabase_file(file_url: str):
    path = storage_path_from_url(file_url)

    if not path:
        raise ValueError("Lokasi dokumen tidak dapat dibaca.")

    data = (
        supabase
        .storage
        .from_(SUPABASE_BUCKET)
        .download(path)
    )

    name = FilePath(path).name
    return data, name, safe_mime(name)


# =========================================================
# BRAND
# =========================================================

st.markdown(
    """
    <div class="brand">
        <div class="brand-title">BANK DATA PUTUSAN MENARIK</div>
        <div class="brand-subtitle">
            Basis data putusan untuk penelusuran isu, pertimbangan,
            dan temuan hukum.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown(
    "### Navigasi"
)

choice = st.sidebar.radio(
    "Menu",
    [
        "Pencarian Putusan",
        "Tambah Putusan",
        "Sinkronisasi Storage",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Bank Data Putusan Menarik"
)
st.sidebar.caption(
    "Versi aplikasi internal"
)


# =========================================================
# PENCARIAN
# =========================================================

if choice == "Pencarian Putusan":

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">Temukan Putusan yang Relevan</div>
            <div class="hero-copy">
                Cari berdasarkan nomor perkara, judul, isu hukum,
                ringkasan, atau kata kunci.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Pencarian",
        placeholder="Nomor perkara, isu hukum, broken marriage, khul'i, verstek, dan sebagainya",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        mode = st.selectbox(
            "Ruang pencarian",
            [
                "Semua bidang",
                "Judul",
                "Nomor perkara",
                "Isi putusan",
                "Kata kunci",
            ],
        )

    with col2:
        sort_order = st.selectbox(
            "Urutan",
            [
                "Terbaru ditampilkan",
                "Judul A–Z",
                "Nomor perkara",
            ],
        )

    if query.strip():

        term = query.strip()
        pattern = f"%{term}%"

        try:
            if mode == "Judul":
                responses = [
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("judul", pattern)
                    .execute()
                ]
            elif mode == "Nomor perkara":
                responses = [
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("nomor", pattern)
                    .execute()
                ]
            elif mode == "Isi putusan":
                responses = [
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("isi_teks", pattern)
                    .execute()
                ]
            elif mode == "Kata kunci":
                responses = [
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("tags", pattern)
                    .execute()
                ]
            else:
                responses = [
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("judul", pattern)
                    .execute(),
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("nomor", pattern)
                    .execute(),
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("isi_teks", pattern)
                    .execute(),
                    supabase
                    .table("putusan")
                    .select("*")
                    .ilike("tags", pattern)
                    .execute(),
                ]

            data = []
            seen = set()

            for response in responses:
                for item in (response.data or []):
                    key = item.get("id")
                    if key is None:
                        key = (
                            item.get("file_url", ""),
                            item.get("judul", ""),
                            item.get("nomor", ""),
                        )

                    if key not in seen:
                        seen.add(key)
                        data.append(item)

            if sort_order == "Judul A–Z":
                data.sort(
                    key=lambda x: (x.get("judul") or "").lower()
                )
            elif sort_order == "Nomor perkara":
                data.sort(
                    key=lambda x: (x.get("nomor") or "").lower()
                )
            else:
                data.reverse()

            st.markdown(
                f'<div class="section-title">{len(data)} hasil ditemukan</div>',
                unsafe_allow_html=True,
            )

            if data:

                for item in data:

                    judul = item.get("judul") or "Tanpa Judul"
                    nomor = item.get("nomor") or "Nomor perkara tidak dicatat"
                    tags = item.get("tags") or ""
                    isi = item.get("isi_teks") or ""

                    st.markdown(
                        f"""
                        <div class="result-card">
                            <div class="result-number">{nomor}</div>
                            <div class="result-title">{judul}</div>
                            <div class="meta">
                                Bank Data Putusan Menarik
                            </div>
                            <div>
                                {format_tags(tags)}
                            </div>
                            <div class="summary">
                                {truncate(isi)}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    file_url = item.get("file_url")

                    if file_url:
                        try:
                            file_bytes, file_name, mime = (
                                download_supabase_file(
                                    file_url
                                )
                            )

                            st.download_button(
                                "Unduh Putusan",
                                data=file_bytes,
                                file_name=file_name,
                                mime=mime,
                                key=f"download_{item.get('id', file_url)}",
                                use_container_width=False,
                            )
                        except Exception:
                            st.warning(
                                "Dokumen tidak dapat disiapkan untuk diunduh."
                            )

            else:

                st.markdown(
                    """
                    <div class="info-panel">
                        Tidak ditemukan putusan yang sesuai dengan
                        kata kunci tersebut.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        except Exception as exc:

            st.error(
                "Pencarian gagal dijalankan."
            )
            st.code(str(exc))

    else:

        st.markdown(
            """
            <div class="section-title">Cara menggunakan pencarian</div>
            <div class="info-panel">
                Masukkan nomor perkara, isu hukum, kata kunci,
                atau istilah yang terdapat dalam pertimbangan putusan.
                Sistem akan menelusuri judul, nomor perkara, isi teks,
                dan kata kunci.
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# TAMBAH PUTUSAN
# =========================================================

elif choice == "Tambah Putusan":

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">Tambah Putusan Baru</div>
            <div class="hero-copy">
                Masukkan metadata dan dokumen putusan.
                Dokumen dianjurkan telah dianonimkan sebelum diunggah.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        judul = st.text_input(
            "Judul Putusan"
        )

    with col2:
        nomor = st.text_input(
            "Nomor Putusan"
        )

    kasus_posisi = st.text_area(
        "Ringkasan Kasus Posisi / Kata Kunci",
        height=140,
        placeholder=(
            "Contoh: broken marriage, khul'i, "
            "taklik talak, pisah rumah, verstek."
        ),
    )

    file_dokumen = st.file_uploader(
        "Dokumen putusan",
        type=["pdf", "doc", "docx", "rtf"],
        max_upload_size=1,
        key="upload_putusan",
    )

    st.caption(
        "Batas aplikasi: 500 KB per file."
    )

    if st.button(
        "Simpan Putusan",
        use_container_width=False,
    ):

        if not judul or not nomor or not file_dokumen:
            st.error(
                "Judul, nomor perkara, dan dokumen wajib diisi."
            )

        elif file_dokumen.size > 512000:
            st.error(
                "Ukuran dokumen melebihi batas 500 KB."
            )

        else:

            file_bytes = file_dokumen.getvalue()
            extension = FilePath(
                file_dokumen.name
            ).suffix.lower()

            with st.spinner(
                "Menyimpan putusan..."
            ):

                try:

                    text = ""

                    if extension == ".pdf":
                        text = extract_pdf_text(
                            file_bytes
                        )

                    if not text:
                        text = (
                            f"Dokumen {extension.lstrip('.') or 'file'} "
                            "tersimpan dalam Bank Data Putusan Menarik."
                        )

                    file_name_safe = (
                        file_dokumen.name.replace(
                            " ",
                            "_"
                        )
                    )

                    path = (
                        f"{SUPABASE_ROOT}/"
                        f"{file_name_safe}"
                    )

                    content_type = (
                        file_dokumen.type
                        or safe_mime(file_dokumen.name)
                    )

                    supabase.storage.from_(
                        SUPABASE_BUCKET
                    ).upload(
                        path=path,
                        file=file_bytes,
                        file_options={
                            "content-type": content_type,
                            "upsert": "true",
                        },
                    )

                    file_url = (
                        supabase
                        .storage
                        .from_(SUPABASE_BUCKET)
                        .get_public_url(path)
                    )

                    row = {
                        "judul": judul,
                        "nomor": nomor,
                        "file_url": file_url,
                        "isi_teks": text,
                        "tags": kasus_posisi,
                    }

                    (
                        supabase
                        .table("putusan")
                        .insert(row)
                        .execute()
                    )

                    st.success(
                        "Putusan berhasil disimpan."
                    )

                except Exception as exc:

                    st.error(
                        "Putusan gagal disimpan."
                    )
                    st.code(str(exc))


# =========================================================
# SINKRONISASI
# =========================================================

else:

    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">Sinkronisasi Storage</div>
            <div class="hero-copy">
                Mendaftarkan dokumen yang sudah ada di Supabase Storage
                ke dalam indeks pencarian tanpa menghapus file lama.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="info-panel">
            Fungsi ini hanya membaca daftar file pada
            <strong>dokumen-putusan/public</strong> dan membuat
            metadata pada tabel putusan jika belum terdaftar.
            Nama file tidak ditampilkan kepada pengguna.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    if st.button(
        "Mulai Sinkronisasi",
        use_container_width=False,
    ):

        with st.spinner(
            "Memeriksa Storage..."
        ):

            try:

                files = list_all_storage_files()
                existing = existing_file_paths()

                added = 0
                skipped = 0
                failed = 0

                for file_path in files:

                    if file_path in existing:
                        skipped += 1
                        continue

                    file_name = FilePath(
                        file_path
                    ).name

                    extension = FilePath(
                        file_name
                    ).suffix.lower()

                    text = ""

                    if extension == ".pdf":

                        try:
                            file_bytes = (
                                supabase
                                .storage
                                .from_(SUPABASE_BUCKET)
                                .download(file_path)
                            )

                            text = extract_pdf_text(
                                file_bytes
                            )

                        except Exception:
                            text = ""

                    if not text:
                        text = (
                            f"File {extension.lstrip('.') or 'dokumen'} "
                            "yang tersimpan pada Supabase Storage."
                        )

                    path_url = (
                        supabase
                        .storage
                        .from_(SUPABASE_BUCKET)
                        .get_public_url(
                            file_path
                        )
                    )

                    row = {
                        "judul": clean_title(file_name),
                        "nomor": case_number_from_name(file_name),
                        "file_url": path_url,
                        "isi_teks": text,
                        "tags": tags_from_name(file_name),
                    }

                    try:

                        (
                            supabase
                            .table("putusan")
                            .insert(row)
                            .execute()
                        )

                        existing.add(
                            file_path
                        )

                        added += 1

                    except Exception:
                        failed += 1

                c1, c2, c3 = st.columns(3)

                with c1:
                    st.markdown(
                        f"""
                        <div class="metric-box">
                            <div class="metric-label">Total file</div>
                            <div class="metric-value">{len(files)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with c2:
                    st.markdown(
                        f"""
                        <div class="metric-box">
                            <div class="metric-label">File baru</div>
                            <div class="metric-value">{added}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with c3:
                    st.markdown(
                        f"""
                        <div class="metric-box">
                            <div class="metric-label">Sudah terdaftar</div>
                            <div class="metric-value">{skipped}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if failed:
                    st.warning(
                        f"{failed} file tidak dapat didaftarkan."
                    )
                else:
                    st.success(
                        "Sinkronisasi selesai."
                    )

            except Exception as exc:

                st.error(
                    "Sinkronisasi gagal dijalankan."
                )
                st.code(str(exc))


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer-note">
        Bank Data Putusan Menarik
    </div>
    """,
    unsafe_allow_html=True,
)
