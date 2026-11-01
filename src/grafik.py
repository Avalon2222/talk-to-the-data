"""
grafik.py - Membuat grafik Plotly dari hasil query + spesifikasi kecil yang dikirim LLM.

Spesifikasi grafik:

    {"jenis": "bar" | "line" | "scatter" | "pie" | "peta",
     "x": "kolom", "y": "kolom" atau ["kolom1", "kolom2"],
     "warna": "kolom kategori (opsional)", "ukuran": "kolom angka (opsional)",
     "label": "kolom teks untuk hover (opsional)", "judul": "judul grafik",
     "lat": "kolom lintang", "lon": "kolom bujur"}            # hanya untuk jenis "peta"

LLM hanya memilih kolom dan jenis; warna, ukuran marka, dan tata letak ditentukan di sini
supaya semua grafik di aplikasi terlihat satu keluarga (dan aman untuk buta warna).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

JENIS = ("bar", "line", "scatter", "pie", "peta")

# Urutan warna kategori tetap (bukan diputar), sudah divalidasi untuk buta warna.
PALET = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
WARNA_TUNGGAL = PALET[0]
SKALA_SEKUENSIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MAKS_KATEGORI_PIE = 8
MAKS_SERI = 8


class GalatGrafik(ValueError):
    """Spesifikasi grafik tidak cocok dengan hasil query. Pesannya untuk LLM."""


def _kolom_y(spek: dict) -> list[str]:
    y = spek.get("y")
    if y is None:
        return []
    return [y] if isinstance(y, str) else list(y)


def periksa(df: pd.DataFrame, spek: dict) -> dict:
    """Validasi spesifikasi terhadap kolom hasil. Mengembalikan spesifikasi yang sudah dirapikan."""
    if not isinstance(spek, dict):
        raise GalatGrafik("Spesifikasi grafik harus objek JSON.")
    jenis = spek.get("jenis", "bar")
    if jenis not in JENIS:
        raise GalatGrafik(f"Jenis grafik '{jenis}' tidak dikenal. Pilihan: {', '.join(JENIS)}.")
    kolom = list(map(str, df.columns))

    def ada(nama: str | None, peran: str) -> None:
        if nama and nama not in kolom:
            raise GalatGrafik(f"Kolom '{nama}' untuk {peran} grafik tidak ada di hasil query. Kolom hasil: {', '.join(kolom)}.")

    if jenis == "peta":
        lat, lon = spek.get("lat", "lat"), spek.get("lon", "lon")
        ada(lat, "lat"), ada(lon, "lon")
        spek = {**spek, "lat": lat, "lon": lon}
    else:
        if not spek.get("x") or not _kolom_y(spek):
            raise GalatGrafik("Grafik butuh 'x' dan 'y'.")
        ada(spek["x"], "x")
        for y in _kolom_y(spek):
            ada(y, "y")
    for peran in ("warna", "ukuran", "label"):
        ada(spek.get(peran), peran)
    if len(_kolom_y(spek)) > MAKS_SERI:
        raise GalatGrafik(f"Maksimal {MAKS_SERI} kolom y.")
    return {**spek, "jenis": jenis}


def _rapikan(fig: go.Figure, judul: str | None, tinggi: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_white", title=judul or None, height=tinggi, colorway=PALET,
        margin=dict(l=10, r=10, t=50 if judul else 20, b=10), hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#0b0b0b"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, title_font=dict(color="#52514e"))
    fig.update_yaxes(gridcolor="#e6e5e1", zeroline=False, title_font=dict(color="#52514e"))
    return fig


def buat(df: pd.DataFrame, spek: dict) -> go.Figure:
    """Hasil query + spesifikasi → go.Figure. Melempar GalatGrafik bila tidak cocok."""
    spek = periksa(df, spek)
    jenis, judul = spek["jenis"], spek.get("judul")
    warna, label = spek.get("warna"), spek.get("label")
    if df.empty:
        raise GalatGrafik("Hasil query kosong, tidak ada yang bisa digambar.")

    if jenis == "peta":
        hover = {k: True for k in df.columns if k not in (spek["lat"], spek["lon"])}
        fig = px.scatter_map(
            df, lat=spek["lat"], lon=spek["lon"], color=warna, size=spek.get("ukuran"), hover_name=label,
            hover_data=hover, color_discrete_sequence=PALET, size_max=22, zoom=3.3,
            center=dict(lat=float(df[spek["lat"]].mean()), lon=float(df[spek["lon"]].mean())),
            map_style="carto-positron",
        )
        fig.update_traces(marker=dict(opacity=0.85))
        if not warna:
            fig.update_traces(marker=dict(color=WARNA_TUNGGAL, size=10 if not spek.get("ukuran") else None))
        return _rapikan(fig, judul, 520)

    x, ys = spek["x"], _kolom_y(spek)
    data = df.copy()

    if jenis == "pie":
        y = ys[0]
        data = data.sort_values(y, ascending=False)
        if len(data) > MAKS_KATEGORI_PIE:  # kategori ke-9 dst. dilipat menjadi "Lainnya", warnanya tidak pernah diputar
            sisa = data.iloc[MAKS_KATEGORI_PIE - 1:][y].sum()
            data = pd.concat([data.iloc[: MAKS_KATEGORI_PIE - 1], pd.DataFrame({x: ["Lainnya"], y: [sisa]})])
        fig = px.pie(data, names=x, values=y, hole=0.45, color_discrete_sequence=PALET)
        fig.update_traces(textposition="inside", textinfo="percent+label", marker=dict(line=dict(color="#fcfcfb", width=2)))
        return _rapikan(fig, judul)

    if jenis == "line" and pd.api.types.is_numeric_dtype(data[x]) or pd.api.types.is_datetime64_any_dtype(data[x]):
        data = data.sort_values(x)

    if len(ys) > 1:
        # Beberapa kolom y → format panjang supaya tiap kolom jadi satu seri berwarna tetap.
        nama_seri, nama_nilai = "seri", "nilai"
        while nama_seri in data.columns or nama_nilai in data.columns:  # hindari bentrok dengan kolom hasil
            nama_seri, nama_nilai = nama_seri + "_", nama_nilai + "_"
        data = data.melt(id_vars=[x] + [k for k in (warna, label) if k], value_vars=ys,
                         var_name=nama_seri, value_name=nama_nilai)
        y, warna = nama_nilai, nama_seri
    else:
        y = ys[0]

    hover = {k: True for k in (label,) if k}
    if jenis == "bar":
        banyak = data[x].nunique() > 12 and not warna
        fig = px.bar(data, x=y if banyak else x, y=x if banyak else y, color=warna, hover_name=label,
                     color_discrete_sequence=PALET, orientation="h" if banyak else "v", barmode="group")
        fig.update_traces(marker=dict(line=dict(color="#fcfcfb", width=1)))
        if banyak:
            fig.update_yaxes(autorange="reversed")
        if not warna:
            fig.update_traces(marker_color=WARNA_TUNGGAL)
    elif jenis == "line":
        fig = px.line(data, x=x, y=y, color=warna, hover_name=label, color_discrete_sequence=PALET, markers=len(data) <= 60)
        fig.update_traces(line=dict(width=2))
        if not warna:
            fig.update_traces(line_color=WARNA_TUNGGAL)
    else:  # scatter
        fig = px.scatter(data, x=x, y=y, color=warna, size=spek.get("ukuran"), hover_name=label, hover_data=hover,
                         color_discrete_sequence=PALET, size_max=24)
        fig.update_traces(marker=dict(opacity=0.8, line=dict(color="#fcfcfb", width=1)))
        if not warna:
            fig.update_traces(marker_color=WARNA_TUNGGAL)
    return _rapikan(fig, judul)
