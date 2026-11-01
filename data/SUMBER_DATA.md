# Sumber data

Semua file di folder ini adalah **salinan** dari repo proyek lain di akun yang sama, diambil dengan
`python scripts/sinkron_data.py` (dari GitHub) atau `--lokal ..` (dari clone di folder induk). Daftar file,
path asal, dan arti kolom ada di satu tempat: `src/katalog.py`. Dokumentasi asli tiap dataset ada di
`data/SUMBER_DATA.md` repo masing-masing.

| Folder | Repo asal | File | Isi | Sumber asli |
|---|---|---|---|---|
| `dc-impact-dashboard/` | [dc-impact-dashboard](https://github.com/Avalon2222/dc-impact-dashboard) | `data_center_indonesia.csv`, `parameter_asumsi.csv` | 27 pusat data, parameter PUE/WUE | Liputan industri, pernyataan operator, Uptime Institute |
| `btc-news-volatility/` | [btc-news-volatility](https://github.com/Avalon2222/btc-news-volatility) | `btc_harga_harian.csv`, `berita_besar.csv` | Harga harian BTC-USD sejak 2020, 102 peristiwa | Coinbase, kurasi manual dari Wikipedia/berita |
| `indonesia-defense-gis/` | [indonesia-defense-gis](https://github.com/Avalon2222/indonesia-defense-gis) | `markas_tni.csv`, `pangkalan_asing.csv`, `pulau_terluar_perbatasan.csv`, `alki.csv`, `anggaran_indonesia.csv`, `anggaran_kawasan.csv`, `alutsista.csv` | Geografi dan anggaran pertahanan | Wikipedia, SIPRI, IISS, Kemenkeu |
| `ring-of-fire-pulse/` | [ring-of-fire-pulse](https://github.com/Avalon2222/ring-of-fire-pulse) | `usgs.json`, `bmkg_terkini.json`, `gunung_api.csv`, `magma_level.csv` | Gempa 30 hari, 15 gempa M≥5 BMKG, 69 gunung api + level | USGS FDSN, BMKG, MAGMA ESDM, Smithsonian GVP |
| `who-owns-the-sky/` | [who-owns-the-sky](https://github.com/Avalon2222/who-owns-the-sky) | `snapshots.csv`, `bandara.csv` | ±60 snapshot posisi pesawat, 36 bandara | OpenSky Network (ADS-B) |
| `follow-the-money/` | [follow-the-money](https://github.com/Avalon2222/follow-the-money) | `apbd_provinsi.csv`, `penduduk_provinsi.csv` | APBD 38 provinsi 2022-2025 per akun, penduduk 2025 | DJPK Kemenkeu (SIKD), BPS |
| `btc-whale-watch/` | [btc-whale-watch](https://github.com/Avalon2222/btc-whale-watch) | `transaksi_paus.csv`, `blok.csv`, `btc_harga_5menit.csv` | 9.130 transaksi ≥ 50 BTC (28-31 Okt 2026), 428 blok, candle 5 menit | mempool.space, blockchain.info, Coinbase |

Catatan:

- File JSON gempa diratakan menjadi tabel saat dimuat (`katalog._baca_usgs`, `katalog._baca_bmkg`).
- `snapshots.csv` mendapat tiga kolom turunan saat dimuat: `waktu` (dari epoch), `maskapai`, dan
  `negara_maskapai` (tebakan dari callsign, modul `src/maskapai.py`).
- Hanya kolom yang tercantum di `katalog.py` yang dibawa ke chatbot; kolom lain di file asal diabaikan
  supaya skema yang dikirim ke model tetap ringkas.
- Semua kolom waktu diubah ke UTC tanpa zona waktu.
