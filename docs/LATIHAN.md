# 🏋️ Latihan

Urut dari yang paling mudah. Bintang = tingkat kesulitan. Tiap latihan punya petunjuk dan cara mengecek
jawabanmu. Kerjakan di branch baru (`git checkout -b latihan-1`) supaya mudah kembali kalau ada yang rusak.
Jalankan `python -m pytest tests/ -v` setelah tiap latihan. Latihan 1-5 tidak butuh API key.

---

### Latihan 1 — Query builder dulu, chatbot nanti ⭐

Buka halaman **Datasets**, pilih `apbd_provinsi`, group by `provinsi`, aggregate `sum` kolom `realisasi`,
filter `akun == Belanja Modal`, tahun bebas. Nyalakan Learning mode dan lihat JSON spesifikasinya.

Sekarang buka Chat dan ajukan pertanyaan yang sama dalam kalimat. Bandingkan JSON yang dibuat model (di
expander Learning mode) dengan JSON buatanmu. Apa yang berbeda?

**Cek:** kamu bisa menjelaskan kenapa angka dari query builder dan dari chatbot sama persis padahal jalannya
berbeda (petunjuk: keduanya memanggil `query.jalankan`).

---

### Latihan 2 — Tambah pertanyaan contoh ⭐

`CONTOH_PERTANYAAN` di `app.py` berisi delapan pertanyaan. Tambahkan satu yang menurutmu paling menarik
dari data pertahanan (`markas_tni`, `pangkalan_asing`). Coba di chatbot; kalau model salah memilih dataset,
perbaiki kalimat pertanyaannya, bukan kodenya.

**Cek:** pertanyaan barumu dijawab benar dengan satu putaran alat (lihat Learning mode).

---

### Latihan 3 — Perbaiki satu arti kolom ⭐

Di `src/katalog.py`, cari kolom yang penjelasannya menurutmu kurang jelas (misalnya `keyakinan` di
`data_center`). Tulis ulang dalam satu kalimat pendek. Lalu jalankan:

```python
from src import alat; print(len(alat.prompt_sistem()))
```

**Cek:** `tests/test_katalog_alat.py::test_id_dataset_unik_dan_prompt_ringkas` masih lolos (ada batas
panjang prompt). Kalau gagal, kamu baru saja merasakan anggaran token.

---

### Latihan 4 — Operator baru: `startswith` ⭐⭐

Tambahkan operator `startswith` ke `OPERATOR` dan `saring` di `src/query.py` (tanpa peduli huruf besar).
Tambahkan juga ke deskripsi `op` di `_SKEMA_FILTER` (`src/alat.py`), karena model hanya tahu operator yang
tertulis di sana.

**Cek:** tulis satu tes di `tests/test_query.py`: filter `provinsi startswith "ja"` pada fixture `df`
menghasilkan 1 baris. Lalu tanyakan ke chatbot "callsign yang diawali GIA ada berapa pesawat unik?" dan lihat
apakah model memakai operator barumu.

---

### Latihan 5 — Bucket `kuartal` ⭐⭐

Tambahkan bucket waktu `kuartal` di `BUCKET` dan `_kunci_kelompok` (`src/query.py`). Hasilnya harus teks
seperti `"2024-Q1"` supaya bisa di-JSON-kan (lihat BELAJAR.md Langkah 5). Perbarui deskripsi `kelompok` di
`src/alat.py`.

**Cek:** tes baru: `query.agregasi(df, ["waktu:kuartal"], [])` pada fixture menghasilkan kuartal
`["2022-Q1", "2022-Q2", "2023-Q1", "2023-Q4"]`.

---

### Latihan 6 — Dataset baru dari proyek baru ⭐⭐

Pilih satu CSV dari proyek lain di akun yang sama yang belum ada di katalog (atau buat CSV kecil sendiri).
Tambahkan folder `data/<id-proyek>/`, satu `Proyek` baru di `src/katalog.py` dengan `Dataset`-nya, dan
pastikan `asal` benar supaya `scripts/sinkron_data.py` bisa memperbaruinya.

**Cek:** `pytest tests/test_katalog_alat.py -k semua_dataset` lolos untuk dataset barumu (semua kolom
punya arti, kolom waktu terbaca). Chatbot bisa menjawab satu pertanyaan tentang data itu.

---

### Latihan 7 — Alat ketiga: `join_datasets` ⭐⭐⭐

Pertanyaan "belanja per kapita tiap provinsi" butuh `apbd_provinsi` digabung dengan `penduduk_provinsi`.
Saat ini model harus memanggil dua query dan menghitung sendiri (dan ia buruk dalam aritmetika).

Buat alat `join_datasets` di `src/alat.py`: argumen `kiri`, `kanan`, `kunci` (kolom gabung), lalu
spesifikasi query yang sama dijalankan pada hasil gabungan. Batasi: hanya `inner join`, hanya satu kolom
kunci, dan kedua dataset harus punya kolom itu. Tambahkan definisi JSON schema-nya dan satu kalimat di prompt
sistem.

**Cek:** tes dengan `alat.Alat().jalankan("join_datasets", {...})` menghasilkan kolom `per_kapita` untuk
38 provinsi. Lalu tanyakan ke chatbot "provinsi mana yang belanja per kapitanya tertinggi di 2024?".

---

### Latihan 8 — Ganti provider dan ukur ⭐⭐⭐

Buat API key Gemini gratis, isi di sidebar (session only), dan ajukan lima pertanyaan contoh yang sama ke
Groq dan ke Gemini. Catat untuk masing-masing: jumlah putaran alat, apakah ada putaran gagal, dan waktu
jawab (tambahkan `time.perf_counter()` di sekitar `llm.jawab` di `app.py`, tampilkan di Learning mode).

**Cek:** tabel 5 × 2 dengan tiga kolom itu, plus satu paragraf: model mana yang lebih sering benar di putaran
pertama, dan apakah itu sebanding dengan kecepatannya.

---

### Latihan 9 — Evaluasi otomatis ⭐⭐⭐

Chatbot yang "kelihatannya benar" belum tentu benar. Buat `scripts/evaluasi.py` berisi daftar 10 pertanyaan
beserta **jawaban yang diharapkan**, dihitung langsung dengan `query.jalankan` (bukan ditulis tangan).
Contoh: pertanyaan "provinsi dengan realisasi Belanja Daerah tertinggi 2024" → jawaban yang diharapkan =
`provinsi` di baris pertama hasil query yang sesuai.

Skrip menjalankan `llm.jawab` untuk tiap pertanyaan, lalu memeriksa apakah nilai yang diharapkan muncul di
teks jawaban atau di `Lampiran.hasil`. Cetak skor X/10 dan daftar yang gagal. Perhatikan batas kuota: beri
jeda beberapa detik antar pertanyaan dan tangani `llm.BatasLaju`.

**Cek:** skor pertama kali dijalankan, lalu ubah satu kalimat di prompt sistem (`src/alat.py`) dan jalankan
lagi. Naik atau turun? Sekarang kamu punya alat untuk memperbaiki prompt dengan bukti, bukan perasaan.
