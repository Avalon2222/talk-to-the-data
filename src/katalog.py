"""
katalog.py - Daftar proyek dan dataset yang bisa ditanyai chatbot.

Satu tempat untuk semua metadata: proyek asal, nama file, arti tiap kolom, dan cara memuatnya.
Modul lain (alat.py, app.py, scripts/sinkron_data.py) hanya membaca dari sini. Kalau ada proyek
baru, cukup tambahkan satu entri di PROYEK dan salin datanya ke data/<id-proyek>/.

Aturan yang dijaga di sini:
- Hanya kolom yang tercantum di `kolom` yang dibawa ke DataFrame. Kolom lain dibuang supaya
  skema yang dikirim ke LLM tetap ringkas (tier gratis dibatasi token per menit).
- Semua kolom waktu diparse menjadi datetime naive UTC, supaya filter/bucket waktu konsisten.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src import maskapai

DIR_DATA = Path(__file__).resolve().parent.parent / "data"
AKUN_GITHUB = "Avalon2222"


@dataclass(frozen=True)
class Dataset:
    id: str
    proyek: str
    file: str                 # nama file di data/<proyek>/
    asal: str                 # path file di repo asal (untuk scripts/sinkron_data.py)
    deskripsi: str
    kolom: dict[str, str]     # nama kolom → arti singkat; hanya kolom ini yang dipakai
    waktu: tuple[str, ...] = ()
    format: str = "csv"       # csv | usgs | bmkg

    @property
    def path(self) -> Path:
        return DIR_DATA / self.proyek / self.file


@dataclass(frozen=True)
class Proyek:
    id: str
    judul: str
    hook: str
    deskripsi: str
    dataset: tuple[Dataset, ...]

    @property
    def url_repo(self) -> str:
        return f"https://github.com/{AKUN_GITHUB}/{self.id}"

    @property
    def url_app(self) -> str:
        return f"https://{self.id}.streamlit.app"


def _ds(proyek: str, id: str, file: str, deskripsi: str, kolom: dict[str, str], asal: str | None = None,
        waktu: tuple[str, ...] = (), format: str = "csv") -> Dataset:
    return Dataset(id, proyek, file, asal or f"data/{file}", deskripsi, kolom, waktu, format)


# ---------------------------------------------------------------------------
# Definisi proyek + dataset
# ---------------------------------------------------------------------------

PROYEK: dict[str, Proyek] = {}


def _daftar(p: Proyek) -> None:
    PROYEK[p.id] = p


_daftar(Proyek(
    "dc-impact-dashboard", "Data Center Impact Dashboard", "The machines are thirsty.",
    "Peta pusat data (data center) di Indonesia beserta estimasi konsumsi listrik dan air.",
    (
        _ds("dc-impact-dashboard", "data_center", "data_center_indonesia.csv",
            "Daftar pusat data di Indonesia: operator, lokasi, kapasitas IT (MW), status, tahun beroperasi.",
            {"nama": "nama fasilitas", "operator": "perusahaan pengelola", "kabupaten_kota": "kabupaten/kota",
             "provinsi": "provinsi", "lat": "lintang", "lon": "bujur",
             "kapasitas_it_mw": "kapasitas IT dalam megawatt", "status": "beroperasi/dibangun/direncanakan",
             "tahun": "tahun mulai beroperasi (perkiraan)", "tipe": "kolokasi/hyperscale/dsb.",
             "keyakinan": "tingkat keyakinan data: tinggi/sedang/rendah", "sumber": "sumber data"}),
        _ds("dc-impact-dashboard", "parameter_asumsi", "parameter_asumsi.csv",
            "Parameter asumsi perhitungan listrik dan air: PUE, WUE, utilisasi, konsumsi per kapita.",
            {"parameter": "nama parameter", "nilai": "nilai", "satuan": "satuan", "sumber": "sumber",
             "catatan": "penjelasan"}),
    ),
))

_daftar(Proyek(
    "btc-news-volatility", "Bitcoin vs World News", "Every Bitcoin crash has a suspect.",
    "Harga Bitcoin harian sejak 2020 dan daftar berita besar dunia yang bertepatan dengan hari-hari paling liar.",
    (
        _ds("btc-news-volatility", "btc_harga_harian", "btc_harga_harian.csv",
            "Harga BTC-USD harian (OHLCV) sejak 1 Januari 2020.",
            {"tanggal": "tanggal (UTC)", "open": "harga buka USD", "high": "tertinggi", "low": "terendah",
             "close": "harga tutup USD", "volume": "volume perdagangan USD"}, waktu=("tanggal",)),
        _ds("btc-news-volatility", "berita_besar", "berita_besar.csv",
            "Sekitar 100 peristiwa dunia besar 2020-2026 yang dikaitkan dengan gejolak harga Bitcoin.",
            {"tanggal": "tanggal peristiwa", "judul": "judul peristiwa", "kategori": "kategori: geopolitik, "
             "the_fed_makro, regulasi, bursa_crypto, trump, teknologi, dsb.", "penjelasan": "ringkasan peristiwa",
             "sumber_url": "tautan sumber"}, waktu=("tanggal",)),
    ),
))

_daftar(Proyek(
    "indonesia-defense-gis", "Indonesia Defense WebGIS", "The archipelago, under the all-seeing eye.",
    "Geografi pertahanan Indonesia: markas TNI, pulau terluar, alur laut (ALKI), pangkalan asing di kawasan, "
    "anggaran pertahanan, dan alutsista. Semua dari sumber publik.",
    (
        _ds("indonesia-defense-gis", "markas_tni", "markas_tni.csv",
            "Markas dan pangkalan utama TNI (AD, AL, AU, gabungan).",
            {"nama": "nama markas", "matra": "AD/AL/AU/Gabungan", "jenis": "jenis satuan (Kodam, Lantamal, Lanud, dsb.)",
             "kota": "kota", "provinsi": "provinsi", "lat": "lintang", "lon": "bujur", "keterangan": "keterangan"}),
        _ds("indonesia-defense-gis", "pangkalan_asing", "pangkalan_asing.csv",
            "Pangkalan militer asing di kawasan Asia Tenggara dan Pasifik barat.",
            {"nama": "nama pangkalan", "negara_operator": "negara pengguna", "negara_tuan_rumah": "negara lokasi",
             "jenis": "udara/laut/darat", "lat": "lintang", "lon": "bujur", "status": "status", "keterangan": "keterangan"}),
        _ds("indonesia-defense-gis", "pulau_terluar", "pulau_terluar_perbatasan.csv",
            "Pulau-pulau terluar dan titik perbatasan Indonesia.",
            {"nama": "nama pulau/titik", "jenis": "pulau_terluar/pos_perbatasan", "provinsi": "provinsi", "lat": "lintang",
             "lon": "bujur", "berbatasan_dengan": "negara tetangga", "keterangan": "keterangan"}),
        _ds("indonesia-defense-gis", "alki", "alki.csv",
            "Titik-titik jalur Alur Laut Kepulauan Indonesia (ALKI I, II, III).",
            {"alki": "nama alur", "urutan": "urutan titik", "lat": "lintang", "lon": "bujur", "keterangan": "lokasi"}),
        _ds("indonesia-defense-gis", "anggaran_indonesia", "anggaran_indonesia.csv",
            "Anggaran pertahanan Indonesia per tahun 2015-2026 (triliun rupiah dan % PDB).",
            {"tahun": "tahun", "anggaran_rp_triliun": "anggaran dalam triliun rupiah", "persen_pdb": "persentase PDB",
             "keyakinan": "tingkat keyakinan data", "catatan": "catatan", "sumber": "sumber"}),
        _ds("indonesia-defense-gis", "anggaran_kawasan", "anggaran_kawasan.csv",
            "Belanja militer 2024 negara-negara kawasan (USD miliar, % PDB, personel aktif).",
            {"negara": "negara", "belanja_usd_miliar_2024": "belanja militer 2024, miliar USD",
             "persen_pdb_2024": "persentase PDB 2024", "personel_aktif_ribu": "personel aktif (ribu orang)",
             "sumber": "sumber"}),
        _ds("indonesia-defense-gis", "alutsista", "alutsista.csv",
            "Perkiraan jumlah alutsista utama TNI (tank, pesawat tempur, kapal selam, dsb.).",
            {"matra": "AD/AL/AU", "alutsista": "nama alat", "jumlah_perkiraan": "jumlah perkiraan unit",
             "status": "aktif/dipesan", "sumber": "sumber"}),
    ),
))

_daftar(Proyek(
    "ring-of-fire-pulse", "The Pulse of the Ring of Fire", "The ground never sleeps.",
    "Gempa dan gunung api Indonesia dari BMKG, USGS, dan MAGMA ESDM (snapshot 30 hari terakhir saat data diambil).",
    (
        _ds("ring-of-fire-pulse", "gempa_usgs", "usgs.json",
            "Gempa M≥2,5 di wilayah Indonesia dari katalog USGS, sekitar 30 hari terakhir (snapshot).",
            {"waktu": "waktu kejadian (UTC)", "magnitudo": "magnitudo", "tipe_magnitudo": "jenis skala (mb, mww, dsb.)",
             "lokasi": "deskripsi lokasi (bahasa Inggris)", "lat": "lintang", "lon": "bujur",
             "kedalaman_km": "kedalaman km", "tsunami": "1 bila ada peringatan tsunami", "url": "halaman USGS"},
            asal="data/sample/usgs.json", waktu=("waktu",), format="usgs"),
        _ds("ring-of-fire-pulse", "gempa_bmkg", "bmkg_terkini.json",
            "15 gempa M≥5 terbaru versi BMKG (snapshot).",
            {"waktu": "waktu kejadian (UTC)", "magnitudo": "magnitudo", "kedalaman_km": "kedalaman km",
             "lat": "lintang", "lon": "bujur", "wilayah": "deskripsi wilayah", "potensi": "potensi tsunami"},
            asal="data/sample/bmkg_terkini.json", waktu=("waktu",), format="bmkg"),
        _ds("ring-of-fire-pulse", "gunung_api", "gunung_api.csv",
            "Gunung api aktif Indonesia (Smithsonian GVP): koordinat dan elevasi.",
            {"nama": "nama gunung", "lat": "lintang", "lon": "bujur", "elevasi_m": "elevasi meter", "provinsi": "provinsi"}),
        _ds("ring-of-fire-pulse", "magma_level", "magma_level.csv",
            "Status aktivitas gunung api menurut MAGMA ESDM (Level 1 Normal sampai 4 Awas), snapshot.",
            {"nama": "nama gunung", "provinsi": "provinsi", "level": "level 1-4", "status": "Normal/Waspada/Siaga/Awas",
             "url_laporan": "tautan laporan"}, asal="data/sample/magma_level.csv"),
    ),
))

_daftar(Proyek(
    "who-owns-the-sky", "Who Owns the Sky?", "Every plane leaves a trail.",
    "Posisi pesawat di atas Indonesia dari data ADS-B publik (OpenSky), snapshot sekitar 60 kali selama ±20 menit.",
    (
        _ds("who-owns-the-sky", "pesawat", "snapshots.csv",
            "Posisi pesawat per snapshot (satu baris = satu pesawat pada satu waktu). Satu pesawat muncul "
            "berkali-kali; untuk menghitung pesawat unik pakai nunique pada icao24.",
            {"icao24": "ID transponder unik pesawat", "callsign": "callsign penerbangan", "maskapai": "maskapai (tebakan dari callsign)",
             "negara_maskapai": "negara maskapai", "negara_asal": "negara registrasi pesawat", "waktu": "waktu snapshot (UTC)",
             "lat": "lintang", "lon": "bujur", "alt_baro_m": "ketinggian meter", "di_darat": "True bila di darat",
             "kecepatan_ms": "kecepatan m/s", "arah": "arah derajat"},
            asal="data/sample/snapshots.csv"),
        _ds("who-owns-the-sky", "bandara", "bandara.csv",
            "Bandara utama di Indonesia dan sekitarnya.",
            {"kode": "kode IATA", "nama": "nama bandara", "kota": "kota", "negara": "negara", "lat": "lintang", "lon": "bujur"}),
    ),
))

_daftar(Proyek(
    "follow-the-money", "Follow the Money", "Every rupiah has a destination.",
    "APBD (anggaran dan realisasi) 38 provinsi Indonesia dari DJPK Kemenkeu, 2022-2025, plus penduduk dan luas.",
    (
        _ds("follow-the-money", "apbd_provinsi", "apbd_provinsi.csv",
            "APBD provinsi per akun, dalam RUPIAH PENUH. tingkat 1 = total (Pendapatan Daerah, Belanja Daerah, "
            "Pembiayaan Daerah), tingkat 2 = kelompok (PAD, TKDD, Belanja Pegawai, Belanja Modal, ...), tingkat 3 = rincian "
            "(Pajak Daerah, Belanja Hibah, ...). Selalu filter satu tingkat atau satu akun; jangan menjumlahkan lintas tingkat.",
            {"kode_bps": "kode provinsi BPS", "provinsi": "nama provinsi", "tahun": "tahun anggaran", "akun": "nama akun",
             "induk": "akun induk", "tingkat": "1 total, 2 kelompok, 3 rincian", "anggaran": "anggaran, rupiah",
             "realisasi": "realisasi, rupiah"}),
        _ds("follow-the-money", "penduduk_provinsi", "penduduk_provinsi.csv",
            "Penduduk 2025 dan luas wilayah tiap provinsi (untuk angka per kapita).",
            {"kode_bps": "kode provinsi BPS", "provinsi": "nama provinsi", "luas_km2": "luas km²",
             "penduduk_2025": "jumlah penduduk 2025"}),
    ),
))

_daftar(Proyek(
    "btc-whale-watch", "Whale Watch", "Someone always moves first.",
    "Transaksi Bitcoin raksasa (≥ 50 BTC) langsung dari blockchain selama ±3 hari, disandingkan dengan harga per 5 menit.",
    (
        _ds("btc-whale-watch", "transaksi_paus", "transaksi_paus.csv",
            "Transaksi Bitcoin dengan total output ≥ 50 BTC, 28-31 Oktober 2026.",
            {"txid": "hash transaksi", "waktu": "waktu blok (UTC)", "tinggi_blok": "nomor blok",
             "jumlah_input": "jumlah input", "jumlah_output": "jumlah output", "total_btc": "total output BTC",
             "fee_btc": "biaya transaksi BTC", "output_terbesar_btc": "output tunggal terbesar BTC",
             "pola": "konsolidasi/distribusi/transfer", "bulat": "True bila output terbesar bilangan bulat BTC"},
            waktu=("waktu",)),
        _ds("btc-whale-watch", "blok", "blok.csv",
            "Ringkasan tiap blok yang diproses: jumlah transaksi, jumlah paus, BTC paus.",
            {"tinggi": "nomor blok", "waktu": "waktu blok (UTC)", "jumlah_tx": "jumlah transaksi di blok",
             "jumlah_paus": "transaksi ≥ 50 BTC", "btc_paus": "total BTC transaksi paus"}, waktu=("waktu",)),
        _ds("btc-whale-watch", "btc_harga_5menit", "btc_harga_5menit.csv",
            "Candle BTC-USD per 5 menit (Coinbase) yang menutupi rentang blok.",
            {"waktu": "waktu candle (UTC)", "open": "buka", "high": "tertinggi", "low": "terendah", "close": "tutup",
             "volume": "volume BTC"}, waktu=("waktu",)),
    ),
))

DATASET: dict[str, Dataset] = {d.id: d for p in PROYEK.values() for d in p.dataset}


# ---------------------------------------------------------------------------
# Memuat data
# ---------------------------------------------------------------------------

def _baca_usgs(path: Path) -> pd.DataFrame:
    fitur = json.loads(path.read_text(encoding="utf-8")).get("features", [])
    baris = []
    for f in fitur:
        p, g = f.get("properties", {}), f.get("geometry", {}).get("coordinates", [None, None, None])
        baris.append({
            "waktu": pd.to_datetime(p.get("time"), unit="ms"), "magnitudo": p.get("mag"),
            "tipe_magnitudo": p.get("magType"), "lokasi": p.get("place"), "lat": g[1], "lon": g[0],
            "kedalaman_km": g[2] if len(g) > 2 else None, "tsunami": p.get("tsunami", 0), "url": p.get("url"),
        })
    return pd.DataFrame(baris)


def _baca_bmkg(path: Path) -> pd.DataFrame:
    daftar = json.loads(path.read_text(encoding="utf-8")).get("Infogempa", {}).get("gempa", [])
    baris = []
    for g in daftar:
        lat, lon = (float(x) for x in g["Coordinates"].split(","))
        baris.append({
            "waktu": pd.to_datetime(g["DateTime"], utc=True).tz_convert(None), "magnitudo": float(g["Magnitude"]),
            "kedalaman_km": float(str(g["Kedalaman"]).split()[0]), "lat": lat, "lon": lon,
            "wilayah": g.get("Wilayah"), "potensi": g.get("Potensi"),
        })
    return pd.DataFrame(baris)


def _turunan(id: str, df: pd.DataFrame) -> pd.DataFrame:
    """Kolom tambahan yang tidak ada di file asal."""
    if id == "pesawat":
        df = df.copy()
        df["waktu"] = pd.to_datetime(df["waktu_snapshot"], unit="s")
        cs = df["callsign"].fillna("").astype(str)
        df["maskapai"] = cs.map(maskapai.tebak_maskapai)
        df["negara_maskapai"] = cs.map(maskapai.negara_maskapai)
    return df


@lru_cache(maxsize=None)
def muat(id: str) -> pd.DataFrame:
    """Muat satu dataset (dari cache setelah pemanggilan pertama). ValueError bila id tidak dikenal."""
    if id not in DATASET:
        raise ValueError(f"Dataset '{id}' tidak ada. Pilihan: {', '.join(DATASET)}.")
    d = DATASET[id]
    if not d.path.exists():
        raise FileNotFoundError(f"File {d.path} tidak ditemukan. Jalankan: python scripts/sinkron_data.py")
    if d.format == "usgs":
        df = _baca_usgs(d.path)
    elif d.format == "bmkg":
        df = _baca_bmkg(d.path)
    else:
        df = pd.read_csv(d.path)
    df = _turunan(id, df)
    for k in d.waktu:
        df[k] = pd.to_datetime(df[k], utc=True, errors="coerce").dt.tz_convert(None)
    ada = [k for k in d.kolom if k in df.columns]
    return df[ada].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Deskripsi untuk LLM
# ---------------------------------------------------------------------------

def skema_ringkas() -> str:
    """Satu blok teks: semua proyek + dataset + kolom. Dipakai di prompt sistem."""
    baris = []
    for p in PROYEK.values():
        baris.append(f"## {p.judul} (proyek `{p.id}`): {p.deskripsi}")
        for d in p.dataset:
            baris.append(f"- dataset `{d.id}`: {d.deskripsi} Kolom: {', '.join(d.kolom)}.")
    return "\n".join(baris)


def deskripsi_dataset(id: str, maks_contoh: int = 15) -> str:
    """Profil kolom: tipe, rentang/nilai unik, jumlah baris. Dipakai alat describe_dataset."""
    d = DATASET.get(id)
    if d is None:
        raise ValueError(f"Dataset '{id}' tidak ada. Pilihan: {', '.join(DATASET)}.")
    df = muat(id)
    p = PROYEK[d.proyek]
    baris = [f"Dataset `{id}` dari proyek {p.judul}: {d.deskripsi}", f"{len(df)} baris."]
    for kolom in df.columns:
        seri = df[kolom]
        arti = d.kolom.get(kolom, "")
        if pd.api.types.is_datetime64_any_dtype(seri):
            info = f"waktu, {seri.min()} s.d. {seri.max()}"
        elif pd.api.types.is_bool_dtype(seri):
            info = f"boolean, True pada {int(seri.sum())} baris"
        elif pd.api.types.is_numeric_dtype(seri):
            info = f"angka, min {seri.min():g}, median {seri.median():g}, max {seri.max():g}"
        else:
            unik = seri.dropna().astype(str).unique()
            contoh = ", ".join(sorted(unik)[:maks_contoh])
            info = f"teks, {len(unik)} nilai unik" + (f": {contoh}" if len(unik) <= maks_contoh else f", contoh: {contoh}, ...")
        baris.append(f"- {kolom} ({arti}): {info}")
    return "\n".join(baris)


def info_snapshot() -> list[dict]:
    """Ringkasan tiap dataset untuk halaman Datasets di app: baris, kolom, rentang waktu."""
    hasil = []
    for p in PROYEK.values():
        for d in p.dataset:
            df = muat(d.id)
            rentang = ""
            if d.waktu and d.waktu[0] in df.columns:
                s = df[d.waktu[0]]
                rentang = f"{s.min():%d %b %Y} – {s.max():%d %b %Y}"
            hasil.append({"proyek": p.judul, "dataset": d.id, "baris": len(df), "kolom": len(df.columns),
                          "rentang_waktu": rentang, "deskripsi": d.deskripsi})
    return hasil
