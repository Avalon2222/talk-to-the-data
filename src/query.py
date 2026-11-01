"""
query.py - Menjalankan "query terstruktur" di atas DataFrame pandas.

Chatbot ini tidak pernah menjalankan kode Python bebas yang ditulis LLM; di aplikasi publik
itu sama dengan membuka pintu rumah lebar-lebar. Sebagai gantinya LLM mengirim spesifikasi
JSON kecil (filter, kolom hitung, kelompok, agregasi, urutan, limit) dan modul ini yang
menerjemahkannya menjadi operasi pandas yang sudah dibatasi.

Semua fungsi di sini murni: DataFrame masuk, DataFrame keluar, tidak menyentuh file atau
jaringan, sehingga mudah diuji (lihat tests/test_query.py).

Contoh spesifikasi:

    {
      "filter":   [{"kolom": "provinsi", "op": "==", "nilai": "Jawa Barat"}],
      "hitung":   [{"nama": "per_kapita", "rumus": "anggaran / penduduk_2025"}],
      "kelompok": ["tahun"],
      "agregasi": [{"kolom": "anggaran", "fungsi": "sum", "alias": "total"}],
      "urut":     {"kolom": "total", "turun": true},
      "limit":    10
    }
"""

from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

OPERATOR = ("==", "!=", ">", ">=", "<", "<=", "in", "not_in", "contains", "between")
FUNGSI = ("sum", "mean", "count", "min", "max", "median", "nunique", "first", "last")
BUCKET = ("tahun", "bulan", "hari", "jam", "hari_minggu")
LIMIT_DEFAULT = 50
LIMIT_MAKS = 500

_POLA_RUMUS = re.compile(r"^[\w\s\.\+\-\*/\(\)%]+$")
_POLA_NAMA = re.compile(r"^[A-Za-z_]\w*$")


class GalatQuery(ValueError):
    """Spesifikasi query tidak valid. Pesannya ditulis agar LLM bisa memperbaiki sendiri."""


# ---------------------------------------------------------------------------
# Bantuan
# ---------------------------------------------------------------------------

def _cek_kolom(df: pd.DataFrame, nama: str, konteks: str = "") -> None:
    if nama not in df.columns:
        raise GalatQuery(
            f"Kolom '{nama}' tidak ada{(' di ' + konteks) if konteks else ''}. "
            f"Kolom yang tersedia: {', '.join(map(str, df.columns))}."
        )


def _paksa_nilai(seri: pd.Series, nilai: Any) -> Any:
    """Ubah nilai dari JSON ke tipe kolom (angka, tanggal, atau teks)."""
    if pd.api.types.is_datetime64_any_dtype(seri):
        return pd.to_datetime(nilai)
    if pd.api.types.is_bool_dtype(seri):
        if isinstance(nilai, str):
            return nilai.strip().lower() in ("true", "1", "ya", "yes")
        return bool(nilai)
    if pd.api.types.is_numeric_dtype(seri):
        try:
            return float(nilai)
        except (TypeError, ValueError):
            raise GalatQuery(f"Kolom '{seri.name}' berisi angka, tetapi nilai filter '{nilai}' bukan angka.")
    return str(nilai)


# ---------------------------------------------------------------------------
# Tahap 1: filter
# ---------------------------------------------------------------------------

def saring(df: pd.DataFrame, daftar_filter: list[dict]) -> pd.DataFrame:
    for f in daftar_filter:
        kolom, op, nilai = f.get("kolom"), f.get("op", "=="), f.get("nilai")
        if not kolom:
            raise GalatQuery("Setiap filter butuh 'kolom'.")
        _cek_kolom(df, kolom, "filter")
        if op not in OPERATOR:
            raise GalatQuery(f"Operator '{op}' tidak dikenal. Pakai salah satu: {', '.join(OPERATOR)}.")
        seri = df[kolom]

        if op == "contains":
            df = df[seri.astype(str).str.contains(str(nilai), case=False, regex=False, na=False)]
        elif op in ("in", "not_in"):
            if not isinstance(nilai, list):
                nilai = [nilai]
            daftar = [_paksa_nilai(seri, n) for n in nilai]
            if pd.api.types.is_string_dtype(seri) or seri.dtype == object:
                # Teks dibandingkan tanpa peduli huruf besar/kecil.
                cocok = seri.astype(str).str.lower().isin([str(n).lower() for n in daftar])
            else:
                cocok = seri.isin(daftar)
            df = df[cocok] if op == "in" else df[~cocok]
        elif op == "between":
            if not isinstance(nilai, list) or len(nilai) != 2:
                raise GalatQuery("Operator 'between' butuh nilai berupa list dua elemen [bawah, atas].")
            bawah, atas = (_paksa_nilai(seri, n) for n in nilai)
            df = df[(seri >= bawah) & (seri <= atas)]
        else:
            v = _paksa_nilai(seri, nilai)
            if (pd.api.types.is_string_dtype(seri) or seri.dtype == object) and op in ("==", "!="):
                cocok = seri.astype(str).str.lower() == str(v).lower()
                df = df[cocok] if op == "==" else df[~cocok]
            else:
                df = df[{
                    "==": seri == v, "!=": seri != v, ">": seri > v,
                    ">=": seri >= v, "<": seri < v, "<=": seri <= v,
                }[op]]
    return df


# ---------------------------------------------------------------------------
# Tahap 2: kolom hitung
# ---------------------------------------------------------------------------

def hitung(df: pd.DataFrame, daftar_hitung: list[dict]) -> pd.DataFrame:
    """Tambahkan kolom baru dari rumus aritmetika sederhana, misalnya 'realisasi / anggaran * 100'."""
    if not daftar_hitung:
        return df
    df = df.copy()
    for h in daftar_hitung:
        nama, rumus = h.get("nama"), h.get("rumus", "")
        if not nama or not _POLA_NAMA.match(nama):
            raise GalatQuery(f"Nama kolom hitung '{nama}' tidak valid (huruf, angka, garis bawah; tanpa spasi).")
        if not rumus or not _POLA_RUMUS.match(rumus):
            raise GalatQuery(
                f"Rumus '{rumus}' ditolak. Hanya boleh nama kolom, angka, dan operator + - * / % ( )."
            )
        for token in re.findall(r"[A-Za-z_]\w*", rumus):
            _cek_kolom(df, token, f"rumus '{rumus}'")
        try:
            df[nama] = df.eval(rumus)
        except Exception as e:  # pembagian kolom teks, dsb.
            raise GalatQuery(f"Rumus '{rumus}' gagal dihitung: {e}") from e
    return df


# ---------------------------------------------------------------------------
# Tahap 3: kelompok + agregasi
# ---------------------------------------------------------------------------

def _kunci_kelompok(df: pd.DataFrame, kunci: str) -> tuple[str, pd.Series]:
    """'waktu:bulan' → ('bulan', seri bulan). 'provinsi' → ('provinsi', kolomnya)."""
    if ":" in kunci:
        kolom, bucket = kunci.split(":", 1)
        _cek_kolom(df, kolom, "kelompok")
        if bucket not in BUCKET:
            raise GalatQuery(f"Bucket waktu '{bucket}' tidak dikenal. Pakai: {', '.join(BUCKET)}.")
        seri = df[kolom]
        if not pd.api.types.is_datetime64_any_dtype(seri):
            raise GalatQuery(f"Kolom '{kolom}' bukan tanggal/waktu, tidak bisa dipotong per {bucket}.")
        if bucket == "tahun":
            return "tahun", seri.dt.year
        if bucket == "bulan":
            return "bulan", seri.dt.strftime("%Y-%m")
        if bucket == "hari":
            return "hari", seri.dt.floor("D")
        if bucket == "jam":
            return "jam", seri.dt.floor("h")
        return "hari_minggu", seri.dt.day_name()
    _cek_kolom(df, kunci, "kelompok")
    return kunci, df[kunci]


def agregasi(df: pd.DataFrame, kelompok: list[str], daftar_agregasi: list[dict]) -> pd.DataFrame:
    kunci_nama: list[str] = []
    kunci_seri: list[pd.Series] = []
    for k in kelompok:
        nama, seri = _kunci_kelompok(df, k)
        kunci_nama.append(nama)
        kunci_seri.append(seri.rename(nama))

    spesifikasi: dict[str, tuple[str, str]] = {}
    hitung_baris: str | None = None
    for a in daftar_agregasi:
        fungsi = a.get("fungsi", "count")
        if fungsi not in FUNGSI:
            raise GalatQuery(f"Fungsi agregasi '{fungsi}' tidak dikenal. Pakai: {', '.join(FUNGSI)}.")
        kolom = a.get("kolom")
        if fungsi == "count" and kolom in (None, "", "*"):
            hitung_baris = a.get("alias") or "jumlah"
            continue
        _cek_kolom(df, kolom, "agregasi")
        if fungsi in ("sum", "mean", "median") and not pd.api.types.is_numeric_dtype(df[kolom]):
            raise GalatQuery(f"Kolom '{kolom}' bukan angka, tidak bisa di-{fungsi}. Pakai count/nunique/min/max.")
        alias = a.get("alias") or f"{fungsi}_{kolom}"
        spesifikasi[alias] = (kolom, fungsi)
    if not spesifikasi and hitung_baris is None:
        hitung_baris = "jumlah"

    if not kunci_seri:
        hasil: dict[str, Any] = {}
        for alias, (kolom, fungsi) in spesifikasi.items():
            hasil[alias] = getattr(df[kolom], fungsi)()
        if hitung_baris:
            hasil[hitung_baris] = len(df)
        return pd.DataFrame([hasil])

    grup = df.groupby(kunci_seri, dropna=False, observed=True, sort=True)
    bagian = []
    if spesifikasi:
        bagian.append(grup.agg(**spesifikasi))
    if hitung_baris:
        bagian.append(grup.size().rename(hitung_baris))
    hasil_df = pd.concat(bagian, axis=1).reset_index()
    return hasil_df


# ---------------------------------------------------------------------------
# Tahap 4: urut + limit, dan pintu masuk utama
# ---------------------------------------------------------------------------

def urutkan(df: pd.DataFrame, urut: dict | None) -> pd.DataFrame:
    if not urut:
        return df
    kolom = urut.get("kolom")
    if not kolom:
        return df
    _cek_kolom(df, kolom, "urut")
    return df.sort_values(kolom, ascending=not bool(urut.get("turun", False)), kind="mergesort")


def jalankan(df: pd.DataFrame, spek: dict) -> pd.DataFrame:
    """Jalankan seluruh tahap. Mengembalikan DataFrame baru, maksimal LIMIT_MAKS baris."""
    if not isinstance(spek, dict):
        raise GalatQuery("Spesifikasi query harus berupa objek JSON.")
    df = saring(df, spek.get("filter") or [])
    df = hitung(df, spek.get("hitung") or [])
    kelompok = spek.get("kelompok") or []
    daftar_agregasi = spek.get("agregasi") or []
    if kelompok or daftar_agregasi:
        df = agregasi(df, kelompok, daftar_agregasi)
    elif spek.get("kolom"):
        for k in spek["kolom"]:
            _cek_kolom(df, k, "kolom")
        df = df[list(spek["kolom"])]
    df = urutkan(df, spek.get("urut"))
    try:
        limit = LIMIT_DEFAULT if spek.get("limit") is None else int(spek["limit"])
    except (TypeError, ValueError):
        raise GalatQuery("'limit' harus berupa angka.")
    limit = max(1, min(limit, LIMIT_MAKS))
    return df.head(limit).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Serialisasi hasil untuk dibaca LLM
# ---------------------------------------------------------------------------

def ke_catatan(df: pd.DataFrame, maks_baris: int = 40) -> list[dict]:
    """DataFrame → list of dict yang aman di-JSON-kan (tanggal jadi teks, float dibulatkan)."""
    potongan = df.head(maks_baris)
    catatan = []
    for baris in potongan.itertuples(index=False):
        d: dict[str, Any] = {}
        for kolom, nilai in zip(potongan.columns, baris):
            if isinstance(nilai, pd.Timestamp):
                d[kolom] = nilai.isoformat(sep=" ")
            elif isinstance(nilai, float):
                d[kolom] = None if pd.isna(nilai) else round(nilai, 4)
            elif hasattr(nilai, "item"):  # numpy scalar
                d[kolom] = nilai.item()
            elif nilai is pd.NaT or (nilai is not None and not isinstance(nilai, (str, bool, int)) and pd.isna(nilai)):
                d[kolom] = None
            else:
                d[kolom] = nilai
        catatan.append(d)
    return catatan


def ke_teks(df: pd.DataFrame, maks_baris: int = 40) -> str:
    """Ringkasan hasil query sebagai teks untuk LLM: jumlah baris, lalu baris-barisnya dalam JSON."""
    catatan = ke_catatan(df, maks_baris)
    keterangan = f"{len(df)} baris, kolom: {', '.join(map(str, df.columns))}."
    if len(df) > maks_baris:
        keterangan += f" Hanya {maks_baris} baris pertama yang ditampilkan di sini."
    return keterangan + "\n" + json.dumps(catatan, ensure_ascii=False, default=str)
