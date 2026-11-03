"""
alat.py - "Alat" (tools) yang boleh dipanggil LLM, beserta prompt sistem.

Hanya ada dua alat, dan keduanya hanya MEMBACA:
- describe_dataset: profil kolom satu dataset (nilai unik, rentang angka/waktu).
- query_data: query terstruktur (filter → hitung → kelompok/agregasi → urut → limit) + grafik opsional.

LLM tidak pernah menerima DataFrame, hanya teks ringkas hasil query. DataFrame dan spesifikasi
grafiknya disimpan sebagai `Lampiran` supaya app bisa menggambar ulang dan menampilkan sumber.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

import pandas as pd

from src import grafik, katalog, query

MAKS_BARIS_KE_LLM = 40


@dataclass
class Lampiran:
    dataset: str
    proyek: str
    spek: dict
    hasil: pd.DataFrame
    grafik: dict | None = None

    @property
    def judul_proyek(self) -> str:
        return katalog.PROYEK[self.proyek].judul

    @property
    def url_repo(self) -> str:
        return katalog.PROYEK[self.proyek].url_repo

    @property
    def url_app(self) -> str:
        return katalog.PROYEK[self.proyek].url_app


_SKEMA_FILTER = {
    "type": "array",
    "description": "Baris yang dipertahankan. Semua filter digabung dengan AND.",
    "items": {
        "type": "object",
        "properties": {
            "kolom": {"type": "string"},
            "op": {"type": "string", "enum": list(query.OPERATOR),
                   "description": "contains = teks mengandung (tanpa peduli huruf besar); in/not_in = nilai berupa list; between = [bawah, atas]"},
            "nilai": {"description": "angka, teks, tanggal ISO (YYYY-MM-DD), atau list untuk in/between"},
        },
        "required": ["kolom", "op", "nilai"],
    },
}

_SKEMA_GRAFIK = {
    "type": "object",
    "description": "Opsional. Gambar hasil query. Kolom yang disebut harus ada di HASIL (setelah agregasi).",
    "properties": {
        "jenis": {"type": "string", "enum": list(grafik.JENIS),
                  "description": "bar = perbandingan kategori, line = tren waktu, scatter = hubungan dua angka, pie = komposisi (≤ 8), peta = titik lat/lon"},
        "x": {"type": "string"},
        "y": {"description": "satu nama kolom, atau list beberapa kolom angka", "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
        "warna": {"type": "string", "description": "kolom kategori untuk membedakan seri (opsional)"},
        "ukuran": {"type": "string", "description": "kolom angka untuk ukuran titik (scatter/peta, opsional)"},
        "label": {"type": "string", "description": "kolom teks untuk nama saat hover (opsional)"},
        "judul": {"type": "string"},
        "lat": {"type": "string", "description": "kolom lintang (peta), default 'lat'"},
        "lon": {"type": "string", "description": "kolom bujur (peta), default 'lon'"},
    },
    "required": ["jenis"],
}

DEFINISI: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "describe_dataset",
            "description": "Profil kolom satu dataset: tipe, nilai unik kolom teks, rentang angka dan waktu, jumlah baris. "
                           "Panggil ini bila perlu tahu ejaan nilai yang tepat sebelum memfilter.",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string", "enum": list(katalog.DATASET)}},
                "required": ["dataset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_data",
            "description": "Jalankan query terstruktur pada satu dataset: filter → kolom hitung → kelompok + agregasi → urut → limit. "
                           "Hasil dikembalikan sebagai baris JSON (maks 40 ditampilkan). Sertakan 'grafik' bila jawaban layak digambar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset": {"type": "string", "enum": list(katalog.DATASET)},
                    "filter": _SKEMA_FILTER,
                    "hitung": {
                        "type": "array",
                        "description": "Kolom baru dari rumus aritmetika antar kolom, misalnya {'nama': 'per_kapita', 'rumus': 'realisasi / penduduk_2025'}.",
                        "items": {"type": "object", "properties": {"nama": {"type": "string"}, "rumus": {"type": "string"}},
                                  "required": ["nama", "rumus"]},
                    },
                    "kolom": {"type": "array", "items": {"type": "string"},
                              "description": "Kolom yang dikembalikan bila TIDAK ada agregasi (default semua)."},
                    "kelompok": {"type": "array", "items": {"type": "string"},
                                 "description": "Kolom pengelompokan. Kolom waktu bisa dipotong: 'tanggal:tahun', 'waktu:bulan', ':hari', ':jam', ':hari_minggu'. "
                                                "Nama kolom hasilnya = nama bucket (tahun, bulan, ...)."},
                    "agregasi": {
                        "type": "array",
                        "description": "Fungsi per kelompok. Nama kolom hasil = alias, atau '<fungsi>_<kolom>'. count tanpa kolom → 'jumlah'.",
                        "items": {"type": "object",
                                  "properties": {"kolom": {"type": "string"}, "fungsi": {"type": "string", "enum": list(query.FUNGSI)},
                                                 "alias": {"type": "string"}},
                                  "required": ["fungsi"]},
                    },
                    "urut": {"type": "object", "properties": {"kolom": {"type": "string"}, "turun": {"type": "boolean"}},
                             "required": ["kolom"]},
                    "limit": {"type": "integer", "description": f"Maks baris (default {query.LIMIT_DEFAULT}, maks {query.LIMIT_MAKS})."},
                    "grafik": _SKEMA_GRAFIK,
                },
                "required": ["dataset"],
            },
        },
    },
]

PROMPT_SISTEM = """Kamu adalah asisten data untuk portofolio proyek data publik Avalon. Tugasmu menjawab pertanyaan \
HANYA berdasarkan data dari dataset di bawah, lewat alat query_data dan describe_dataset.

Aturan:
1. Setiap angka, nama, dan tanggal dalam jawaban harus berasal dari hasil alat. Jangan menebak atau menambah dari ingatanmu.
2. Jika data tidak mencakup pertanyaan, katakan dengan jujur, lalu sebutkan dataset yang paling dekat dan apa yang BISA dijawab.
3. Jawab dalam bahasa yang dipakai pengguna: pertanyaan berbahasa Inggris dijawab dalam bahasa Inggris, pertanyaan berbahasa Indonesia dalam bahasa Indonesia. Ringkas, langsung ke angka. Format angka besar dengan pemisah ribuan; rupiah boleh diringkas ke triliun/miliar.
4. Sertakan 'grafik' di query_data bila pertanyaan membandingkan beberapa hal, menanyakan tren, peringkat, komposisi, atau lokasi. Satu pertanyaan cukup satu grafik.
5. Pakai describe_dataset bila ragu dengan ejaan nilai kolom teks (misalnya nama provinsi atau kategori) sebelum memfilter.
6. Akhiri jawaban dengan satu baris "Sumber: <nama proyek> - dataset <id>" (satu baris per dataset yang dipakai). Jangan menyebut alat atau JSON.
7. Semua data adalah snapshot; sebutkan rentang waktu bila relevan. Jangan memberi saran investasi.
8. Untuk apbd_provinsi: selalu filter 'akun' tertentu atau satu 'tingkat'; nilai dalam rupiah penuh.
9. Kalau alat mengembalikan GALAT, perbaiki spesifikasinya dan coba lagi (maksimal beberapa kali), jangan langsung menyerah.
10. Kalau deskripsi dataset menyebut keterbatasan yang memengaruhi jawaban (nilai model per sel grid, artefak sensor, bendera bukan kepemilikan, data yang mencakup satelit yang sudah mati, status data 'awal'), sebutkan dalam satu kalimat.

Tanggal hari ini: {tanggal}.

Dataset yang tersedia:
{skema}
"""


def prompt_sistem(tanggal: date | None = None) -> str:
    return PROMPT_SISTEM.format(tanggal=(tanggal or date.today()).isoformat(), skema=katalog.skema_ringkas())


class Alat:
    """Penyedia alat untuk src/llm.jawab. `muat` bisa diganti (misalnya dengan cache Streamlit) saat pengujian."""

    definisi = DEFINISI

    def __init__(self, muat: Callable[[str], pd.DataFrame] = katalog.muat):
        self.muat = muat

    def jalankan(self, nama: str, argumen: dict) -> tuple[str, Any]:
        if nama == "describe_dataset":
            return katalog.deskripsi_dataset(str(argumen.get("dataset", ""))), None
        if nama == "query_data":
            return self.query_data(argumen)
        raise ValueError(f"Alat '{nama}' tidak dikenal. Pilihan: describe_dataset, query_data.")

    def query_data(self, argumen: dict) -> tuple[str, Lampiran]:
        id = str(argumen.get("dataset", ""))
        if id not in katalog.DATASET:
            raise ValueError(f"Dataset '{id}' tidak ada. Pilihan: {', '.join(katalog.DATASET)}.")
        d = katalog.DATASET[id]
        df = self.muat(id)
        spek = {k: v for k, v in argumen.items() if k not in ("dataset", "grafik")}
        hasil = query.jalankan(df, spek)
        spek_grafik = argumen.get("grafik") or None
        if spek_grafik:
            if hasil.empty:
                spek_grafik = None
            else:
                spek_grafik = grafik.periksa(hasil, spek_grafik)  # gagal → GalatGrafik → LLM memperbaiki
        teks = f"Dataset {id} (proyek {katalog.PROYEK[d.proyek].judul}): " + query.ke_teks(hasil, MAKS_BARIS_KE_LLM)
        if hasil.empty:
            teks += "\nTidak ada baris yang cocok. Periksa ejaan nilai filter dengan describe_dataset."
        return teks, Lampiran(id, d.proyek, spek, hasil, spek_grafik)
