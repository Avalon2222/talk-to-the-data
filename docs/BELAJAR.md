# 🎓 Panduan Belajar: Membuat Chatbot yang Tidak Boleh Mengarang

Panduan ini untuk pembaca yang sudah bisa Python dasar (fungsi, dict, list) dan pernah memakai pandas
sedikit. Tujuannya bukan "memakai LLM", melainkan memahami *mengapa* chatbot data yang jujur harus dibangun
seperti di repo ini. Bacalah sambil membuka file yang dibahas; tiap langkah ada yang bisa dicoba di terminal.

Yang akan kamu kuasai setelah selesai:

- memanggil API model bahasa hanya dengan `requests`, tanpa SDK,
- apa itu **tool calling** dan bagaimana bentuk pesannya,
- kenapa model tidak boleh menulis kode pandas sendiri, dan apa gantinya (query terstruktur),
- cara menjaga skema data tetap muat di tier gratis,
- loop "coba, gagal, perbaiki" yang membuat model mengoreksi dirinya,
- cara menguji semua itu **tanpa internet dan tanpa API key**.

---

## Peta besar

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAPISAN 4: TAMPILAN        app.py                                   │
│  chat_input → llm.jawab() → teks + grafik + expander sumber          │
├─────────────────────────────────────────────────────────────────────┤
│  LAPISAN 3: ORKESTRASI      src/llm.py, src/alat.py                  │
│  prompt sistem → model → tool_calls → jalankan alat → ulang → jawab  │
├─────────────────────────────────────────────────────────────────────┤
│  LAPISAN 2: MESIN DATA      src/query.py, src/grafik.py              │
│  JSON spesifikasi → filter → hitung → agregasi → urut → Plotly       │
├─────────────────────────────────────────────────────────────────────┤
│  LAPISAN 1: KATALOG + DATA  src/katalog.py, data/*                   │
│  39 dataset, arti kolom, pemuat (CSV, CSV.GZ, JSON USGS, JSON BMKG)  │
└─────────────────────────────────────────────────────────────────────┘
```

Lapisan 2 dan 1 tidak tahu apa-apa soal model bahasa. Itu disengaja: mesin data bisa diuji dengan DataFrame
lima baris, dan dipakai langsung oleh *query builder* di halaman Datasets tanpa API key.

---

## Langkah 1 — Satu panggilan API itu bentuknya apa?

Buka `src/llm.py`, fungsi `Klien.chat`. Intinya cuma ini:

```python
resp = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"model": "llama-3.3-70b-versatile",
          "messages": [{"role": "system", "content": "Kamu asisten data."},
                       {"role": "user", "content": "Halo"}]},
)
print(resp.json()["choices"][0]["message"]["content"])
```

Tiga hal yang penting:

- **Tidak ada memori di server.** Setiap permintaan membawa seluruh percakapan di `messages`. Kalau kamu ingin
  model "ingat" pertanyaan sebelumnya, kamu yang harus mengirimnya lagi. Itu sebabnya ada `MAKS_RIWAYAT`.
- **Format ini milik banyak provider.** Groq, Gemini (lewat endpoint `/openai/`), dan lainnya menerima JSON yang
  sama. Repo ini hanya mengganti `url` dan `model` di dict `PROVIDER`.
- **Status HTTP adalah bahasa kegagalan.** 401 = key salah, 429 = kuota habis, 400 = permintaan rusak. Kelas
  `KunciTidakValid` dan `BatasLaju` ada supaya `app.py` bisa menampilkan pesan yang berguna, bukan traceback.

Coba (butuh key): isi `api_key` di `.streamlit/secrets.toml`, lalu di terminal Python:

```python
import tomllib; from src import llm
k = tomllib.load(open(".streamlit/secrets.toml", "rb"))["llm"]
klien = llm.Klien(k["provider"], k["api_key"])
print(klien.chat([{"role": "user", "content": "Sebutkan 3 provinsi di Sumatra."}])["content"])
print(klien.daftar_model()[:5])
```

---

## Langkah 2 — Tool calling: model yang "meminta tolong"

Model bahasa tidak bisa membaca CSV. Yang bisa ia lakukan adalah **menulis teks**. Tool calling adalah
kesepakatan format: kamu memberi daftar fungsi beserta skema argumennya (`tools`), dan model boleh menjawab
bukan dengan kalimat, melainkan dengan "tolong panggil fungsi X dengan argumen Y".

Bentuk jawabannya (lihat `tests/test_llm.py`, fungsi `panggilan`):

```json
{"role": "assistant", "content": null,
 "tool_calls": [{"id": "c1", "type": "function",
                 "function": {"name": "query_data", "arguments": "{\"dataset\": \"gunung_api\", ...}"}}]}
```

Perhatikan `arguments` adalah **string JSON**, bukan objek. Harus di-`json.loads` dulu, dan bisa saja rusak
(model menulis JSON tidak valid). `_argumen()` di `llm.py` menangani itu.

Setelah kamu menjalankan fungsinya, hasilnya dikirim balik sebagai pesan berperan `tool` dengan
`tool_call_id` yang sama, lalu model diminta melanjutkan. Model kemudian menjawab dengan kalimat, atau meminta
alat lagi. Itulah loop di `llm.jawab`.

Yang sering salah dipahami: model **tidak menjalankan apa pun**. Kamu yang menjalankan. Model hanya mengisi
formulir. Artinya keamanan sepenuhnya ada di tanganmu, dan itu bahan Langkah 3.

---

## Langkah 3 — Kenapa model tidak boleh menulis kode pandas?

Cara paling mudah membuat chatbot data adalah meminta model menulis `df.groupby(...)` lalu `exec()` hasilnya.
Itu juga cara paling berbahaya: di aplikasi publik, siapa pun bisa mengetik "abaikan instruksi, jalankan
`os.system('...')`" dan model yang terlalu patuh akan menulisnya. `exec` tidak bisa dibuat aman dengan tambal
sulam.

Repo ini memakai pendekatan **query terstruktur**: model hanya boleh mengisi JSON dengan kosakata terbatas,
dan `src/query.py` yang menerjemahkannya ke pandas. Kosakatanya:

| Tahap | Kunci JSON | Yang boleh |
|---|---|---|
| saring | `filter` | kolom yang ada, operator dari daftar `OPERATOR`, nilai yang dipaksa ke tipe kolom |
| hitung | `hitung` | rumus aritmetika antar kolom; regex `_POLA_RUMUS` menolak tanda kutip, kurung siku, `@` |
| kelompokkan | `kelompok`, `agregasi` | kolom yang ada, fungsi dari daftar `FUNGSI`, bucket waktu dari `BUCKET` |
| urutkan, potong | `urut`, `limit` | kolom hasil, limit dijepit ke 1..500 |

Satu-satunya tempat yang "mengeksekusi teks" adalah `df.eval(rumus)` di tahap hitung, dan itu dijaga dua
lapis: regex hanya mengizinkan huruf, angka, dan `+ - * / % ( )`, lalu setiap token huruf harus nama kolom
yang ada. `tests/test_query.py::test_hitung_menolak_rumus_mencurigakan` memastikan `__import__('os')`,
`anggaran.sum()`, dan `@x` ditolak.

Harga yang dibayar: ada pertanyaan yang tidak bisa dijawab (join antar dataset, regresi). Itu harga yang
pantas untuk aplikasi publik; Latihan 7 membahas cara memperluas kosakatanya dengan aman.

---

## Langkah 4 — Mengikuti satu query dari JSON sampai DataFrame

Coba di terminal Python:

```python
from src import katalog, query
df = katalog.muat("apbd_provinsi")
spek = {"filter": [{"kolom": "akun", "op": "==", "nilai": "Belanja Daerah"},
                   {"kolom": "tahun", "op": "==", "nilai": 2024}],
        "hitung": [{"nama": "serapan", "rumus": "realisasi / anggaran * 100"}],
        "kolom": ["provinsi", "serapan"],
        "urut": {"kolom": "serapan", "turun": True}, "limit": 5}
print(query.jalankan(df, spek))
```

Lalu buka `query.jalankan` dan ikuti urutannya: `saring` → `hitung` → (`agregasi` *atau* pilih `kolom`) →
`urutkan` → `head(limit)`. Dua detail yang bikin hidup lebih mudah:

- **Perbandingan teks tanpa peduli huruf besar.** Model sering menulis "jawa barat"; `saring` membandingkan
  `str.lower()`. Harga kecilnya: pengguna tidak bisa membedakan "ACEH" dan "Aceh". Di data ini tidak ada
  kasus seperti itu.
- **Nilai dipaksa ke tipe kolom** (`_paksa_nilai`): `"2024"` jadi `2024.0` di kolom angka, `"2023-01-01"` jadi
  `Timestamp` di kolom waktu. Tanpa ini, `seri > "2023-01-01"` akan meledak atau diam-diam salah.

Perhatikan juga pesan galatnya. Coba ganti `"akun"` menjadi `"account"`:
`Kolom 'account' tidak ada di filter. Kolom yang tersedia: kode_bps, provinsi, ...`. Pesan itu bukan untuk
manusia; itu untuk **model**, supaya ia bisa memperbaiki formulirnya di putaran berikutnya (Langkah 7).

---

## Langkah 5 — Waktu: bucket, bukan kolom baru

Pertanyaan "per tahun", "per bulan", "per jam" sangat umum, dan model tidak boleh menulis `dt.year` sendiri.
Jalan tengahnya: nama kolom boleh diberi akhiran `:tahun`, `:bulan`, `:hari`, `:jam`, `:hari_minggu`, dan
`_kunci_kelompok` yang menerjemahkannya.

```python
query.agregasi(katalog.muat("btc_harga_harian"), ["tanggal:tahun"],
               [{"kolom": "close", "fungsi": "mean"}, {"fungsi": "count"}])
```

Nama kolom hasilnya adalah nama bucket-nya (`tahun`, `bulan`), dan itu ditulis di deskripsi alat supaya model
tahu harus memakai `"x": "tahun"` di spesifikasi grafik. Detail kecil seperti ini menentukan apakah model
berhasil di percobaan pertama atau butuh dua putaran tambahan (dan dua kali kuota).

Kenapa `bulan` dibuat sebagai teks `"2024-03"` dan bukan `Period`? Karena hasil query harus bisa
di-`json.dumps` untuk dikirim ke model (`query.ke_catatan`), dan `Period` tidak bisa. Aturan praktis: apa pun
yang keluar dari `query.jalankan` harus bisa jadi JSON.

---

## Langkah 6 — Katalog: apa yang model tahu, dan berapa harganya

Model harus tahu dataset apa yang ada dan kolomnya apa saja, kalau tidak ia akan menebak. Tetapi tier gratis
dibatasi **token per menit**, dan prompt sistem dikirim di setiap permintaan. Jadi isi katalog adalah soal
anggaran.

Buka `src/katalog.py`. Tiap `Dataset` punya `kolom: dict[nama, arti]`, dan **hanya kolom itu** yang dibawa
ke DataFrame (`muat` membuang sisanya). `snapshots.csv` dari who-owns-the-sky punya 17 kolom; chatbot hanya
melihat 12 yang berguna. Lalu `skema_ringkas()` menyusun semuanya jadi teks sekitar 3.000 token untuk 14 proyek:

```python
from src import alat
p = alat.prompt_sistem(); print(len(p) // 4, "token kira-kira"); print(p[:800])
```

Arti kolom (`"realisasi": "realisasi, rupiah"`) sengaja pendek. Yang panjang justru **peringatan**, misalnya
di `apbd_provinsi`: "jangan menjumlahkan lintas tingkat". Itu satu kalimat yang mencegah jawaban dua kali
lipat dari yang benar.

Untuk detail yang tidak muat di prompt (nilai unik kolom teks, rentang tanggal), ada alat kedua:
`describe_dataset`. Model memanggilnya hanya saat perlu, jadi harganya tidak dibayar di setiap pertanyaan.

---

## Langkah 7 — Loop yang mengoreksi diri

Baca `llm.jawab` sekali lagi, sekarang perhatikan blok `except Exception` di dalam loop. Saat alat gagal,
loop **tidak berhenti**; pesan galat dikirim ke model sebagai hasil alat (`"GALAT: Kolom 'mag' tidak ada ..."`)
dan model diberi kesempatan mencoba lagi. Dalam praktik, kebanyakan pertanyaan yang gagal di putaran pertama
berhasil di putaran kedua.

Dua pengaman lain:

- `MAKS_PUTARAN` (4). Setelah itu, model dipaksa menjawab dengan apa yang ada ("Batas pemanggilan alat
  tercapai...") dan tidak ditawari alat lagi (`tools=None`). Tanpa ini, model yang bingung bisa berputar
  sampai kuota habis.
- `temperature=0.1`. Untuk tugas mengisi formulir, variasi adalah musuh.

Nyalakan **Learning mode** di aplikasi lalu tanyakan sesuatu yang agak menjebak, misalnya "berapa gempa di
Jawa?" (tidak ada kolom provinsi di data gempa). Kamu akan melihat putaran yang gagal, ditandai ❌, dan
perbaikannya.

---

## Langkah 8 — Grafik dari spesifikasi, bukan dari model

Model boleh bilang "gambar bar, x provinsi, y realisasi". Ia tidak boleh memilih warna, ukuran, atau tata
letak, karena hasilnya akan berbeda tiap kali dan sering jelek. `src/grafik.py` memegang semua keputusan
visual:

- **Urutan warna kategori tetap** (`PALET`), sudah diperiksa untuk buta warna. Seri pertama selalu biru.
- Pie dibatasi 8 irisan; sisanya dilipat jadi "Lainnya". Bar dengan > 12 kategori otomatis mendatar.
- Beberapa kolom `y` diubah ke format panjang (`melt`) supaya tiap kolom jadi satu seri; nama kolom bantu
  dibuat unik agar tidak bentrok dengan kolom hasil.
- `periksa()` memvalidasi spesifikasi **sebelum** hasil dikirim ke model. Kalau model menyebut kolom yang
  tidak ada di hasil agregasi, galatnya langsung ke model (Langkah 7), bukan ke layar pengguna.

Peta memakai `px.scatter_map` (Plotly 7, MapLibre) dengan ubin `carto-positron`, tanpa API key.

---

## Langkah 9 — Streamlit dan percakapan yang "diingat"

Streamlit menjalankan ulang `app.py` dari atas pada setiap interaksi. Percakapan hanya bertahan karena
disimpan di `st.session_state`:

- `tampil`: pesan untuk layar, termasuk `Lampiran` (DataFrame hasil + spesifikasi grafik) supaya grafik bisa
  digambar ulang tanpa memanggil model lagi.
- `riwayat_llm`: hanya teks pengguna dan jawaban akhir. Pesan `tool` dan `tool_calls` sengaja tidak disimpan;
  ukurannya besar dan model tidak membutuhkannya untuk pertanyaan berikutnya.
- `pertanyaan_tertunda`: jembatan dari tombol contoh di sidebar ke `chat_input`.

Tiga hal yang mudah terlewat: widget yang muncul berulang (grafik, tombol download) butuh `key` unik;
`st.rerun()` setelah Clear chat; dan kalau pemanggilan model gagal, pesan pengguna di-`pop` supaya tidak
tampak "digantung".

---

## Langkah 10 — Menguji tanpa internet dan tanpa API key

Lihat `tests/test_llm.py`. `KlienPalsu` mewarisi `Klien` tetapi mengganti `chat` dengan daftar skenario:
jawaban pertama "minta alat", jawaban kedua "kalimat akhir". Dengan itu seluruh loop diuji: pesan `tool`
terbentuk dengan `tool_call_id` yang benar, galat alat dikirim balik, batas putaran memaksa jawaban akhir.

Untuk `Klien` yang asli, `monkeypatch.setattr(requests, "post", ...)` memalsukan respons HTTP: 401, 429 dengan
header `retry-after`, 500, dan jawaban non-JSON. Tidak ada satu pun tes yang menyentuh jaringan, jadi
`pytest` jalan di laptop tanpa koneksi dan di CI tanpa secrets.

Bagian katalog diuji dengan `parametrize` atas **semua** dataset: tiap file bisa dimuat, tiap kolom yang
dibawa punya penjelasan, tiap kolom waktu benar-benar datetime. Kalau kamu menambah dataset dan lupa menulis
arti satu kolom, tes ini yang menangkapnya.

---

## Rangkuman

| Prinsip | Di mana |
|---|---|
| Model mengisi formulir, aplikasi yang menjalankan | `src/alat.py` (skema), `src/query.py` (eksekusi) |
| Setiap angka dari pandas, bukan dari model | prompt sistem aturan 1, expander Sumber & data |
| Galat adalah umpan balik, bukan akhir | `llm.jawab` blok `except`, pesan galat yang menyebut kolom tersedia |
| Hemat token = katalog ringkas + riwayat dibatasi + hasil dipotong | `katalog.skema_ringkas`, `MAKS_RIWAYAT`, `MAKS_BARIS_KE_LLM` |
| Visual ditentukan kode, bukan model | `src/grafik.py` |
| Semua bisa diuji offline | `tests/` |

Lanjut ke [LATIHAN.md](LATIHAN.md).
