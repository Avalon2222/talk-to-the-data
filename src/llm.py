"""
llm.py - Klien ringan ke API chat yang kompatibel OpenAI (Groq, Gemini) dan loop tool calling.

Tanpa SDK, hanya `requests`. Semua yang menyentuh jaringan ada di kelas Klien, sehingga loop
tool calling (fungsi `jawab`) bisa diuji dengan klien palsu tanpa internet dan tanpa API key
(lihat tests/test_llm.py).

Alur satu pertanyaan:

    pengguna ─► jawab() ─► LLM: "aku butuh data" ─► tool_calls ─► alat.jalankan() ─► hasil (teks)
                              ▲                                                        │
                              └────────────── dikirim balik sebagai pesan "tool" ◄──────┘
                              ─► LLM: jawaban akhir (teks) ─► Jawaban(teks, langkah)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests

PROVIDER = {
    "groq": {
        "nama": "Groq",
        "url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "url_kunci": "https://console.groq.com/keys",
    },
    "gemini": {
        "nama": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "url_kunci": "https://aistudio.google.com/apikey",
    },
}
MAKS_RIWAYAT = 8        # pesan lama yang ikut dikirim (hemat token: tier gratis dibatasi per menit)
MAKS_PUTARAN = 4        # berapa kali LLM boleh memanggil alat untuk satu pertanyaan
MAKS_TOKEN_JAWABAN = 1024


class GalatLLM(Exception):
    """Permintaan ke API gagal. `kode` = status HTTP (0 kalau jaringan putus)."""

    def __init__(self, pesan: str, kode: int = 0):
        super().__init__(pesan)
        self.kode = kode


class KunciTidakValid(GalatLLM):
    pass


class BatasLaju(GalatLLM):
    """HTTP 429: kuota per menit/hari habis. `detik` = saran tunggu dari server, bila ada."""

    def __init__(self, pesan: str, detik: float | None = None):
        super().__init__(pesan, 429)
        self.detik = detik


def _detik_tunggu(resp: requests.Response) -> float | None:
    header = resp.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    cocok = re.search(r"try again in ([\d.]+)\s*(ms|s|m)", resp.text)
    if cocok:
        angka, satuan = float(cocok.group(1)), cocok.group(2)
        return angka / 1000 if satuan == "ms" else angka * 60 if satuan == "m" else angka
    return None


class Klien:
    """Pembungkus endpoint /chat/completions dan /models."""

    def __init__(self, provider: str = "groq", api_key: str = "", model: str | None = None, timeout: int = 90):
        if provider not in PROVIDER:
            raise ValueError(f"Provider '{provider}' tidak dikenal. Pilihan: {', '.join(PROVIDER)}.")
        self.provider = provider
        self.url = PROVIDER[provider]["url"]
        self.api_key = api_key
        self.model = model or PROVIDER[provider]["model"]
        self.timeout = timeout

    @property
    def nama_provider(self) -> str:
        return PROVIDER[self.provider]["nama"]

    def _header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(self, messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.1) -> dict:
        """Kirim satu permintaan chat. Mengembalikan objek `message` dari pilihan pertama."""
        if not self.api_key:
            raise KunciTidakValid("API key kosong.", 401)
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": MAKS_TOKEN_JAWABAN,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        try:
            resp = requests.post(f"{self.url}/chat/completions", headers=self._header(), json=body, timeout=self.timeout)
        except requests.RequestException as e:
            raise GalatLLM(f"Tidak bisa menghubungi {self.nama_provider}: {type(e).__name__}.") from e

        if resp.status_code in (401, 403):
            raise KunciTidakValid(f"API key ditolak oleh {self.nama_provider} (HTTP {resp.status_code}).", resp.status_code)
        if resp.status_code == 429:
            detik = _detik_tunggu(resp)
            raise BatasLaju(
                f"Kuota {self.nama_provider} sedang penuh (HTTP 429)."
                + (f" Coba lagi dalam ±{detik:.0f} detik." if detik else " Coba lagi sebentar."),
                detik,
            )
        if resp.status_code >= 400:
            raise GalatLLM(f"{self.nama_provider} menjawab HTTP {resp.status_code}: {resp.text[:300]}", resp.status_code)
        try:
            return resp.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError) as e:
            raise GalatLLM(f"Jawaban {self.nama_provider} tidak bisa dibaca: {resp.text[:200]}") from e

    def daftar_model(self) -> list[str]:
        resp = requests.get(f"{self.url}/models", headers=self._header(), timeout=self.timeout)
        if resp.status_code in (401, 403):
            raise KunciTidakValid(f"API key ditolak oleh {self.nama_provider}.", resp.status_code)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return sorted(m.get("id", "") for m in data if m.get("id"))


# ---------------------------------------------------------------------------
# Loop tool calling
# ---------------------------------------------------------------------------

class PenyediaAlat(Protocol):
    """Apa pun yang punya daftar definisi alat dan bisa menjalankannya (lihat src/alat.py)."""

    definisi: list[dict]

    def jalankan(self, nama: str, argumen: dict) -> tuple[str, Any]: ...


@dataclass
class Langkah:
    alat: str
    argumen: dict
    teks_hasil: str
    lampiran: Any = None       # objek apa pun dari alat (misalnya hasil query + spesifikasi grafik)
    galat: str | None = None


@dataclass
class Jawaban:
    teks: str
    langkah: list[Langkah] = field(default_factory=list)
    putaran: int = 0


def _argumen(panggilan: dict) -> dict:
    mentah = panggilan.get("function", {}).get("arguments") or "{}"
    if isinstance(mentah, dict):
        return mentah
    try:
        hasil = json.loads(mentah)
    except json.JSONDecodeError as e:
        raise ValueError(f"Argumen alat bukan JSON valid: {e}") from e
    return hasil if isinstance(hasil, dict) else {}


def jawab(
    klien: Klien,
    sistem: str,
    riwayat: list[dict],
    pertanyaan: str,
    alat: PenyediaAlat,
    maks_putaran: int = MAKS_PUTARAN,
) -> Jawaban:
    """Jalankan loop: tanya LLM, jalankan alat yang diminta, ulangi sampai LLM menjawab dengan teks."""
    messages: list[dict] = [{"role": "system", "content": sistem}]
    messages += riwayat[-MAKS_RIWAYAT:]
    messages.append({"role": "user", "content": pertanyaan})
    langkah: list[Langkah] = []

    for putaran in range(1, maks_putaran + 1):
        try:
            pesan = klien.chat(messages, tools=alat.definisi)
        except GalatLLM as e:
            # Groq kadang menjawab 400 "tool_use_failed" kalau model salah menyusun JSON; coba sekali lagi.
            if e.kode == 400 and "tool" in str(e).lower():
                pesan = klien.chat(messages, tools=alat.definisi)
            else:
                raise
        panggilan = pesan.get("tool_calls") or []
        if not panggilan:
            return Jawaban(pesan.get("content") or "", langkah, putaran)

        messages.append({"role": "assistant", "content": pesan.get("content") or None, "tool_calls": panggilan})
        for p in panggilan:
            nama = p.get("function", {}).get("name", "")
            try:
                argumen = _argumen(p)
                teks, lampiran = alat.jalankan(nama, argumen)
                langkah.append(Langkah(nama, argumen, teks, lampiran))
            except Exception as e:  # alat gagal → beri tahu LLM supaya bisa memperbaiki, jangan hentikan loop
                teks = f"GALAT: {e}"
                langkah.append(Langkah(nama, locals().get("argumen", {}), teks, None, str(e)))
            messages.append({"role": "tool", "tool_call_id": p.get("id", nama), "name": nama, "content": teks})

    # Putaran habis: minta jawaban akhir tanpa menawarkan alat lagi.
    messages.append({
        "role": "user",
        "content": "Batas pemanggilan alat tercapai. Jawab sekarang dengan data yang sudah ada, "
                   "dan sebutkan bila ada bagian yang belum sempat dicek.",
    })
    pesan = klien.chat(messages, tools=None)
    return Jawaban(pesan.get("content") or "", langkah, maks_putaran)
