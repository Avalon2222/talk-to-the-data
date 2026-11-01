"""
sinkron_data.py - Menyalin ulang snapshot data dari ketujuh repo proyek.

Sumber bawaan: GitHub (raw.githubusercontent.com, branch main). Alternatif: folder lokal yang
berisi clone tiap repo (satu folder per repo, nama sama dengan id proyek).

    python scripts/sinkron_data.py                       # unduh semua dari GitHub
    python scripts/sinkron_data.py --hanya follow-the-money
    python scripts/sinkron_data.py --lokal ..            # salin dari ../<id-proyek>/<path asal>

Daftar file yang disalin diambil dari src/katalog.py, jadi tidak ada daftar ganda.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import katalog  # noqa: E402

RAW = "https://raw.githubusercontent.com/{akun}/{repo}/main/{path}"


def url_sumber(d: katalog.Dataset, akun: str = katalog.AKUN_GITHUB) -> str:
    return RAW.format(akun=akun, repo=d.proyek, path=d.asal)


def unduh(d: katalog.Dataset) -> int:
    import requests

    resp = requests.get(url_sumber(d), timeout=60)
    resp.raise_for_status()
    d.path.parent.mkdir(parents=True, exist_ok=True)
    d.path.write_bytes(resp.content)
    return len(resp.content)


def salin_lokal(d: katalog.Dataset, akar: Path) -> int:
    sumber = akar / d.proyek / d.asal
    if not sumber.exists():
        raise FileNotFoundError(sumber)
    d.path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sumber, d.path)
    return d.path.stat().st_size


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lokal", type=Path, help="folder yang berisi clone tiap repo (bukan GitHub)")
    ap.add_argument("--hanya", action="append", help="id proyek yang disinkronkan (bisa diulang)")
    args = ap.parse_args(argv)

    gagal = 0
    for d in katalog.DATASET.values():
        if args.hanya and d.proyek not in args.hanya:
            continue
        try:
            ukuran = salin_lokal(d, args.lokal) if args.lokal else unduh(d)
            print(f"{d.proyek:24s} {d.file:28s} {ukuran / 1024:8.1f} KB")
        except Exception as e:  # satu file gagal tidak boleh menghentikan sisanya
            gagal += 1
            print(f"{d.proyek:24s} {d.file:28s} GAGAL: {type(e).__name__}: {e}")
    katalog.muat.cache_clear()
    print(f"Selesai, {gagal} gagal.")
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
