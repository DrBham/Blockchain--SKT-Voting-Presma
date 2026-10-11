# Desain: Voting Presma UNTAD Terdistribusi Berbasis Blockchain (Tubes SKT)

Tanggal: 26 November 2026 · Kelompok 4 · Mata kuliah Sistem Komputasi Terdistribusi (Sub-CPMK 4 & 5)

## 1. Maksud dan alasan

Tubes SKT meminta aplikasi voting dua laptop yang dibangun dari fondasi Praktikum 3–5. Dosen membolehkan kelompok melanjutkan project blockchain dari mata kuliah Teknologi Blockchain (PB1 + PB2). Kelompok ingin dua hal sekaligus:

1. Asisten praktikum yang menilai langsung mengenali struktur, nama file, endpoint, dan alat uji dari modul SKT.
2. Konsep blockchain dari PB1/PB2 tetap menjadi ciri khas aplikasi.

Karena itu kerangka aplikasi **mengikuti Praktikum 5 apa adanya**, dan blockchain menjadi lapisan pencatatan suara di pusat rekap (Laptop B) serta dasar aturan unik.

## 2. Kasus (lima hal Bagian 2)

| Hal | Isi |
| --- | --- |
| Nama kegiatan | Pemilihan Presiden Mahasiswa (Presma) Universitas Tadulako |
| Yang dipilih | Dua pasangan calon: `Paslon 1` dan `Paslon 2`. Nama calon tidak dicantumkan di aplikasi, laporan, maupun data |
| Yang boleh memberi suara | Mahasiswa aktif semua angkatan yang ada di Daftar Pemilih Tetap (DPT) rekaan, dikenali dari NIM format UNTAD (mis. `F55125001`). Batas semester 3–7 di Peraturan Rektor Untad No. 1/2021 Pasal 20 ayat (1) huruf a hanya syarat calon, bukan pemilih |
| Tempat pengumpulan dan penghitungan | Laptop A = TPS Fakultas Teknik (`tps-ft`); Laptop B = Pusat Rekap KPU Mahasiswa |
| Waktu dibuka/ditutup | Dibuka dan ditutup dari papan hasil Laptop B, diumumkan ke TPS lewat MQTT (mekanisme Praktikum 5) |

Kasusnya nyata (Presma UNTAD), tetapi data pemilih rekaan dan nama calon tidak dipakai. Tidak ada data pribadi orang sungguhan.

## 3. Aturan unik: Bukti suara bagi pemilih

Setiap suara yang diterima TPS menghasilkan **kode bukti**: hash SHA-256 (16 karakter pertama ditampilkan) dari isi suara yang disetor. Pemilih bisa memasukkan kode itu di papan hasil Laptop B dan melihat statusnya:

| Status di papan Laptop B | Arti |
| --- | --- |
| `belum diterima pusat rekap` | Suara masih di buffer TPS (mis. jaringan putus) |
| `diterima, menunggu ditambang` | Suara sudah di pusat rekap, ada di pool, belum masuk block |
| `tercatat di block N` | Suara sudah tercatat permanen di rantai |

Halaman bilik Laptop A juga menampilkan status lokal kode yang sama (`antre di TPS` / `terkirim`). Papan **tidak** menampilkan pilihan paslon untuk kode bukti, hanya statusnya.

Mengapa ini aturan unik (bukan sekadar tampilan): cara suara diterima berubah (setiap suara wajib membawa kode bukti yang dihitung ulang dan dicocokkan oleh pusat rekap; suara yang kodenya tidak cocok ditolak), dan ada fitur baru yang bisa diuji. Aturan ini tidak dipakai kelompok lain yang sudah terdaftar (K9 mayoritas mutlak, K3 survei MBG, K2 rata-rata nilai).

Uji aturan unik (ditulis di laporan, jaringan normal dan saat putus):
1. Normal: pilih di bilik → catat kode bukti → cek di papan → `tercatat di block N` dalam beberapa detik.
2. Putus ≥60 detik: pilih di bilik → kode bukti → papan Laptop B `belum diterima pusat rekap`, bilik `antre di TPS` → sambung lagi → papan `tercatat di block N`, total suara bertambah tepat 1.
3. Kode bukti palsu atau salah ketik → `tidak ditemukan`.

## 4. Pendekatan yang dipertimbangkan

| Pendekatan | Untung | Rugi | Keputusan |
| --- | --- | --- | --- |
| A. Blockchain P2P PB1/PB2 disusun ulang mengikuti konsep SKT | Blockchain jadi inti sistem | Struktur, endpoint, dan alat uji beda dari modul; asisten harus belajar kode baru; library REST stdlib, bukan FastAPI/MQTT | Tidak dipilih |
| **B. Kerangka Praktikum 5 + blockchain sebagai buku besar di pusat rekap** | Struktur sama dengan modul (edge-api, voter-sim, cloud-api, mosquitto, `.env`, `lamport.py`, `setor.py`, `uji_urutan.py`, `ukur_voting.py`); asisten tidak bingung | Blockchain tidak lagi multi-node P2P | **Dipilih kelompok** |

## 5. Arsitektur

Sama dengan Praktikum 5. Yang baru ditandai **(baru)**.

| Laptop | Service (Docker Compose) | Port host | Peran |
| --- | --- | --- | --- |
| A | `edge-api` (FastAPI) | 8080 | Bilik suara, pemeriksaan, buffer SQLite `tps.db`, penyetor `setor.py` dengan kirim ulang, Lamport, **kode bukti (baru)** |
| A | `voter-sim` | – | Simulasi pemilih (dengan NIM Presma) |
| B | `cloud-api` (FastAPI) | 9090 | Terima suara bertoken, idempoten `request_id`, rekap, papan, Lamport, **rantai block (baru)**, **cek bukti (baru)** |
| B | `mosquitto` | 1883 | Pengumuman buka/tutup (MQTT) |

Alur satu suara: bilik/voter-sim → `edge-api` periksa → simpan `antre` di `tps.db` + hitung kode bukti → `setor.py` kirim REST ke `cloud-api` dengan header `X-TPS-Token` (kirim ulang bila gagal) → `cloud-api` cek token, cocokkan kode bukti, simpan ke SQLite (idempoten) **dan masukkan ke pool rantai** → penambang latar di `cloud-api` membentuk block (PoW) → papan menampilkan rekap dan status bukti.

### Blockchain di pusat rekap (baru)

File baru `laptop-b/cloud-api/rantai.py`, diadaptasi dari `node.py` PB1/PB2 (bukan disalin utuh):

- `Block`: `index`, `timestamp`, `transaksi` (list suara), `previous_hash`, `nonce`, `hash` (SHA-256 JSON terurut), genesis tetap.
- Proof of work dengan `DIFFICULTY` dari `.env` (default 3, agar demo cepat).
- Pool: suara yang diterima `cloud-api` masuk pool; thread penambang membentuk block setiap `TAMBANG_TIAP_S` detik (default 3) bila pool tidak kosong.
- `validasi_rantai()`: cek hash, previous hash, PoW; mengembalikan index block pertama yang rusak.
- Persistensi: rantai disimpan ke `/data/rantai.json` (volume `data-pusat`) setiap block baru, dimuat lagi saat container start, supaya restart atau uji partisi tidak menghilangkan block.
- Suara di pool yang belum ditambang juga harus selamat saat restart: pool dibangun ulang dari tabel SQLite `suara` yang belum punya nomor block.

Peran SQLite di Laptop B tetap seperti praktikum (rekap cepat, idempoten). Tabel `suara` ditambah kolom `bukti` dan `block` (nomor block, NULL bila belum ditambang).

### Endpoint

Tetap: semua endpoint Praktikum 5 (`/suara`, `/rekap`, `/pemungutan/{nilai}`, `/papan`, `/event`, `/status`, `/bilik`, `/daftar`).

Baru:
- Laptop B `GET /bukti/{kode}` → status bukti (tabel di bagian 3).
- Laptop B `GET /rantai` → ringkasan block; `GET /rantai/validasi` → valid atau index block rusak.
- Laptop A `GET /bukti/{kode}` → status lokal (`antre di TPS` / `terkirim` / `tidak ditemukan`).
- Balasan `POST /suara` di Laptop A ditambah field `bukti`.

### Lamport

`lamport.py` tidak diubah. Event baru di `cloud-api`: `lokal("tambang", block=N, jumlah=k)` setiap block terbentuk. Pasangan kirim–terima yang dibaca `uji_urutan.py` tetap sama.

### Konfigurasi (`.env`)

Laptop A tetap (`CLOUD_HOST`, `TPS_ID=tps-ft`, `TIMEOUT_S`, `MAKS_COBA`, `TPS_TOKEN`, `SETOR_TIAP_S`, `SETOR_MAKS`). Laptop B tambah `DIFFICULTY=3`, `TAMBANG_TIAP_S=3`. File `.env` tidak di-commit; ada `.env.example` tanpa token asli.

### Data rekaan

- Pemilih (DPT rekaan, 150): 3 fakultas × 5 angkatan × 10 orang, `{f"{fak}{prodi}{th}{n:03d}" for fak, prodi in (("A", "121"), ("C", "301"), ("F", "551")) for th in ("19", "22", "23", "24", "25") for n in range(1, 11)}`. Cocok dengan `JUMLAH_PEMILIH = 150`.
- Pemeriksaan pemilih di Laptop A memakai aturan dari project Blockchain, berurutan: format NIM (1 huruf kapital + 7–8 digit) → kode fakultas UNTAD (`A B C D E F G K L N P`, pesan `Kode Fakultas 'X' tidak terdaftar di UNTAD!`) → ada di DPT (`pemilih tidak terdaftar`) → belum memilih. Tidak ada batas angkatan.
- Paslon: `{1: "Paslon 1", 2: "Paslon 2"}`, tanpa nama calon.
- `voter-sim`: NIM acak dari daftar, pilihan acak antara paslon 1 dan 2, sesekali NIM tak terdaftar (`X...`) dan paslon tak ada (9), seperti praktikum.

## 6. Bukti delapan kemampuan inti

| # | Kemampuan | Cara (alat dari modul) |
| --- | --- | --- |
| 1 | Dua laptop, ≥2 service, suara A sampai B | 2 compose (edge-api + voter-sim, cloud-api + mosquitto) |
| 2 | Alamat dari file pengaturan | `laptop-a/.env` `CLOUD_HOST` |
| 3 | Urutan Lamport | `uji_urutan.py` + uji rancangan kelompok: restart `cloud-api` di tengah voting, lalu `uji_urutan.py` tetap LULUS dan rantai tetap valid |
| 4 | Periksa di A, tolak, buffer | `periksa()` + `tps.db` status `antre` |
| 5 | B simpan, hitung, tampilkan | `/rekap`, `/papan` |
| 6 | Token | `tps_gadungan.py` → 401 |
| 7 | Kinerja | `ukur_voting.py beban 150` (throughput, p50/p95, ditolak) |
| 8 | Putus ≥60 detik | Catat `/status` A dan `/rekap` B sebelum/selama/sesudah; tidak ada hilang/dobel (`kiriman_ganda`, `pemilih_ganda` = 0) + rantai valid |

## 7. Tujuan, bukan-tujuan, dan anti-tujuan

Tujuan:
- Lolos delapan kemampuan inti dengan alat uji modul tanpa modifikasi besar.
- Aturan unik bukti suara bekerja normal dan saat putus.
- Blockchain di pusat rekap bisa diperiksa (validasi rantai) dan dijelaskan saat penilaian individu.

Bukan tujuan:
- Jaringan blockchain multi-node/P2P, smart contract, web CRUD paslon, tanda tangan digital per pemilih (semuanya milik mata kuliah Blockchain).
- Kerahasiaan suara end-to-end.

Anti-tujuan (gagal walau jalan):
- Mengubah nama file, endpoint, port, atau format log praktikum sehingga `uji_urutan.py`/`ukur_voting.py` tidak jalan atau asisten tidak mengenali alurnya.
- Menyentuh atau mencampur folder project Blockchain (`E:\Kuliah\Semester 5\Block Chain\Project Base 1`).
- Penambangan memperlambat penerimaan suara sampai latensi p95 melonjak (penambang harus di thread latar, bukan di jalur `POST /suara`).

## 8. Batasan

- Lokasi: `E:\Kuliah\Semester 5\Sistem Komputasi Terdistribusi\skt-presma-blockchain\`, repo git sendiri.
- Basis kode: salinan `skt-voting` milik kelompok (Praktikum 5 yang sudah dilengkapi), bukan ZIP LMS.
- Library: tetap `requirements.txt` praktikum (FastAPI, uvicorn, httpx, paho-mqtt). Blockchain hanya pakai stdlib (`hashlib`, `json`), tanpa library blockchain.
- Tenggat SKT 10 Desember 2026; tenggat PB2 Blockchain 3 Desember 2026 didahulukan kelompok.

## 9. Keputusan kecil (dibuat perancang, boleh dikoreksi)

- Kode bukti = 16 karakter hex pertama dari SHA-256 atas JSON terurut field `request_id`, `tps_id`, `seq`, `pemilih_id`, `pilihan`, `waktu`. Laptop A menghitungnya saat suara disimpan; Laptop B menghitung ulang dari pesan yang diterima dan menolak (422) bila tidak sama. 16 hex cukup untuk 150 pemilih.
- Suara yang sama dikirim ulang (`request_id` sama) tidak masuk pool dua kali; ikut jalur idempoten yang sudah ada. Mode percobaan `IDEMPOTEN=0` dari praktikum dibiarkan apa adanya.
- Blockchain hanya di Laptop B. Laptop A tidak menyimpan replika rantai.

## 10. Yang diserahkan ke builder

- Bentuk visual kolom cek bukti di `papan.html` dan tampilan kode bukti di `bilik.html` (ikuti gaya CSS yang ada).
- README berbahasa Inggris untuk folder baru.
