                    )
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
                        seen.add(
                            item_id
                        )
                        hasil_unik.append(
                            item
                        )
                # -------------------------------------------------
                # HASIL PENCARIAN
                # -------------------------------------------------
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
                            f"**Nomor:** "
                            f"{nomor_hasil}"
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
                                mime = (
                                    safe_mime(
                                        nama_download
                                    )
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
