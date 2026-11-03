"""
wilayah.py - Menentukan provinsi untuk banyak titik lat/lon sekaligus (dari burning-archipelago).

Dipakai untuk memberi kolom `provinsi` pada titik api FIRMS, supaya chatbot bisa menjawab
"provinsi mana yang paling banyak titik apinya". Uji titik di dalam poligon memakai ray casting
dengan numpy, tanpa pustaka geospasial. Titik di laut atau di negara tetangga mendapat None.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _daftar_poligon(geometri: dict) -> list:
    if geometri["type"] == "Polygon":
        return [geometri["coordinates"]]
    if geometri["type"] == "MultiPolygon":
        return geometri["coordinates"]
    raise ValueError(f"Tipe geometri tidak didukung: {geometri['type']}")


def titik_dalam_cincin(lon: np.ndarray, lat: np.ndarray, cincin: np.ndarray) -> np.ndarray:
    """Ray casting: sinar mendatar ke kanan dari tiap titik; jumlah potongan ganjil berarti di dalam."""
    x, y = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    x1, y1 = cincin[:, 0], cincin[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    di_dalam = np.zeros(x.shape, dtype=bool)
    for ax, ay, bx, by in zip(x1, y1, x2, y2):
        if ay == by:
            continue
        melintang = (ay > y) != (by > y)
        if not melintang.any():
            continue
        x_potong = ax + (y - ay) * (bx - ax) / (by - ay)
        di_dalam ^= melintang & (x < x_potong)
    return di_dalam


class PenentuProvinsi:
    """Tiap poligon hanya diuji pada titik di dalam kotak pembatasnya; lubang poligon dikurangkan."""

    def __init__(self, path_geojson: Path | str):
        geojson = json.loads(Path(path_geojson).read_text(encoding="utf-8"))
        self.poligon: list[tuple[str, np.ndarray, list[np.ndarray], tuple]] = []
        for fitur in geojson["features"]:
            nama = fitur["properties"]["provinsi"]
            for poli in _daftar_poligon(fitur["geometry"]):
                luar = np.asarray(poli[0], dtype=float)
                lubang = [np.asarray(c, dtype=float) for c in poli[1:]]
                kotak = (luar[:, 0].min(), luar[:, 1].min(), luar[:, 0].max(), luar[:, 1].max())
                self.poligon.append((nama, luar, lubang, kotak))

    def tentukan(self, lon, lat) -> np.ndarray:
        lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
        hasil = np.full(lon.shape, None, dtype=object)
        belum = np.ones(lon.shape, dtype=bool)
        for nama, luar, lubang, (xmin, ymin, xmax, ymax) in self.poligon:
            kandidat = belum & (lon >= xmin) & (lon <= xmax) & (lat >= ymin) & (lat <= ymax)
            if not kandidat.any():
                continue
            idx = np.flatnonzero(kandidat)
            dalam = titik_dalam_cincin(lon[idx], lat[idx], luar)
            for c in lubang:
                dalam &= ~titik_dalam_cincin(lon[idx], lat[idx], c)
            cocok = idx[dalam]
            hasil[cocok] = nama
            belum[cocok] = False
        return hasil
