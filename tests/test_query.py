"""
Tes untuk src/query.py: tiap tahap query terstruktur dengan DataFrame mini yang hasilnya
bisa dihitung di kepala.
"""

import pandas as pd
import pytest

from src import query


@pytest.fixture
def df():
    return pd.DataFrame({
        "provinsi": ["Aceh", "Bali", "Aceh", "Bali", "Jawa Barat"],
        "tahun": [2022, 2022, 2023, 2023, 2023],
        "waktu": pd.to_datetime(["2022-01-05", "2022-06-10", "2023-02-01", "2023-02-20", "2023-11-30"]),
        "anggaran": [100.0, 200.0, 110.0, 220.0, 500.0],
        "realisasi": [90.0, 210.0, 100.0, 210.0, 450.0],
        "aktif": [True, False, True, True, False],
    })


# --- filter -----------------------------------------------------------------

def test_filter_sama_tidak_peduli_huruf(df):
    hasil = query.saring(df, [{"kolom": "provinsi", "op": "==", "nilai": "aceh"}])
    assert len(hasil) == 2


def test_filter_angka_dan_tanggal(df):
    assert len(query.saring(df, [{"kolom": "anggaran", "op": ">=", "nilai": "200"}])) == 3
    assert len(query.saring(df, [{"kolom": "waktu", "op": ">", "nilai": "2023-01-01"}])) == 3
    assert len(query.saring(df, [{"kolom": "waktu", "op": "between", "nilai": ["2022-01-01", "2022-12-31"]}])) == 2


def test_filter_in_contains_boolean(df):
    assert len(query.saring(df, [{"kolom": "provinsi", "op": "in", "nilai": ["Bali", "jawa barat"]}])) == 3
    assert len(query.saring(df, [{"kolom": "provinsi", "op": "not_in", "nilai": "Bali"}])) == 3
    assert len(query.saring(df, [{"kolom": "provinsi", "op": "contains", "nilai": "jawa"}])) == 1
    assert len(query.saring(df, [{"kolom": "aktif", "op": "==", "nilai": "true"}])) == 3


def test_filter_kolom_salah_menyebut_kolom_tersedia(df):
    with pytest.raises(query.GalatQuery, match="provinsi, tahun"):
        query.saring(df, [{"kolom": "propinsi", "op": "==", "nilai": "Aceh"}])
    with pytest.raises(query.GalatQuery, match="Operator"):
        query.saring(df, [{"kolom": "tahun", "op": "like", "nilai": 2022}])
    with pytest.raises(query.GalatQuery, match="bukan angka"):
        query.saring(df, [{"kolom": "tahun", "op": "==", "nilai": "dua ribu"}])


# --- hitung -----------------------------------------------------------------

def test_hitung_rumus_sederhana(df):
    hasil = query.hitung(df, [{"nama": "rasio", "rumus": "realisasi / anggaran * 100"}])
    assert hasil["rasio"].iloc[0] == pytest.approx(90.0)
    assert "rasio" not in df.columns  # DataFrame asal tidak diubah


@pytest.mark.parametrize("rumus", ["__import__('os')", "anggaran.sum()", "anggaran[0]", "@x + 1", "'a'"])
def test_hitung_menolak_rumus_mencurigakan(df, rumus):
    with pytest.raises(query.GalatQuery):
        query.hitung(df, [{"nama": "x", "rumus": rumus}])


def test_hitung_nama_tidak_valid(df):
    with pytest.raises(query.GalatQuery, match="Nama kolom"):
        query.hitung(df, [{"nama": "dua kata", "rumus": "anggaran * 2"}])


# --- agregasi ---------------------------------------------------------------

def test_agregasi_per_kelompok(df):
    hasil = query.agregasi(df, ["provinsi"], [{"kolom": "anggaran", "fungsi": "sum", "alias": "total"}, {"fungsi": "count"}])
    hasil = hasil.set_index("provinsi")
    assert hasil.loc["Aceh", "total"] == 210.0
    assert hasil.loc["Bali", "jumlah"] == 2
    assert list(hasil.columns) == ["total", "jumlah"]


def test_agregasi_tanpa_kelompok_satu_baris(df):
    hasil = query.agregasi(df, [], [{"kolom": "realisasi", "fungsi": "max"}, {"kolom": "provinsi", "fungsi": "nunique"}])
    assert len(hasil) == 1
    assert hasil["max_realisasi"].iloc[0] == 450.0
    assert hasil["nunique_provinsi"].iloc[0] == 3


def test_agregasi_bucket_waktu(df):
    per_tahun = query.agregasi(df, ["waktu:tahun"], [{"fungsi": "count"}])
    assert per_tahun["tahun"].tolist() == [2022, 2023]
    assert per_tahun["jumlah"].tolist() == [2, 3]
    per_bulan = query.agregasi(df, ["waktu:bulan"], [])
    assert per_bulan["bulan"].tolist() == ["2022-01", "2022-06", "2023-02", "2023-11"]
    assert per_bulan.loc[per_bulan["bulan"] == "2023-02", "jumlah"].iloc[0] == 2


def test_agregasi_galat_jelas(df):
    with pytest.raises(query.GalatQuery, match="bukan angka"):
        query.agregasi(df, ["tahun"], [{"kolom": "provinsi", "fungsi": "sum"}])
    with pytest.raises(query.GalatQuery, match="Bucket"):
        query.agregasi(df, ["waktu:minggu"], [])
    with pytest.raises(query.GalatQuery, match="bukan tanggal"):
        query.agregasi(df, ["provinsi:tahun"], [])
    with pytest.raises(query.GalatQuery, match="Fungsi"):
        query.agregasi(df, ["provinsi"], [{"kolom": "anggaran", "fungsi": "variance"}])


# --- jalankan (semua tahap) --------------------------------------------------

def test_jalankan_lengkap(df):
    spek = {
        "filter": [{"kolom": "tahun", "op": "==", "nilai": 2023}],
        "hitung": [{"nama": "rasio", "rumus": "realisasi / anggaran"}],
        "kelompok": ["provinsi"],
        "agregasi": [{"kolom": "rasio", "fungsi": "mean", "alias": "rasio"}],
        "urut": {"kolom": "rasio", "turun": True},
        "limit": 2,
    }
    hasil = query.jalankan(df, spek)
    assert hasil["provinsi"].tolist() == ["Bali", "Aceh"]  # 210/220 > 100/110
    assert len(hasil) == 2


def test_jalankan_pilih_kolom_dan_limit_dibatasi(df):
    hasil = query.jalankan(df, {"kolom": ["provinsi", "anggaran"], "limit": 99999})
    assert list(hasil.columns) == ["provinsi", "anggaran"]
    assert len(hasil) == 5
    assert query.jalankan(df, {"limit": 0}).shape[0] == 1  # limit minimal 1
    with pytest.raises(query.GalatQuery):
        query.jalankan(df, {"limit": "banyak"})
    with pytest.raises(query.GalatQuery):
        query.jalankan(df, ["bukan", "objek"])


def test_ke_teks_aman_untuk_json(df):
    teks = query.ke_teks(df, maks_baris=2)
    assert teks.startswith("5 baris, kolom: provinsi")
    assert "Hanya 2 baris pertama" in teks
    assert '"waktu": "2022-01-05 00:00:00"' in teks
    catatan = query.ke_catatan(pd.DataFrame({"a": [1.23456789, float("nan")]}))
    assert catatan == [{"a": 1.2346}, {"a": None}]
