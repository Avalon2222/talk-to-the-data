"""
Tes untuk src/llm.py: loop tool calling dengan klien palsu (tanpa internet, tanpa API key),
dan penanganan status HTTP dengan requests yang dipalsukan.
"""

import json

import pytest
import requests

from src import llm


class AlatPalsu:
    definisi = [{"type": "function", "function": {"name": "hitung", "parameters": {"type": "object"}}}]

    def __init__(self):
        self.dipanggil = []

    def jalankan(self, nama, argumen):
        self.dipanggil.append((nama, argumen))
        if argumen.get("meledak"):
            raise ValueError("kolom tidak ada")
        return f"hasil untuk {argumen.get('x')}", {"lampiran": argumen.get("x")}


class KlienPalsu(llm.Klien):
    """Mengembalikan skenario jawaban yang sudah ditentukan, satu per panggilan."""

    def __init__(self, skenario):
        super().__init__("groq", api_key="kunci-palsu")
        self.skenario = list(skenario)
        self.permintaan = []

    def chat(self, messages, tools=None, temperature=0.1):
        self.permintaan.append({"messages": list(messages), "tools": tools})
        return self.skenario.pop(0)


def panggilan(id, argumen):
    return {"id": id, "type": "function", "function": {"name": "hitung", "arguments": json.dumps(argumen)}}


def test_jawab_langsung_tanpa_alat():
    klien = KlienPalsu([{"role": "assistant", "content": "Halo."}])
    jawaban = llm.jawab(klien, "sistem", [], "hai", AlatPalsu())
    assert jawaban.teks == "Halo."
    assert jawaban.langkah == []
    pesan = klien.permintaan[0]["messages"]
    assert pesan[0] == {"role": "system", "content": "sistem"}
    assert pesan[-1] == {"role": "user", "content": "hai"}


def test_jawab_dengan_satu_panggilan_alat():
    alat = AlatPalsu()
    klien = KlienPalsu([
        {"role": "assistant", "content": None, "tool_calls": [panggilan("c1", {"x": 7})]},
        {"role": "assistant", "content": "Jawabannya 7."},
    ])
    jawaban = llm.jawab(klien, "sistem", [], "berapa?", alat)
    assert jawaban.teks == "Jawabannya 7."
    assert alat.dipanggil == [("hitung", {"x": 7})]
    assert len(jawaban.langkah) == 1 and jawaban.langkah[0].lampiran == {"lampiran": 7}
    # Permintaan kedua harus membawa pesan assistant (tool_calls) + pesan tool dengan id yang sama.
    pesan = klien.permintaan[1]["messages"]
    assert pesan[-2]["role"] == "assistant" and pesan[-2]["tool_calls"][0]["id"] == "c1"
    assert pesan[-1] == {"role": "tool", "tool_call_id": "c1", "name": "hitung", "content": "hasil untuk 7"}


def test_galat_alat_dikirim_balik_bukan_menghentikan():
    alat = AlatPalsu()
    klien = KlienPalsu([
        {"role": "assistant", "tool_calls": [panggilan("c1", {"meledak": True})]},
        {"role": "assistant", "tool_calls": [panggilan("c2", {"x": 1})]},
        {"role": "assistant", "content": "Setelah diperbaiki: 1."},
    ])
    jawaban = llm.jawab(klien, "s", [], "q", alat)
    assert jawaban.teks == "Setelah diperbaiki: 1."
    assert jawaban.langkah[0].galat == "kolom tidak ada"
    assert klien.permintaan[1]["messages"][-1]["content"].startswith("GALAT: kolom tidak ada")
    assert jawaban.langkah[1].galat is None


def test_argumen_rusak_jadi_galat():
    klien = KlienPalsu([
        {"role": "assistant", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "hitung", "arguments": "{bukan json"}}]},
        {"role": "assistant", "content": "ok"},
    ])
    jawaban = llm.jawab(klien, "s", [], "q", AlatPalsu())
    assert "bukan JSON" in jawaban.langkah[0].galat


def test_batas_putaran_memaksa_jawaban_akhir():
    skenario = [{"role": "assistant", "tool_calls": [panggilan(f"c{i}", {"x": i})]} for i in range(2)]
    skenario.append({"role": "assistant", "content": "Cukup."})
    klien = KlienPalsu(skenario)
    jawaban = llm.jawab(klien, "s", [], "q", AlatPalsu(), maks_putaran=2)
    assert jawaban.teks == "Cukup." and jawaban.putaran == 2
    terakhir = klien.permintaan[-1]
    assert terakhir["tools"] is None
    assert "Batas pemanggilan alat" in terakhir["messages"][-1]["content"]


def test_riwayat_dibatasi():
    riwayat = [{"role": "user", "content": str(i)} for i in range(30)]
    klien = KlienPalsu([{"role": "assistant", "content": "ok"}])
    llm.jawab(klien, "s", riwayat, "q", AlatPalsu())
    pesan = klien.permintaan[0]["messages"]
    assert len(pesan) == 1 + llm.MAKS_RIWAYAT + 1
    assert pesan[1]["content"] == str(30 - llm.MAKS_RIWAYAT)


# --- Klien asli dengan requests palsu ---------------------------------------

class ResponsPalsu:
    def __init__(self, status, body="", headers=None, json_body=None):
        self.status_code, self.text, self.headers, self._json = status, body, headers or {}, json_body

    def json(self):
        if self._json is None:
            raise ValueError("bukan json")
        return self._json


def test_klien_tanpa_kunci():
    with pytest.raises(llm.KunciTidakValid):
        llm.Klien("groq", api_key="").chat([{"role": "user", "content": "hai"}])
    with pytest.raises(ValueError, match="Provider"):
        llm.Klien("openai", api_key="x")


def test_klien_status_http(monkeypatch):
    skenario = {}

    def post_palsu(url, headers, json, timeout):
        skenario["url"], skenario["body"] = url, json
        return skenario["respons"]

    monkeypatch.setattr(requests, "post", post_palsu)
    klien = llm.Klien("groq", api_key="k", model="m")

    skenario["respons"] = ResponsPalsu(200, json_body={"choices": [{"message": {"role": "assistant", "content": "ya"}}]})
    assert klien.chat([{"role": "user", "content": "?"}], tools=[{"x": 1}])["content"] == "ya"
    assert skenario["url"].endswith("/chat/completions") and skenario["body"]["tool_choice"] == "auto"
    assert skenario["body"]["model"] == "m"

    skenario["respons"] = ResponsPalsu(401, "no")
    with pytest.raises(llm.KunciTidakValid):
        klien.chat([])

    skenario["respons"] = ResponsPalsu(429, "Rate limit reached. Please try again in 7.5s.", {"retry-after": "12"})
    with pytest.raises(llm.BatasLaju) as e:
        klien.chat([])
    assert e.value.detik == 12.0

    skenario["respons"] = ResponsPalsu(429, "Please try again in 850ms.")
    with pytest.raises(llm.BatasLaju) as e:
        klien.chat([])
    assert e.value.detik == pytest.approx(0.85)

    skenario["respons"] = ResponsPalsu(500, "server error")
    with pytest.raises(llm.GalatLLM) as e:
        klien.chat([])
    assert e.value.kode == 500

    skenario["respons"] = ResponsPalsu(200, "html", json_body=None)
    with pytest.raises(llm.GalatLLM, match="tidak bisa dibaca"):
        klien.chat([])


def test_klien_jaringan_putus(monkeypatch):
    def post_gagal(*a, **k):
        raise requests.ConnectionError("putus")

    monkeypatch.setattr(requests, "post", post_gagal)
    with pytest.raises(llm.GalatLLM, match="ConnectionError"):
        llm.Klien("gemini", api_key="k").chat([])


def test_klien_beralih_ke_model_cadangan(monkeypatch):
    dipanggil = []

    def post_palsu(url, headers, json, timeout):
        dipanggil.append(json["model"])
        if json["model"] == "utama":
            return ResponsPalsu(503, "high demand")
        if json["model"] == "cadangan-1":
            return ResponsPalsu(404, "not found")
        return ResponsPalsu(200, json_body={"choices": [{"message": {"content": "dari cadangan"}}]})

    monkeypatch.setattr(requests, "post", post_palsu)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    klien = llm.Klien("gemini", api_key="k", model="utama")
    klien.cadangan = ["cadangan-1", "cadangan-2"]
    assert klien.chat([])["content"] == "dari cadangan"
    assert dipanggil == ["utama"] * (len(llm.TUNGGU_503_DETIK) + 1) + ["cadangan-1", "cadangan-2"]
    assert klien.model_terpakai == "cadangan-2"

    klien.cadangan = []
    with pytest.raises(llm.GalatLLM) as e:
        klien.chat([])
    assert e.value.kode == 503


def test_klien_429_pindah_ke_model_lain(monkeypatch):
    def post_palsu(url, headers, json, timeout):
        if json["model"] == "utama":
            return ResponsPalsu(429, "quota exceeded", {"retry-after": "30"})
        return ResponsPalsu(200, json_body={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(requests, "post", post_palsu)
    klien = llm.Klien("gemini", api_key="k", model="utama")
    klien.cadangan = ["lain"]
    assert klien.chat([])["content"] == "ok" and klien.model_terpakai == "lain"
