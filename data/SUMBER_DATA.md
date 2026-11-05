# Sumber data

Semua file di folder ini adalah **salinan** dari repo proyek lain di akun yang sama, diambil dengan
`python scripts/sinkron_data.py` (dari GitHub) atau `--lokal ..` (dari clone di folder induk). Daftar file,
path asal, dan arti kolom ada di satu tempat: `src/katalog.py`. Dokumentasi asli tiap dataset ada di
`data/SUMBER_DATA.md` repo masing-masing.

| Folder | Repo asal | File | Isi | Sumber asli |
|---|---|---|---|---|
| `dc-impact-dashboard/` | [dc-impact-dashboard](https://github.com/Avalon2222/dc-impact-dashboard) | `data_center_indonesia.csv`, `parameter_asumsi.csv`, `pue_google_kuartalan.csv`, `meta_listrik_air_tahunan.csv`, `prediksi_lokasi.csv` | 27 pusat data, parameter PUE/WUE, PUE kuartalan 35 kampus Google 2008-2026, listrik & air 18 situs Meta 2020-2024, prediksi PUE per lokasi | Liputan industri, pernyataan operator, Google Data Center Efficiency, Meta Environmental Data Index, NASA POWER |
| `btc-news-volatility/` | [btc-news-volatility](https://github.com/Avalon2222/btc-news-volatility) | `btc_harga_harian.csv`, `berita_besar.csv` | Harga harian BTC-USD sejak 2020, 102 peristiwa | Coinbase, kurasi manual dari Wikipedia/berita |
| `indonesia-defense-gis/` | [indonesia-defense-gis](https://github.com/Avalon2222/indonesia-defense-gis) | `markas_tni.csv`, `pangkalan_asing.csv`, `pulau_terluar_perbatasan.csv`, `alki.csv`, `anggaran_indonesia.csv`, `anggaran_kawasan.csv`, `alutsista.csv` | Geografi dan anggaran pertahanan | Wikipedia, SIPRI, IISS, Kemenkeu |
| `ring-of-fire-pulse/` | [ring-of-fire-pulse](https://github.com/Avalon2222/ring-of-fire-pulse) | `usgs.json`, `bmkg_terkini.json`, `gunung_api.csv`, `magma_level.csv` | Gempa 30 hari, 15 gempa M≥5 BMKG, 69 gunung api + level | USGS FDSN, BMKG, MAGMA ESDM, Smithsonian GVP |
| `who-owns-the-sky/` | [who-owns-the-sky](https://github.com/Avalon2222/who-owns-the-sky) | `snapshots.csv`, `bandara.csv` | ±60 snapshot posisi pesawat, 36 bandara | OpenSky Network (ADS-B) |
| `follow-the-money/` | [follow-the-money](https://github.com/Avalon2222/follow-the-money) | `apbd_provinsi.csv`, `penduduk_provinsi.csv` | APBD 38 provinsi 2022-2025 per akun, penduduk 2025 | DJPK Kemenkeu (SIKD), BPS |
| `btc-whale-watch/` | [btc-whale-watch](https://github.com/Avalon2222/btc-whale-watch) | `transaksi_paus.csv`, `blok.csv`, `btc_harga_5menit.csv` | 9.130 transaksi ≥ 50 BTC (28-31 Okt 2026), 428 blok, candle 5 menit | mempool.space, blockchain.info, Coinbase |
| `roof-vs-paycheck/` | [roof-vs-paycheck](https://github.com/Avalon2222/roof-vs-paycheck) | `kota.csv`, `asumsi.csv` | UMK 2026 dan harga rumah/kos/kontrakan 13 kota, asumsi KPR | SK upah minimum, Rumah123, Colliers, artikel (dikumpulkan manual, berkode mutu) |
| `the-air-we-breathe/` | [the-air-we-breathe](https://github.com/Avalon2222/the-air-we-breathe) | `jam.csv.gz` | Polutan dan cuaca per jam di 51 titik Jabodetabek, 60 hari + prakiraan | Open-Meteo Air Quality (CAMS) dan Forecast |
| `burning-archipelago/` | [burning-archipelago](https://github.com/Avalon2222/burning-archipelago) | `titik_api_7hari.csv.gz`, `gfw_tahunan.csv`, `gfw_tutupan.csv`, `provinsi.geojson` | ±48 ribu titik api 7 hari, kehilangan tutupan pohon 2001-2025 per provinsi | NASA FIRMS VIIRS, Global Forest Watch (Hansen/UMD) |
| `global-conflict-tracker/` | [global-conflict-tracker](https://github.com/Avalon2222/global-conflict-tracker) | `korban_negara_tahun.csv`, `konflik_tahun.csv`, `grid_kejadian.csv` | Kejadian dan korban konflik bersenjata 1989-2026 per negara, konflik, dan sel grid 0,5° | UCDP GED 26.1 dan Candidate Events (CC BY 4.0) |
| `strait-watch/` | [strait-watch](https://github.com/Avalon2222/strait-watch) | `portwatch_harian.csv`, `portwatch_chokepoint.csv`, `posisi.csv`, `kapal_statis.csv`, `pelabuhan.csv` | Transit kapal harian per selat sejak 2019, 28 chokepoint dunia, potret posisi kapal AIS | IMF PortWatch, aisstream.io, Wikipedia |
| `who-watches-indonesia/` | [who-watches-indonesia](https://github.com/Avalon2222/who-watches-indonesia) | `katalog_satelit.csv`, `kode_negara.csv`, `satelit_indonesia.csv` | ±27 ribu satelit dunia dan 9 satelit Indonesia | GCAT (CC BY 4.0), Wikipedia |
| `blackout-watch/` | [blackout-watch](https://github.com/Avalon2222/blackout-watch) | `shutdown_dunia.csv`, `ioda_ringkasan_30hari.csv` | 1.888 pemutusan internet 2016-2025 di 97 negara, gangguan terdeteksi 30 hari terakhir | Access Now #KeepItOn STOP, IODA (Georgia Tech) |
| `cut-the-cable/` | [cut-the-cable](https://github.com/Avalon2222/cut-the-cable) | `kabel.csv`, `landing_station.csv` | 118 kabel bawah laut yang mendarat di Indonesia atau lewat perairan sekitar, 361 landing station (146 di Indonesia) | Submarine Cable Map / TeleGeography (CC BY-NC-SA 3.0) |
| `disinfo-radar/` | [disinfo-radar](https://github.com/Avalon2222/disinfo-radar) | `hoaks_turnbackhoax.csv` | Arsip artikel cek fakta Turnbackhoax sejak 2015: judul, label, kategori, tanggal | Turnbackhoax / Mafindo (halaman daftar artikel publik) |
| `who-uses-palantir/` | [who-uses-palantir](https://github.com/Avalon2222/who-uses-palantir) | `pengguna_palantir.csv`, `kontroversi.csv`, `pendapatan_palantir.csv` | 48 lembaga pemakai Palantir di 19 negara + 3 organisasi internasional, 26 kontroversi, pendapatan Palantir 2019-2025 per segmen dan wilayah | Kurasi dari sumber publik (pengumuman resmi, pengadaan, media); SEC EDGAR 10-K |
| `palantir-contracts/` | [palantir-contracts](https://github.com/Avalon2222/palantir-contracts) | `as_transaksi.csv`, `as_idv.csv`, `uk_kontrak.csv` | 1.807 transaksi kontrak federal AS ke Palantir 2008-2026, 37 kontrak payung dengan plafon, 29 pengumuman kontrak sektor publik Inggris | USAspending.gov API; Contracts Finder API (OGL v3.0) |
| `ontology-playground/` | [ontology-playground](https://github.com/Avalon2222/ontology-playground) | `pelayaran_lengkap.csv` | 520 pelayaran sintetis 2024-2026 (kapal, pemilik, asal, tujuan, komoditas, pengirim, muatan); pelabuhan dan komoditas nyata, kapal dan perusahaan fiktif dengan seed tetap | Dibangkitkan `scripts/bangun_data.py` di repo asal |
| `pltr-war-index/` | [pltr-war-index](https://github.com/Avalon2222/pltr-war-index) | `harga_saham.csv`, `peristiwa_perang.csv` | Harga harian PLTR, SPY, QQQ, ITA, LMT, NOC, RTX, GD sejak IPO Palantir 2020; 48 peristiwa perang, serangan AS, dan gencatan senjata 2020-2026 | Yahoo Finance; kurasi manual dengan tautan sumber per peristiwa |
| `gotham-lite/` | [gotham-lite](https://github.com/Avalon2222/gotham-lite) | `simpul.csv.gz`, `kapal_tersanksi.csv` | 84.735 entitas graf keterkaitan OpenSanctions (orang, perusahaan, kapal, pesawat; tersanksi atau terhubung ke yang tersanksi) dan ringkasan 2.041 kapal tersanksi dengan pemilik/operator tercatat | OpenSanctions, koleksi default (CC BY-NC 4.0) |

Catatan:

- File JSON gempa diratakan menjadi tabel saat dimuat (`katalog._baca_usgs`, `katalog._baca_bmkg`).
- `snapshots.csv` mendapat tiga kolom turunan saat dimuat: `waktu` (dari epoch), `maskapai`, dan
  `negara_maskapai` (tebakan dari callsign, modul `src/maskapai.py`).
- File `.csv.gz` dibaca langsung oleh pandas; file pendukung (`provinsi.geojson`, `kapal_statis.csv`,
  `kode_negara.csv`) ikut disinkronkan karena dipakai kolom turunan.
- Kolom turunan proyek baru: `provinsi` untuk titik api (ray casting ke poligon 38 provinsi, `src/wilayah.py`;
  di luar poligon = "Laut / luar negeri"), `bendera`, `kategori`, `status_navigasi` untuk kapal (`src/mmsi.py`),
  `negara`, `militer`, `kategori` untuk satelit, dan `kategori_ispu` dari PM2.5 per jam.
- Hanya kolom yang tercantum di `katalog.py` yang dibawa ke chatbot; kolom lain di file asal diabaikan
  supaya skema yang dikirim ke model tetap ringkas.
- Semua kolom waktu diubah ke UTC tanpa zona waktu.
