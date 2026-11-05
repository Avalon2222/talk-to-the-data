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

from src import maskapai, mmsi, wilayah

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
    pendukung: tuple[tuple[str, str], ...] = ()   # (file, path asal) yang dibutuhkan kolom turunan

    @property
    def path(self) -> Path:
        return DIR_DATA / self.proyek / self.file

    def path_pendukung(self, file: str) -> Path:
        return DIR_DATA / self.proyek / file


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
        waktu: tuple[str, ...] = (), format: str = "csv", pendukung: tuple[tuple[str, str], ...] = ()) -> Dataset:
    return Dataset(id, proyek, file, asal or f"data/{file}", deskripsi, kolom, waktu, format, pendukung)


# ---------------------------------------------------------------------------
# Definisi proyek + dataset
# ---------------------------------------------------------------------------

PROYEK: dict[str, Proyek] = {}


def _daftar(p: Proyek) -> None:
    PROYEK[p.id] = p


_daftar(Proyek(
    "dc-impact-dashboard", "Data Center Impact Dashboard", "The machines are thirsty.",
    "Data center Indonesia, estimasi listrik dan air, PUE Google, listrik/air Meta, prediksi PUE.",
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
        _ds("dc-impact-dashboard", "pue_google", "pue_google_kuartalan.csv",
            "PUE kuartalan tiap kampus data center Google 2008-2026; 'Fleet' = seluruh armada.",
            {"kampus": "kampus Google (atau Fleet)", "tahun": "tahun", "kuartal": "kuartal 1-4",
             "pue_kuartalan": "PUE kuartal itu", "pue_ttm": "PUE 12 bulan terakhir"}),
        _ds("dc-impact-dashboard", "meta_listrik_air", "meta_listrik_air_tahunan.csv",
            "Listrik (MWh) dan air (megaliter) tahunan tiap situs data center Meta 2020-2024.",
            {"situs": "situs Meta", "tahun": "tahun", "listrik_mwh": "listrik MWh", "air_megaliter": "air megaliter"}),
        _ds("dc-impact-dashboard", "prediksi_pue_lokasi", "prediksi_lokasi.csv",
            "Prediksi PUE/WUE kelas hyperscale dari model iklim untuk lokasi data center Indonesia.",
            {"kabupaten_kota": "kabupaten/kota", "provinsi": "provinsi", "lat": "lintang", "lon": "bujur",
             "pue_prediksi": "PUE prediksi", "wue_prediksi": "WUE prediksi L/kWh", "suhu_rata": "suhu rata-rata °C",
             "rh_rata": "kelembapan %", "bola_basah_rata": "suhu bola basah °C"}),
    ),
))

_daftar(Proyek(
    "btc-news-volatility", "Bitcoin vs World News", "Every Bitcoin crash has a suspect.",
    "Harga Bitcoin harian sejak 2020 dan berita besar dunia pada hari-hari paling liar.",
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
    "Markas TNI, pulau terluar, ALKI, pangkalan asing, anggaran, dan alutsista Indonesia.",
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
    "Gempa dan gunung api Indonesia dari BMKG, USGS, dan MAGMA ESDM (snapshot 30 hari terakhir).",
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
            "APBD provinsi per akun, dalam RUPIAH PENUH. tingkat 1 = total (Pendapatan/Belanja/Pembiayaan Daerah), 2 "
            "= kelompok (PAD, TKDD, Belanja Pegawai, ...), 3 = rincian (Pajak Daerah, ...). Selalu filter satu "
            "tingkat atau satu akun; jangan menjumlahkan lintas tingkat.",
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
    "Transaksi Bitcoin raksasa (≥ 50 BTC) dari blockchain selama ±3 hari, dengan harga per 5 menit.",
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

_daftar(Proyek(
    "roof-vs-paycheck", "Roof vs Paycheck", "Count the years before the key turns.",
    "Upah minimum 2026 di 13 kota vs harga rumah subsidi, rumah seken, apartemen, kos, dan kontrakan.",
    (
        _ds("roof-vs-paycheck", "kota_upah_rumah", "kota.csv",
            "Satu baris per kota (13 kota). Harga rumah dalam JUTA rupiah, upah/kos/kontrakan dalam rupiah per bulan. "
            "Kode mutu: A laporan resmi, B rentang artikel, C listing, E perkiraan. Lama menabung bisa dihitung dengan "
            "kolom hitung, misalnya 'rumah_seken_juta * 1000000 / (umk_2026 * 12 * 0.3)' (nabung 30% upah).",
            {"kota": "nama kota", "provinsi": "provinsi", "zona_flpp": "zona harga rumah subsidi",
             "umk_2026": "upah minimum 2026, Rp/bulan", "rumah_subsidi_juta": "batas harga rumah subsidi FLPP, juta Rp",
             "rumah_seken_juta": "median rumah seken ≤60 m², juta Rp", "rumah_seken_mutu": "kode mutu harga rumah seken",
             "apartemen_per_m2_juta": "harga apartemen per m², juta Rp (kosong = tidak ada data)",
             "kos_min": "kos standar terendah, Rp/bulan", "kos_max": "kos standar tertinggi, Rp/bulan",
             "kontrakan": "kontrakan 1-2 kamar sederhana, Rp/bulan"}),
        _ds("roof-vs-paycheck", "asumsi_kpr", "asumsi.csv",
            "Asumsi awal simulasi: BI-Rate, bunga KPR tetap dan mengambang, DP, tenor, kenaikan harga rumah, sewa, "
            "upah.",
            {"parameter": "nama parameter", "nilai": "nilai", "satuan": "satuan", "sumber": "sumber"}),
    ),
))

_daftar(Proyek(
    "the-air-we-breathe", "The Air We Breathe", "Every breath is a data point.",
    "Kualitas udara per jam di 51 titik Jabodetabek (Open-Meteo, model CAMS): 60 hari terakhir plus prakiraan 2 hari.",
    (
        _ds("the-air-we-breathe", "udara_per_jam", "jam.csv.gz",
            "PM2.5, PM10, NO2, O3 dan cuaca per jam per titik (model CAMS 0,4°, cenderung di bawah sensor). "
            "prakiraan=True = baris prakiraan. kategori_ispu dari PM2.5 per jam.",
            {"titik": "nama titik (kecamatan/kawasan)", "kota": "Jakarta/Bogor/Depok/Tangerang/Bekasi",
             "wilayah": "wilayah administratif", "lat": "lintang", "lon": "bujur", "waktu": "waktu (UTC)",
             "pm2_5": "PM2.5 µg/m³", "pm10": "PM10 µg/m³", "no2": "NO2 µg/m³", "o3": "ozon µg/m³",
             "kategori_ispu": "Baik/Sedang/Tidak Sehat/Sangat Tidak Sehat/Berbahaya", "suhu": "suhu °C",
             "rh": "kelembapan %", "hujan": "hujan mm", "angin": "kecepatan angin km/j",
             "prakiraan": "True bila baris prakiraan"},
            asal="data/sample/jam.csv.gz", waktu=("waktu",)),
    ),
))

_daftar(Proyek(
    "burning-archipelago", "The Burning Archipelago", "First the smoke, then the silence.",
    "Titik api NASA FIRMS 7 hari dan kehilangan tutupan pohon per provinsi 2001-2025 (Global Forest Watch).",
    (
        _ds("burning-archipelago", "titik_api", "titik_api_7hari.csv.gz",
            "Titik panas VIIRS 7 hari; satu titik = piksel 375 m, bukan satu kebakaran. Per provinsi: buang 'Laut / "
            "luar negeri', pakai keyakinan Nominal/Tinggi.",
            {"waktu": "waktu deteksi (UTC)", "lat": "lintang", "lon": "bujur", "provinsi": "provinsi (dari poligon)",
             "frp": "fire radiative power, MW", "keyakinan": "Rendah/Nominal/Tinggi", "siang_malam": "Siang/Malam",
             "satelit": "NOAA-20/NOAA-21"},
            asal="data/sample/titik_api_7hari.csv.gz", waktu=("waktu",),
            pendukung=(("provinsi.geojson", "data/provinsi.geojson"),)),
        _ds("burning-archipelago", "hilang_tutupan_pohon", "gfw_tahunan.csv",
            "Kehilangan tutupan pohon per provinsi per tahun 2001-2025 (GFW/Hansen, kanopi ≥30%), termasuk akibat "
            "kebakaran. Provinsi versi GADM ('Jakarta Raya', 'Yogyakarta', 'Bangka Belitung').",
            {"provinsi_gfw": "provinsi (versi GADM)", "tahun": "tahun", "hilang_ha": "kehilangan tutupan pohon, hektar",
             "hilang_api_ha": "bagian akibat kebakaran, hektar", "emisi_mg": "emisi kotor, megagram CO2e"}),
        _ds("burning-archipelago", "tutupan_pohon", "gfw_tutupan.csv",
            "Luas wilayah dan tutupan pohon tahun 2000 dan 2010 per provinsi, serta pertumbuhan 2000-2020 (hektar).",
            {"provinsi_gfw": "provinsi (versi GADM)", "luas_ha": "luas wilayah ha", "tutupan_2000_ha": "tutupan pohon 2000 ha",
             "tutupan_2010_ha": "tutupan pohon 2010 ha", "tumbuh_ha": "pertumbuhan tutupan 2000-2020 ha"}),
    ),
))

_daftar(Proyek(
    "global-conflict-tracker", "Global Conflict Tracker", "The world, counted in casualties.",
    "Kekerasan bersenjata terorganisasi di dunia 1989-2026 (UCDP; data 2026 berstatus 'awal').",
    (
        _ds("global-conflict-tracker", "korban_negara", "korban_negara_tahun.csv",
            "Kejadian dan korban jiwa per negara × tahun × jenis kekerasan × status. Jumlahkan lintas jenis untuk total "
            "negara. Nama negara dalam bahasa Indonesia (misalnya 'Afganistan', 'Etiopia').",
            {"negara": "negara (nama Indonesia)", "iso3": "kode ISO3", "wilayah": "Afrika/Amerika/Asia/Eropa/Timur Tengah",
             "tahun": "tahun", "jenis": "Konflik negara/Konflik non-negara/Kekerasan sepihak", "status": "final/awal",
             "kejadian": "jumlah kejadian", "korban": "korban jiwa (estimasi terbaik)", "korban_min": "estimasi terendah",
             "korban_max": "estimasi tertinggi", "korban_sipil": "korban sipil yang disebut sumber (cenderung terlalu rendah)"}),
        _ds("global-conflict-tracker", "konflik", "konflik_tahun.csv",
            "Kejadian dan korban per konflik bernama UCDP per tahun, dengan negara tempat kejadian terbanyak.",
            {"konflik": "nama konflik UCDP", "jenis": "jenis kekerasan", "tahun": "tahun", "status": "final/awal",
             "kejadian": "jumlah kejadian", "korban": "korban jiwa", "korban_sipil": "korban sipil",
             "negara_utama": "negara dengan kejadian terbanyak"}),
        _ds("global-conflict-tracker", "konflik_grid", "grid_kejadian.csv",
            "Kejadian dan korban per sel grid 0,5° per tahun, untuk peta lokasi konflik.",
            {"tahun": "tahun", "lat": "lintang pusat sel", "lon": "bujur pusat sel", "jenis": "jenis kekerasan",
             "negara": "negara", "status": "final/awal", "kejadian": "jumlah kejadian", "korban": "korban jiwa"}),
    ),
))

_daftar(Proyek(
    "strait-watch", "Strait Watch", "The world's busiest chokepoint, live.",
    "Lalu lintas kapal Selat Malaka: transit harian per selat sejak 2019 (IMF PortWatch) dan potret posisi kapal AIS.",
    (
        _ds("strait-watch", "transit_selat_harian", "portwatch_harian.csv",
            "Kapal niaga melintas per hari per selat dan jenis sejak 2019: Malaka, Sunda, Lombok, Makassar, Ombai, "
            "plus Hormuz, Suez, Taiwan.",
            {"tanggal": "tanggal", "selat": "nama selat (bahasa Indonesia)", "n_total": "total kapal melintas",
             "n_tanker": "tanker", "n_container": "kontainer", "n_dry_bulk": "curah kering", "n_general_cargo": "kargo umum",
             "n_roro": "Ro-Ro", "capacity": "kapasitas total DWT", "capacity_tanker": "kapasitas tanker DWT"},
            waktu=("tanggal",)),
        _ds("strait-watch", "chokepoint_dunia", "portwatch_chokepoint.csv",
            "28 chokepoint maritim dunia: lokasi dan jumlah kapal per jenis dalam setahun (database PortWatch).",
            {"portname": "nama chokepoint (bahasa Inggris)", "lat": "lintang", "lon": "bujur",
             "vessel_count_total": "kapal per tahun", "vessel_count_tanker": "tanker per tahun",
             "vessel_count_container": "kontainer per tahun", "vessel_count_dry_bulk": "curah kering per tahun",
             "industry_top1": "komoditas utama"}),
        _ds("strait-watch", "posisi_kapal", "posisi.csv",
            "Potret posisi kapal AIS Selat Malaka ±1 jam (2 Nov 2026). Hitung kapal unik dengan nunique pada mmsi. "
            "Bendera dari kode MMSI.",
            {"mmsi": "ID kapal", "nama": "nama kapal", "bendera": "negara bendera", "kategori": "Kargo/Tanker/Penumpang/...",
             "tujuan": "tujuan (diisi awak)", "panjang_m": "panjang meter", "lat": "lintang", "lon": "bujur",
             "sog_knot": "kecepatan knot", "status_navigasi": "status navigasi", "waktu": "waktu snapshot (UTC)"},
            asal="data/sample/posisi.csv", waktu=("waktu",),
            pendukung=(("kapal_statis.csv", "data/sample/kapal_statis.csv"),)),
        _ds("strait-watch", "pelabuhan_selat", "pelabuhan.csv",
            "Pelabuhan dan pangkalan angkatan laut di sekitar Selat Malaka.",
            {"nama": "nama", "kota": "kota", "negara": "negara", "jenis": "pelabuhan/pangkalan", "lat": "lintang", "lon": "bujur"}),
    ),
))

_daftar(Proyek(
    "who-watches-indonesia", "Who Watches Indonesia?", "Look up. Someone is already looking down.",
    "Katalog satelit dunia (GCAT) dan satelit milik Indonesia.",
    (
        _ds("who-watches-indonesia", "katalog_satelit", "katalog_satelit.csv",
            "Semua satelit bernomor NORAD (±27 ribu): negara, pemilik, kelas operator, misi; termasuk yang mati.",
            {"norad": "nomor NORAD", "nama_gcat": "nama", "negara": "negara (nama Indonesia)", "pemilik": "kode pemilik",
             "militer": "True bila dioperasikan militer", "kelas": "A amatir, B komersial, C sipil, D militer",
             "kategori": "COM komunikasi, IMG pencitraan, IMG-R radar, SIG intai sinyal, NAV, MET, SCI, TECH, ...",
             "program": "program/konstelasi", "orbit_gcat": "kode orbit (LLEO, LEO, MEO, GEO, HEO)",
             "tanggal_luncur": "tanggal peluncuran", "massa_kg": "massa kg"},
            waktu=("tanggal_luncur",), pendukung=(("kode_negara.csv", "data/kode_negara.csv"),)),
        _ds("who-watches-indonesia", "satelit_indonesia", "satelit_indonesia.csv",
            "Sembilan satelit Indonesia yang masih dilacak: operator, fungsi, orbit, tanggal luncur.",
            {"nama": "nama satelit", "operator": "operator", "fungsi": "fungsi", "orbit": "orbit",
             "diluncurkan": "tanggal luncur", "catatan": "catatan"}),
    ),
))

_daftar(Proyek(
    "blackout-watch", "Blackout Watch", "Someone pulled the plug.",
    "Pemutusan internet dunia 2016-2025 (Access Now) dan gangguan 30 hari terakhir (IODA).",
    (
        _ds("blackout-watch", "shutdown_internet", "shutdown_dunia.csv",
            "Pemutusan/pelambatan/pemblokiran internet 2016-2025; nama negara bahasa Indonesia. 'pemicu' = sebab di "
            "lapangan, 'alasan_pemerintah' = dalih resmi.",
            {"negara": "negara (nama Indonesia)", "iso3": "kode ISO3", "wilayah": "Asia/Afrika/Eropa/Amerika/Timur Tengah/Oseania",
             "tahun": "tahun mulai", "mulai": "tanggal mulai", "selesai": "tanggal selesai sebagai teks YYYY-MM-DD (kosong bila tidak diketahui)",
             "durasi_hari": "lama dalam hari (kosong bila tidak diketahui)", "status": "Selesai/Berlangsung/Tidak diketahui",
             "cakupan_wilayah": "Satu kota/kabupaten, Beberapa kota satu provinsi, atau Lintas provinsi / nasional",
             "daerah": "nama daerah (Inggris)", "jenis": "Pemutusan/Pelambatan/Pemutusan & pelambatan",
             "jaringan": "Broadband & seluler/Seluler/Broadband", "cakupan_layanan": "Seluruh jaringan atau Platform tertentu",
             "pemicu": "Unjuk rasa, Konflik bersenjata, Kekerasan komunal, Instabilitas politik, Pemilu, Kontrol informasi, "
             "Ujian sekolah, Hari besar/peringatan, Kunjungan pejabat, Lainnya, Tidak diketahui",
             "alasan_pemerintah": "dalih resmi, misalnya Hoaks / ujaran kebencian, Keamanan / ketertiban umum, Tidak disebutkan",
             "diperintahkan_oleh": "Pemerintah pusat/daerah/Militer/Kepolisian/...", "kekerasan": "Ya/Tidak/Tidak diketahui",
             "platform": "platform yang diblokir dipisah ';' (Facebook, WhatsApp, TikTok, ...)", "keterangan": "ringkasan peristiwa (Inggris)"},
            waktu=("mulai",)),
        _ds("blackout-watch", "gangguan_internet_30hari", "ioda_ringkasan_30hari.csv",
            "Negara dengan gangguan internet terdeteksi IODA 30 hari terakhir. Skor tanpa satuan; nama negara bahasa"
            " Inggris.",
            {"kode": "kode negara ISO2", "nama_en": "nama negara (Inggris)", "jumlah_kejadian": "jumlah kejadian gangguan",
             "skor_total": "skor gangguan total IODA", "skor_bgp": "skor dari sinyal BGP", "skor_ping": "skor dari ping aktif",
             "skor_teleskop": "skor dari teleskop jaringan", "skor_google": "skor dari trafik Google"}),
    ),
))

_daftar(Proyek(
    "cut-the-cable", "Cut the Cable", "Cut one cable. Watch who goes dark.",
    "Kabel bawah laut di dan sekitar Indonesia beserta landing station-nya (TeleGeography).",
    (
        _ds("cut-the-cable", "kabel_bawah_laut", "kabel.csv",
            "Kabel bawah laut terkait Indonesia: 74 mendarat di Indonesia, 44 hanya lewat. Kolom negara dipisah '|',"
            " pakai op 'contains'.",
            {"nama": "nama kabel", "kategori": "internasional/domestik/transit (transit = tidak mendarat di Indonesia)",
             "status": "aktif/rencana", "tahun_rfs": "tahun siap pakai (RFS)", "panjang_km": "panjang km",
             "pemilik": "pemilik/konsorsium", "pemasok": "pabrikan", "n_landing": "jumlah landing station",
             "n_landing_indonesia": "landing station di Indonesia", "negara": "negara pendaratan, dipisah |"}),
        _ds("cut-the-cable", "landing_station_kabel", "landing_station.csv",
            "Landing station kabel di atas: 361 titik, 146 di Indonesia.",
            {"nama": "nama (kota, negara)", "kota": "kota", "negara": "negara", "lat": "lintang", "lon": "bujur",
             "wilayah": "wilayah Indonesia (Sumatra & Kepulauan Riau, Jawa, Kalimantan, Sulawesi, Bali & Nusa Tenggara, "
                        "Maluku, Papua); kosong untuk luar negeri",
             "n_kabel_aktif": "jumlah kabel aktif yang mendarat", "n_kabel": "jumlah kabel termasuk rencana"}),
    ),
))

_daftar(Proyek(
    "disinfo-radar", "Disinfo Radar", "Every lie leaves a fingerprint.",
    "Arsip cek fakta Turnbackhoax (Mafindo) sejak 2015: judul, label, kategori, tanggal.",
    (
        _ds("disinfo-radar", "hoaks_cek_fakta", "hoaks_turnbackhoax.csv",
            "Satu baris per artikel cek fakta. Label dari awalan judul: SALAH (hoaks), PENIPUAN (scam), KLARIFIKASI, "
            "BENAR, HOAX/DISINFORMASI (gaya lama = hoaks). Kategori kosong untuk artikel lama. Tren: hitung baris per"
            " bulan/tahun; topik: cari kata di judul (contains).",
            {"id": "nomor artikel", "tanggal": "tanggal terbit", "judul": "judul artikel, diawali label dalam kurung siku",
             "label": "label pemeriksa fakta (SALAH, PENIPUAN, KLARIFIKASI, BENAR, HOAX, ...)",
             "kategori": "kategori Turnbackhoax (Politik, Kesehatan, Bencana, Bantuan, Lowongan, ...)", "url": "tautan artikel"},
            waktu=("tanggal",)),
    ),
))

_daftar(Proyek(
    "who-uses-palantir", "Who Uses Palantir", "The seeing stone has customers.",
    "Pemakai Palantir di dunia, kontroversi, dan pendapatannya (10-K SEC).",
    (
        _ds("who-uses-palantir", "lembaga_palantir", "pengguna_palantir.csv",
            "Nilai sering berupa plafon.",
            {"negara": "negara (nama Indonesia)", "lembaga": "nama lembaga/program",
             "sektor": "Militer & pertahanan, Intelijen, Kepolisian, Imigrasi & perbatasan, Kesehatan, Pemerintahan sipil, "
                       "Organisasi internasional, Korporasi",
             "produk": "Gotham, Foundry, AIP, Maven Smart System, ...", "tahun_mulai": "tahun mulai",
             "status": "Aktif, Rintisan, Ditinjau ulang, Ditolak/diblokir, Berakhir, Status tidak jelas",
             "nilai_juta_usd": "nilai kontrak juta USD (kurs perkiraan)", "kepastian": "Resmi atau Laporan media",
             "sumber_url": "tautan sumber"}),
        _ds("who-uses-palantir", "kontroversi_palantir", "kontroversi.csv",
            "dampak 1-3 (3 = putusan/kontrak batal).",
            {"judul": "judul kontroversi", "negara": "negara atau kawasan (Eropa, PBB)", "tahun": "tahun",
             "jenis": "Privasi & pengawasan, Pengadaan & tender, Kedaulatan data, Transparansi, Perang & targeting, ...",
             "hasil": "Investigasi media, Kontrak dihentikan, Putusan pengadilan, ...", "dampak": "skor 1-3",
             "sumber_url": "tautan sumber"}),
        _ds("who-uses-palantir", "pendapatan_palantir", "pendapatan_palantir.csv",
            "Juta USD per tahun; filter jenis dulu.",
            {"tahun": "tahun fiskal", "jenis": "segmen atau wilayah",
             "kategori": "Pemerintah/Komersial (segmen); Amerika Serikat/Inggris/Prancis/Negara lain (wilayah)",
             "nilai_juta_usd": "pendapatan juta USD"}),
    ),
))

_daftar(Proyek(
    "palantir-contracts", "Follow the Contracts", "They see everything. Now see who pays.",
    "Kontrak pemerintah AS (USAspending) dan Inggris (Contracts Finder) untuk Palantir 2008-2026.",
    (
        _ds("palantir-contracts", "kontrak_palantir_as", "as_transaksi.csv",
            "Satu baris per transaksi kontrak federal AS; jumlahkan nilai_usd (obligasi, bisa negatif).",
            {"tanggal": "tanggal transaksi", "award_id": "nomor kontrak", "nilai_usd": "dana diikat (USD)",
             "instansi": "Department of Defense, Department of Homeland Security, ...",
             "sub_instansi": "Department of the Army, U.S. Immigration and Customs Enforcement, Internal Revenue Service, ...",
             "deskripsi": "deskripsi transaksi (Inggris)", "negara_bagian": "kode negara bagian tempat pelaksanaan"},
            waktu=("tanggal",)),
        _ds("palantir-contracts", "kontrak_payung_palantir", "as_idv.csv",
            "Kontrak payung AS: plafon vs dana diikat; MULTIPLE AWARD = plafon dibagi banyak vendor.",
            {"award_id": "nomor kontrak", "sub_instansi": "instansi", "mulai": "tanggal mulai",
             "plafon_usd": "batas atas nilai (USD)", "diikat_usd": "dana yang sudah diikat lewat pesanan (USD)",
             "tipe_award": "SINGLE AWARD atau MULTIPLE AWARD", "deskripsi": "deskripsi (Inggris)"},
            waktu=("mulai",)),
        _ds("palantir-contracts", "kontrak_palantir_uk", "uk_kontrak.csv",
            "Kontrak sektor publik Inggris (GBP, nilai saat diumumkan); framework=True jangan dijumlah.",
            {"diumumkan": "tanggal pengumuman", "pembeli": "NHS England, Ministry of Defence, ...", "judul": "judul kontrak",
             "nilai_gbp": "nilai kontrak (GBP)", "framework": "True bila framework multi-pemasok"},
            waktu=("diumumkan",)),
    ),
))

_daftar(Proyek(
    "pltr-war-index", "PLTR War Index", "Every war has a ticker.",
    "Saham Palantir, saham dan ETF pertahanan, serta 48 peristiwa perang sejak IPO 2020 (event study).",
    (
        _ds("pltr-war-index", "harga_saham_perang", "harga_saham.csv",
            "Harga harian sejak 30 Sep 2020: PLTR, SPY, QQQ, ITA (ETF pertahanan), LMT, NOC, RTX, GD. "
            "Selalu filter ticker.",
            {"tanggal": "tanggal bursa", "ticker": "PLTR, SPY, QQQ, ITA, LMT, NOC, RTX, GD", "close": "harga penutupan USD",
             "adj_close": "harga disesuaikan dividen/split USD", "volume": "volume saham"},
            waktu=("tanggal",)),
        _ds("pltr-war-index", "peristiwa_perang", "peristiwa_perang.csv",
            "Perang, eskalasi, serangan AS, dan gencatan senjata 2020-2026 yang diuji terhadap saham PLTR.",
            {"tanggal": "tanggal peristiwa", "peristiwa": "nama peristiwa",
             "kategori": "perang_baru, eskalasi, keterlibatan_as, deeskalasi",
             "kawasan": "Timur Tengah, Eropa & Kaukasus, Asia, Afrika, Amerika", "keterangan": "konteks singkat",
             "sumber": "tautan sumber"},
            waktu=("tanggal",)),
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


DI_LUAR_PROVINSI = "Laut / luar negeri"

# Batas atas PM2.5 (µg/m³) tiap kategori ISPU (Permen LHK P.14/2020).
ISPU_PM25 = [(15.5, "Baik"), (55.4, "Sedang"), (150.4, "Tidak Sehat"), (250.4, "Sangat Tidak Sehat"), (float("inf"), "Berbahaya")]


def kategori_ispu(pm25: float | None) -> str | None:
    if pm25 is None or pm25 != pm25:
        return None
    for batas, nama in ISPU_PM25:
        if pm25 <= batas:
            return nama
    return None


def _turunan(id: str, df: pd.DataFrame) -> pd.DataFrame:
    """Kolom tambahan yang tidak ada di file asal."""
    d = DATASET[id]
    if id == "udara_per_jam":
        df = df.copy()
        df["kategori_ispu"] = df["pm2_5"].map(kategori_ispu)
    elif id == "titik_api":
        df = df.rename(columns={"waktu_utc": "waktu"})
        prov = wilayah.PenentuProvinsi(d.path_pendukung("provinsi.geojson")).tentukan(df["lon"], df["lat"])
        df["provinsi"] = pd.Series(prov, index=df.index).fillna(DI_LUAR_PROVINSI)
    elif id == "posisi_kapal":
        statis = pd.read_csv(d.path_pendukung("kapal_statis.csv")).drop_duplicates("mmsi", keep="last")
        df = df.merge(statis[["mmsi", "tipe_kode", "tujuan", "panjang_m"]], on="mmsi", how="left")
        df["waktu"] = df["waktu_snapshot"]
        df["bendera"] = df["mmsi"].map(mmsi.negara_bendera)
        df["kategori"] = df["tipe_kode"].map(mmsi.kategori_tipe)
        df["status_navigasi"] = df["status_nav_kode"].map(mmsi.status_navigasi)
    elif id == "katalog_satelit":
        negara = pd.read_csv(d.path_pendukung("kode_negara.csv"))
        df = df.merge(negara[["kode_gcat", "negara"]], left_on="negara_kode", right_on="kode_gcat", how="left")
        df["negara"] = df["negara"].fillna(df["negara_kode"])
        df["kelas"] = df["kelas"].fillna("-").astype(str)
        df["militer"] = df["kelas"].str.contains("D")
        df["kategori"] = df["kategori_gcat"].fillna("").astype(str).str.split("/").str[0].str.rstrip("?*")
    elif id == "lembaga_palantir":
        # Kurs perkiraan yang sama dengan proyek asal (src/analisis.py di who-uses-palantir)
        kurs = {"USD": 1.0, "GBP": 1.30, "EUR": 1.10, "AUD": 0.66, "CAD": 0.73}
        df = df.copy()
        df["nilai_juta_usd"] = (df["nilai_asli_juta"] * df["mata_uang"].map(kurs)).round(1)
    elif id == "pesawat":
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
        with open(d.path, "rb") as f:
            awal = f.read(1)
        # Beberapa CSV asal diawali satu baris komentar "# Sumber: ..." (misalnya katalog GCAT).
        df = pd.read_csv(d.path, skiprows=1 if awal == b"#" else 0)
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
