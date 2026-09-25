                            text = ""

                    if not text:

                        text = (
                            f"File "
                            f"{extension.lstrip('.') or 'dokumen'} "
                            "yang tersimpan pada "
                            "Supabase Storage."
                        )

                    file_url = (
                        supabase
                        .storage
                        .from_(
                            SUPABASE_BUCKET
                        )
                        .get_public_url(
                            file_path
                        )
                    )

                    row = {
                        "judul":
                            clean_title(
                                file_name
                            ),
                        "nomor":
                            case_number_from_name(
                                file_name
                            ),
                        "file_url":
                            file_url,
                        "isi_teks":
                            text,
                        "tags":
                            tags_from_name(
                                file_name
                            ),
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

                col1, col2, col3 = (
                    st.columns(3)
                )

                with col1:

                    st.metric(
                        "Total file",
                        len(files)
                    )

                with col2:

                    st.metric(
                        "File baru",
                        added
                    )

                with col3:

                    st.metric(
                        "Sudah terdaftar",
                        skipped
                    )

                if failed:

                    st.warning(
                        f"{failed} file tidak dapat "
                        "didaftarkan."
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
# BUILDER
# =========================================================

st.markdown(
    """
    <div class="builder">
        © 2026 Bagoes KA
    </div>
    """,
    unsafe_allow_html=True,
)
