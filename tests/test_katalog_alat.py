"""
Tes untuk src/katalog.py, src/alat.py, src/grafik.py, dan scripts/sinkron_data.py dengan
snapshot data di data/. Tanpa internet dan tanpa API key.
"""

import json

import pandas as pd
import plotly.graph_objects as go
import pytest

from scripts import sinkron_data
from src import alat, grafik, katalog, query


# --- katalog ----------------------------------------------------------------

@pytest.mark.parametrize("id", list(katalog.DATASET))
def test_semua_dataset_bisa_dimuat(id):
    d = katalog.DATASET[id]
    df = katalog.muat(id)
    assert len(df) > 0
    assert set(df.columns) <= set(d.kolom), "ada kolom yang tidak dijelaskan di katalog"
    for k in d.waktu:
        assert pd.api.types.is_datetime64_any_dtype(df[k]) and df[k].dt.tz is None
        assert df[k].notna().all()


def test_id_dataset_unik_dan_prompt_ringkas():
    assert len(katalog.DATASET) == sum(len(p.dataset) for p in katalog.PROYEK.values())
    skema = katalog.skema_ringkas()
    for id in katalog.DATASET:
        assert f"`{id}`" in skema
    prompt = alat.prompt_sistem()
    assert "query_data" in prompt and len(prompt) < 9000  # ≈ 2.200 token; tier gratis dibatasi per menit


def test_turunan_pesawat():
    df = katalog.muat("pesawat")
    assert {"maskapai", "negara_maskapai", "waktu"} <= set(df.columns)
    assert df.loc[df["callsign"].astype(str).str.startswith("GIA"), "maskapai"].eq("Garuda Indonesia").all()


def test_gempa_dari_json():
    usgs, bmkg = katalog.muat("gempa_usgs"), katalog.muat("gempa_bmkg")
    assert usgs["magnitudo"].between(2.5, 10).all() and usgs["lat"].between(-12, 7).all()
    assert bmkg["kedalaman_km"].gt(0).all() and bmkg["lon"].between(94, 142).all()


def test_deskripsi_dataset():
    teks = katalog.deskripsi_dataset("magma_level")
    assert "69 baris" in teks and "status" in teks and "Siaga" in teks
    with pytest.raises(ValueError, match="tidak ada"):
        katalog.deskripsi_dataset("rahasia")
    with pytest.raises(ValueError, match="tidak ada"):
        katalog.muat("rahasia")


def test_info_snapshot_lengkap():
    info = katalog.info_snapshot()
    assert len(info) == len(katalog.DATASET)
    assert all(i["baris"] > 0 for i in info)


# --- alat -------------------------------------------------------------------

def test_definisi_alat_valid_json():
    json.dumps(alat.DEFINISI)
    nama = {t["function"]["name"] for t in alat.DEFINISI}
    assert nama == {"query_data", "describe_dataset"}
    enum = alat.DEFINISI[1]["function"]["parameters"]["properties"]["dataset"]["enum"]
    assert set(enum) == set(katalog.DATASET)


def test_query_data_belanja_terbesar():
    a = alat.Alat()
    teks, lamp = a.jalankan("query_data", {
        "dataset": "apbd_provinsi",
        "filter": [{"kolom": "akun", "op": "==", "nilai": "Belanja Daerah"}, {"kolom": "tahun", "op": "==", "nilai": 2024}],
        "kolom": ["provinsi", "realisasi"], "urut": {"kolom": "realisasi", "turun": True}, "limit": 3,
        "grafik": {"jenis": "bar", "x": "provinsi", "y": "realisasi"},
    })
    assert teks.startswith("Dataset apbd_provinsi (proyek Follow the Money): 3 baris")
    assert lamp.hasil["provinsi"].iloc[0] == "Jawa Barat"
    assert lamp.grafik["jenis"] == "bar" and lamp.url_repo.endswith("/follow-the-money")
    assert isinstance(grafik.buat(lamp.hasil, lamp.grafik), go.Figure)


def test_query_data_galat_untuk_llm():
    a = alat.Alat()
    with pytest.raises(ValueError, match="Dataset 'x' tidak ada"):
        a.jalankan("query_data", {"dataset": "x"})
    with pytest.raises(query.GalatQuery, match="Kolom 'mag'"):
        a.jalankan("query_data", {"dataset": "gempa_usgs", "filter": [{"kolom": "mag", "op": ">", "nilai": 5}]})
    with pytest.raises(grafik.GalatGrafik, match="tidak ada di hasil"):
        a.jalankan("query_data", {"dataset": "gunung_api", "grafik": {"jenis": "bar", "x": "nama", "y": "tinggi"}})
    with pytest.raises(ValueError, match="tidak dikenal"):
        a.jalankan("hapus_semua", {})


def test_query_data_kosong_memberi_petunjuk():
    teks, lamp = alat.Alat().jalankan("query_data", {
        "dataset": "data_center", "filter": [{"kolom": "provinsi", "op": "==", "nilai": "Atlantis"}],
        "grafik": {"jenis": "peta"},
    })
    assert "Tidak ada baris" in teks and lamp.hasil.empty and lamp.grafik is None


def test_describe_lewat_alat():
    teks, lamp = alat.Alat().jalankan("describe_dataset", {"dataset": "anggaran_kawasan"})
    assert "Indonesia" in teks and lamp is None


# --- grafik -----------------------------------------------------------------

def test_grafik_semua_jenis():
    df = pd.DataFrame({"kat": list("abcdefghij"), "nilai": range(10, 0, -1), "lain": range(10),
                       "lat": [-6.0 + i * 0.1 for i in range(10)], "lon": [106.0 + i for i in range(10)],
                       "waktu": pd.date_range("2024-01-01", periods=10, freq="D")})
    assert isinstance(grafik.buat(df, {"jenis": "bar", "x": "kat", "y": "nilai", "judul": "t"}), go.Figure)
    assert isinstance(grafik.buat(df, {"jenis": "bar", "x": "kat", "y": ["nilai", "lain"]}), go.Figure)
    assert isinstance(grafik.buat(df, {"jenis": "line", "x": "waktu", "y": "nilai"}), go.Figure)
    assert isinstance(grafik.buat(df, {"jenis": "scatter", "x": "nilai", "y": "lain", "ukuran": "nilai", "label": "kat"}), go.Figure)
    pie = grafik.buat(df, {"jenis": "pie", "x": "kat", "y": "nilai"})
    assert "Lainnya" in list(pie.data[0].labels)  # kategori ke-9 dst. dilipat
    assert len(pie.data[0].labels) == grafik.MAKS_KATEGORI_PIE
    peta = grafik.buat(df, {"jenis": "peta", "ukuran": "nilai", "label": "kat"})
    assert peta.data[0].type == "scattermap"


def test_grafik_periksa_galat():
    df = pd.DataFrame({"a": [1], "b": [2]})
    with pytest.raises(grafik.GalatGrafik, match="Jenis"):
        grafik.periksa(df, {"jenis": "radar", "x": "a", "y": "b"})
    with pytest.raises(grafik.GalatGrafik, match="butuh 'x' dan 'y'"):
        grafik.periksa(df, {"jenis": "bar", "x": "a"})
    with pytest.raises(grafik.GalatGrafik, match="untuk lat"):
        grafik.periksa(df, {"jenis": "peta"})
    with pytest.raises(grafik.GalatGrafik, match="kosong"):
        grafik.buat(df.iloc[0:0], {"jenis": "bar", "x": "a", "y": "b"})


# --- sinkron ----------------------------------------------------------------

def test_url_sumber():
    d = katalog.DATASET["gempa_usgs"]
    assert sinkron_data.url_sumber(d) == "https://raw.githubusercontent.com/Avalon2222/ring-of-fire-pulse/main/data/sample/usgs.json"
    assert sinkron_data.url_sumber(katalog.DATASET["apbd_provinsi"]).endswith("/follow-the-money/main/data/apbd_provinsi.csv")


def test_salin_lokal(tmp_path, monkeypatch):
    d = katalog.DATASET["alki"]
    akar = tmp_path / "clones"
    (akar / d.proyek / "data").mkdir(parents=True)
    (akar / d.proyek / d.asal).write_text("alki,urutan,lat,lon,keterangan\nX,1,0,0,uji\n")
    tujuan = tmp_path / "data" / d.proyek / d.file
    monkeypatch.setattr(katalog.Dataset, "path", property(lambda self: tujuan))
    assert sinkron_data.salin_lokal(d, akar) > 0
    assert tujuan.read_text().startswith("alki,")
    with pytest.raises(FileNotFoundError):
        sinkron_data.salin_lokal(d, tmp_path / "kosong")
