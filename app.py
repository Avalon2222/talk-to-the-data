"""
app.py - Talk to the Data (Streamlit).

Jalankan:  streamlit run app.py

File ini hanya mengurus TAMPILAN dan status percakapan. Logika ada di src/:
katalog.py (data), query.py (query terstruktur), grafik.py (Plotly), alat.py (tools + prompt),
llm.py (klien API + loop tool calling).
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src import alat, grafik, katalog, llm, query

st.set_page_config(page_title="Talk to the Data", page_icon="💬", layout="wide")

CONTOH_PERTANYAAN = [
    "Provinsi mana yang belanja daerahnya paling besar di 2024? Tampilkan 10 teratas.",
    "Bagaimana tren rata-rata harga Bitcoin per tahun sejak 2020?",
    "Gempa M≥5 sebulan terakhir ada berapa, dan di mana saja? Tampilkan petanya.",
    "Which airlines own the sky over Indonesia right now?",
    "Data center terbesar di Indonesia ada di mana, dan siapa operatornya?",
    "Gunung api mana saja yang statusnya Siaga atau Awas?",
    "Bandingkan belanja militer Indonesia dengan negara-negara tetangga.",
    "Berapa BTC yang dipindahkan paus per hari, dibagi menurut pola transaksi?",
    "Di kota mana upah minimum paling lama untuk beli rumah seken, kalau nabung 30% gaji?",
    "Provinsi mana yang paling banyak titik apinya minggu ini?",
    "Which countries had the most conflict deaths in 2025?",
    "Bagaimana tren kapal yang melintasi Selat Malaka per bulan sejak 2019?",
    "Negara mana yang punya satelit militer paling banyak?",
    "Kawasan mana di Jabodetabek yang rata-rata PM2.5-nya paling tinggi?",
    "Negara mana yang paling sering memutus internet sejak 2016, dan apa pemicu utamanya?",
    "Kapan saja internet di Indonesia pernah diputus atau dibatasi, dan karena apa?",
]


# ---------------------------------------------------------------------------
# Konfigurasi LLM: secrets → override di sidebar (hanya untuk sesi ini)
# ---------------------------------------------------------------------------

def konfigurasi_secrets() -> dict:
    try:
        bagian = st.secrets.get("llm", {})
        return {"provider": bagian.get("provider", "groq"), "api_key": bagian.get("api_key", ""),
                "model": bagian.get("model", "") or None}
    except Exception:  # tidak ada secrets.toml sama sekali
        return {"provider": "groq", "api_key": "", "model": None}


def buat_klien(konf: dict) -> llm.Klien | None:
    if not konf["api_key"]:
        return None
    return llm.Klien(provider=konf["provider"], api_key=konf["api_key"], model=konf["model"])


def fmt_angka(x) -> str:
    if isinstance(x, float):
        return f"{x:,.2f}" if abs(x) < 1e6 else f"{x:,.0f}"
    if isinstance(x, int):
        return f"{x:,}"
    return str(x)


# ---------------------------------------------------------------------------
# Status percakapan
# ---------------------------------------------------------------------------

st.session_state.setdefault("tampil", [])        # pesan untuk layar: {"role", "content", "lampiran", "langkah"}
st.session_state.setdefault("riwayat_llm", [])   # pesan teks saja untuk konteks LLM
st.session_state.setdefault("pertanyaan_tertunda", None)
st.session_state.setdefault("kunci_sesi", "")


def bersihkan_percakapan() -> None:
    st.session_state["tampil"] = []
    st.session_state["riwayat_llm"] = []
    st.session_state["pertanyaan_tertunda"] = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

konf = konfigurasi_secrets()

with st.sidebar:
    st.title("💬 Talk to the Data")
    st.caption("*The data finally talks back.*")

    st.session_state.setdefault("halaman", "💬 Chat")
    halaman = st.segmented_control(
        "Page", ["💬 Chat", "🗂️ Datasets", "🧭 How it works"], key="halaman", label_visibility="collapsed",
    ) or "💬 Chat"
    mode_belajar = st.toggle("🎓 Learning mode", value=False, help="Tampilkan panggilan alat dan penjelasan di tiap jawaban")

    st.divider()
    st.markdown("**Ask something**")
    def pilih_contoh(teks: str) -> None:
        # Callback: dijalankan sebelum skrip diulang, jadi boleh mengubah nilai widget halaman.
        st.session_state["pertanyaan_tertunda"] = teks
        st.session_state["halaman"] = "💬 Chat"

    for i, contoh in enumerate(CONTOH_PERTANYAAN):
        st.button(contoh, key=f"contoh_{i}", width="stretch", on_click=pilih_contoh, args=(contoh,))

    st.divider()
    with st.expander("⚙️ Settings", expanded=not konf["api_key"]):
        if konf["api_key"]:
            st.success(f"API key dari secrets: {llm.PROVIDER[konf['provider']]['nama']}, model "
                       f"`{konf['model'] or llm.PROVIDER[konf['provider']]['model']}`.")
        else:
            st.warning("Belum ada API key di `.streamlit/secrets.toml`. Isi di bawah untuk sesi ini saja.")
        provider_sesi = st.selectbox("Provider", list(llm.PROVIDER), index=list(llm.PROVIDER).index(konf["provider"]),
                                     format_func=lambda p: llm.PROVIDER[p]["nama"])
        kunci_sesi = st.text_input("API key (session only)", type="password", value=st.session_state["kunci_sesi"],
                                   help="Tidak disimpan di mana pun; hilang saat tab ditutup. "
                                        f"Buat gratis di {llm.PROVIDER[provider_sesi]['url_kunci']}")
        st.session_state["kunci_sesi"] = kunci_sesi
        model_sesi = st.text_input("Model (optional)", value="", placeholder=llm.PROVIDER[provider_sesi]["model"])
        if kunci_sesi:
            konf = {"provider": provider_sesi, "api_key": kunci_sesi, "model": model_sesi or None}
        elif provider_sesi != konf["provider"]:
            st.caption("Provider berbeda dari secrets; isi API key-nya untuk memakainya.")
        st.caption(f"Key gratis: [Groq]({llm.PROVIDER['groq']['url_kunci']}) · [Gemini]({llm.PROVIDER['gemini']['url_kunci']})")

    if st.button("🧹 Clear chat", width="stretch"):
        bersihkan_percakapan()
        st.rerun()
    st.caption(f"{len(katalog.DATASET)} dataset dari {len(katalog.PROYEK)} proyek. Semua jawaban dihitung dari data, bukan dari ingatan model.")

klien = buat_klien(konf)
penyedia_alat = alat.Alat()


# ---------------------------------------------------------------------------
# Komponen tampilan
# ---------------------------------------------------------------------------

def tampilkan_lampiran(daftar: list[alat.Lampiran], kunci: str) -> None:
    for i, lamp in enumerate(daftar):
        if lamp.grafik:
            try:
                st.plotly_chart(grafik.buat(lamp.hasil, lamp.grafik), width="stretch", key=f"{kunci}_grafik_{i}")
            except grafik.GalatGrafik as e:
                st.caption(f"Grafik tidak bisa digambar: {e}")
    if not daftar:
        return
    with st.expander("📎 Sumber & data", expanded=False):
        for i, lamp in enumerate(daftar):
            st.markdown(
                f"**{lamp.judul_proyek}** · dataset `{lamp.dataset}` · "
                f"[Live app]({lamp.url_app}) · [Code]({lamp.url_repo})"
            )
            if lamp.hasil.empty:
                st.caption("Query tidak menghasilkan baris.")
                continue
            st.dataframe(lamp.hasil, width="stretch", hide_index=True, height=min(400, 40 + 35 * len(lamp.hasil)))
            st.download_button(
                "Download CSV", lamp.hasil.to_csv(index=False).encode("utf-8"),
                file_name=f"{lamp.dataset}_hasil.csv", mime="text/csv", key=f"{kunci}_unduh_{i}",
            )


def tampilkan_langkah(langkah: list[llm.Langkah], kunci: str) -> None:
    if not mode_belajar or not langkah:
        return
    with st.expander("🎓 Di balik layar: apa yang diminta model ke data", expanded=False):
        st.markdown(
            "Model tidak membaca CSV. Ia hanya tahu **nama dataset dan kolom** (dari prompt sistem), lalu "
            "mengirim spesifikasi JSON kecil ke alat `query_data`. Pandas yang menghitung; model hanya "
            "merangkai kalimat dari hasilnya. Ini yang biasa disebut *tool calling* atau *RAG terstruktur*."
        )
        for i, l in enumerate(langkah, 1):
            st.markdown(f"**Langkah {i}: `{l.alat}`**" + (" ❌ gagal, model mencoba lagi" if l.galat else ""))
            st.code(json.dumps(l.argumen, ensure_ascii=False, indent=2), language="json")
            st.caption("Yang dikirim balik ke model (dipotong):")
            st.code(l.teks_hasil[:600] + ("…" if len(l.teks_hasil) > 600 else ""), language="text")


def tampilkan_pesan(pesan: dict, kunci: str) -> None:
    with st.chat_message(pesan["role"], avatar="🧑" if pesan["role"] == "user" else "📊"):
        st.markdown(pesan["content"])
        if pesan["role"] == "assistant":
            tampilkan_lampiran(pesan.get("lampiran", []), kunci)
            tampilkan_langkah(pesan.get("langkah", []), kunci)


def pesan_galat(e: Exception) -> str:
    if isinstance(e, llm.KunciTidakValid):
        return (f"API key ditolak atau kosong. Buat key gratis di {llm.PROVIDER[konf['provider']]['url_kunci']} "
                "lalu isi di Settings (sidebar) atau di `.streamlit/secrets.toml`.")
    if isinstance(e, llm.BatasLaju):
        return f"{e} Tier gratis dibatasi per menit dan per hari; tunggu sebentar lalu kirim ulang."
    if isinstance(e, llm.GalatLLM):
        return f"Permintaan ke model gagal: {e}"
    return f"Terjadi kesalahan tak terduga ({type(e).__name__}): {e}"


def proses_pertanyaan(pertanyaan: str) -> None:
    st.session_state["tampil"].append({"role": "user", "content": pertanyaan})
    tampilkan_pesan(st.session_state["tampil"][-1], f"p{len(st.session_state['tampil'])}")

    with st.chat_message("assistant", avatar="📊"):
        if klien is None:
            st.error(pesan_galat(llm.KunciTidakValid("API key kosong.")))
            st.session_state["tampil"].pop()
            return
        with st.spinner("Membaca data…"):
            try:
                jawaban = llm.jawab(klien, alat.prompt_sistem(), st.session_state["riwayat_llm"], pertanyaan, penyedia_alat)
            except Exception as e:  # noqa: BLE001 - semua galat ditampilkan ke pengguna, app tidak boleh mati
                st.error(pesan_galat(e))
                st.session_state["tampil"].pop()
                return
        lampiran = [l.lampiran for l in jawaban.langkah if isinstance(l.lampiran, alat.Lampiran)]
        teks = jawaban.teks.strip() or "(Model tidak memberi jawaban teks.)"
        kunci = f"j{len(st.session_state['tampil'])}"
        st.markdown(teks)
        tampilkan_lampiran(lampiran, kunci)
        tampilkan_langkah(jawaban.langkah, kunci)

    st.session_state["tampil"].append({"role": "assistant", "content": teks, "lampiran": lampiran, "langkah": jawaban.langkah})
    st.session_state["riwayat_llm"] += [{"role": "user", "content": pertanyaan}, {"role": "assistant", "content": teks}]


# ---------------------------------------------------------------------------
# Halaman: Chat
# ---------------------------------------------------------------------------

if halaman == "💬 Chat":
    st.title("💬 Talk to the Data")
    st.markdown(
        f"Tanya apa saja tentang data di {len(katalog.PROYEK)} proyek portofolio ini: APBD provinsi, harga Bitcoin dan "
        "paus-nya, gempa dan gunung api, pesawat, kapal di Selat Malaka, satelit, titik api, polusi udara Jabodetabek, "
        "upah vs harga rumah, konflik bersenjata dunia, pusat data, dan geografi pertahanan. "
        "Jawabannya **dihitung dari data** lewat query terstruktur, lengkap dengan grafik dan sumbernya."
    )
    if not st.session_state["tampil"]:
        st.info("Mulai dengan salah satu pertanyaan di sidebar, atau tulis sendiri di bawah. Bahasa Indonesia atau Inggris sama-sama bisa.")

    for i, pesan in enumerate(st.session_state["tampil"]):
        tampilkan_pesan(pesan, f"r{i}")

    pertanyaan = st.chat_input("Tanya tentang datanya…")
    if st.session_state["pertanyaan_tertunda"]:
        pertanyaan = st.session_state.pop("pertanyaan_tertunda")
    if pertanyaan:
        proses_pertanyaan(pertanyaan)

# ---------------------------------------------------------------------------
# Halaman: Datasets (bisa dipakai tanpa API key)
# ---------------------------------------------------------------------------

elif halaman == "🗂️ Datasets":
    st.title("🗂️ Datasets")
    st.markdown(
        "Semua data adalah **snapshot** yang disalin dari repo masing-masing proyek "
        "(perbarui dengan `python scripts/sinkron_data.py`). Halaman ini juga berisi *query builder* "
        "yang memakai mesin yang sama dengan chatbot, tanpa perlu API key."
    )
    info = pd.DataFrame(katalog.info_snapshot())
    st.dataframe(info, width="stretch", hide_index=True,
                 column_config={"baris": st.column_config.NumberColumn(format="%d")})

    st.subheader("Query builder")
    k1, k2 = st.columns([1, 2])
    id_dataset = k1.selectbox("Dataset", list(katalog.DATASET), format_func=lambda d: f"{d} · {katalog.PROYEK[katalog.DATASET[d].proyek].judul}")
    df = katalog.muat(id_dataset)
    d = katalog.DATASET[id_dataset]
    k2.markdown(f"**{d.deskripsi}**  \n" + " · ".join(f"`{k}` {v}" for k, v in d.kolom.items() if k in df.columns))

    kolom_teks = [k for k in df.columns if not pd.api.types.is_numeric_dtype(df[k]) and not pd.api.types.is_datetime64_any_dtype(df[k])]
    kolom_waktu = [k for k in df.columns if pd.api.types.is_datetime64_any_dtype(df[k])]
    kolom_angka = [k for k in df.columns if pd.api.types.is_numeric_dtype(df[k]) and not pd.api.types.is_bool_dtype(df[k])]
    pilihan_kelompok = kolom_teks + [f"{k}:{b}" for k in kolom_waktu for b in ("tahun", "bulan", "hari")]

    q1, q2, q3, q4 = st.columns(4)
    kelompok = q1.multiselect("Group by", pilihan_kelompok, max_selections=2)
    fungsi = q2.selectbox("Aggregate", list(query.FUNGSI), index=0)
    kolom_agg = q3.selectbox("Column", kolom_angka or list(df.columns)) if fungsi != "count" else None
    limit = q4.slider("Rows", 5, 200, 20)
    f1, f2, f3 = st.columns([1, 1, 2])
    kolom_filter = f1.selectbox("Filter column (optional)", ["(none)"] + list(df.columns))
    op_filter = f2.selectbox("Operator", list(query.OPERATOR), index=0)
    nilai_filter = f3.text_input("Value", placeholder="contoh: Jawa Barat, 2024, 2026-10-01")

    spek: dict = {"limit": limit}
    if kolom_filter != "(none)" and nilai_filter:
        nilai = [v.strip() for v in nilai_filter.split(",")] if op_filter in ("in", "not_in", "between") else nilai_filter
        spek["filter"] = [{"kolom": kolom_filter, "op": op_filter, "nilai": nilai}]
    if kelompok:
        spek["kelompok"] = kelompok
        spek["agregasi"] = [{"fungsi": fungsi, "kolom": kolom_agg, "alias": "nilai"}] if fungsi != "count" else [{"fungsi": "count", "alias": "nilai"}]
        spek["urut"] = {"kolom": "nilai", "turun": True}
    try:
        hasil = query.jalankan(df, spek)
        if kelompok:
            nama_x = kelompok[0].split(":")[1] if ":" in kelompok[0] else kelompok[0]
            jenis = "line" if ":" in kelompok[0] else "bar"
            warna = (kelompok[1].split(":")[1] if ":" in kelompok[1] else kelompok[1]) if len(kelompok) > 1 else None
            st.plotly_chart(grafik.buat(hasil, {"jenis": jenis, "x": nama_x, "y": "nilai", "warna": warna}), width="stretch")
        elif {"lat", "lon"} <= set(hasil.columns):
            label = next((k for k in ("nama", "lokasi", "wilayah", "callsign") if k in hasil.columns), None)
            st.plotly_chart(grafik.buat(hasil, {"jenis": "peta", "label": label}), width="stretch")
        st.dataframe(hasil, width="stretch", hide_index=True)
        if mode_belajar:
            st.caption("Spesifikasi yang dikirim ke `query.jalankan` (sama persis dengan yang dikirim chatbot):")
            st.code(json.dumps(spek, ensure_ascii=False, indent=2), language="json")
    except (query.GalatQuery, grafik.GalatGrafik) as e:
        st.error(str(e))

# ---------------------------------------------------------------------------
# Halaman: How it works
# ---------------------------------------------------------------------------

else:
    st.title("🧭 How it works")
    st.markdown(
        """
Chatbot ini **tidak menghafal data** dan tidak boleh mengarang. Alurnya untuk satu pertanyaan:

1. **Prompt sistem** berisi daftar proyek, dataset, dan nama kolom (sekitar 3.000 token), bukan isi datanya.
2. Model memutuskan dataset mana yang relevan, lalu memanggil alat **`query_data`** dengan spesifikasi JSON:
   filter → kolom hitung → kelompok + agregasi → urut → limit, plus spesifikasi grafik bila perlu.
3. **pandas** menjalankan spesifikasi itu (`src/query.py`). Tidak ada kode bebas dari model yang dieksekusi;
   hanya operasi yang sudah didaftarkan. Kalau spesifikasinya salah, pesan galat dikirim balik dan model memperbaiki.
4. Hasil query (maksimal 40 baris, sebagai JSON) dikirim balik ke model. Model merangkai jawaban dan mencantumkan sumber.
5. Aplikasi menggambar grafiknya dengan **Plotly** (`src/grafik.py`) dari DataFrame hasil, lalu menampilkan tabel sumbernya.

```python
# inti loop di src/llm.py
for putaran in range(MAKS_PUTARAN):
    pesan = klien.chat(messages, tools=alat.definisi)      # model: teks, atau permintaan memanggil alat
    if not pesan.get("tool_calls"):
        return Jawaban(pesan["content"], langkah)          # jawaban akhir
    for p in pesan["tool_calls"]:
        teks, lampiran = alat.jalankan(p["function"]["name"], json.loads(p["function"]["arguments"]))
        messages.append({"role": "tool", "tool_call_id": p["id"], "content": teks})
```

**Model dan biaya.** Memakai API yang kompatibel OpenAI, jadi provider bisa diganti lewat secrets:
Groq (`llama-3.3-70b-versatile`) atau Google Gemini (`gemini-3.5-flash-lite`). Keduanya punya tier gratis
dengan batas permintaan per menit dan per hari; kalau kena batas, aplikasi menampilkan saran tunggu.

**Yang dijaga.** Kunci API hanya hidup di secrets atau di memori sesi, tidak pernah ikut ke repo.
Alat hanya membaca; tidak ada tulis ke file atau internet dari sisi model. Riwayat yang dikirim ke model
dibatasi delapan pesan terakhir supaya hemat token.

**Keterbatasan.**
- Data adalah snapshot saat disalin dari tiap proyek; angka "terkini" berarti terkini di snapshot itu.
- Model bisa salah memilih kolom atau filter. Buka **📎 Sumber & data** untuk mengecek query yang benar-benar dijalankan.
- Query terstruktur tidak mencakup semuanya (join antar dataset, regresi, dsb.). Latihan di `docs/LATIHAN.md` membahas perluasannya.
- Jawaban soal Bitcoin bukan saran investasi.

Penjelasan lengkap, langkah demi langkah, ada di [docs/BELAJAR.md](https://github.com/Avalon2222/talk-to-the-data/blob/main/docs/BELAJAR.md).
        """
    )
    st.subheader("Projects in the index")
    for p in katalog.PROYEK.values():
        st.markdown(f"- **[{p.judul}]({p.url_repo})** — *{p.hook}* {p.deskripsi} "
                    f"({', '.join(f'`{d.id}`' for d in p.dataset)}) · [Live app]({p.url_app})")
