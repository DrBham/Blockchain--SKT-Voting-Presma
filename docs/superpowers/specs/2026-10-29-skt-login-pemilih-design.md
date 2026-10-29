# Rancangan: login pemilih di TPS (fitur tambahan kelompok)

Tanggal: 29 Oktober 2026

## Tujuan

Pemilih harus punya akun sebelum mencoblos di bilik Laptop A, sama seperti web project Blockchain kelompok:
daftar akun → verifikasi email → masuk dengan NIM + password + kode pemilih → bilik (Setuju/Batal) → bukti.
Delapan kemampuan inti dan empat poin demo tubes tetap lulus tanpa mengubah alat uji modul secara besar.

## Keputusan

1. **Tanpa DPT.** Semua mahasiswa aktif berhak memilih. Bukti aktif = kode yang dikirim ke `NIM@untad.ac.id`.
   `daftar.py` hanya menyimpan `KANDIDAT`. DPT bukan syarat tubes; Kemampuan 4 tetap terpenuhi oleh pemeriksaan lokal:
   format NIM, kode fakultas, akun belum ada/belum aktif, sesi tidak ada/habis, sudah memilih, pemungutan belum/sudah ditutup,
   pilihan tidak sah.
2. **Akun di Laptop A.** Tabel `akun` di `tps.db` (SQLite yang sama). Password dan kode pemilih disimpan sebagai hash
   (`hashlib.scrypt`, stdlib). Kode 6 digit, maksimal 5 salah lalu kirim ulang (jeda 60 detik), akun yang belum diverifikasi
   dikunci 15 menit dari pendaftaran ulang, kode hangus setelah memilih.
3. **Sesi.** Masuk menghasilkan token acak di memori edge-api (berlaku 15 menit), dikirim sebagai cookie `sesi` (HttpOnly)
   untuk halaman, atau header `X-Sesi` untuk voter-sim dan `ukur_voting.py`. `POST /suara` mengambil `pemilih_id` dari sesi.
4. **Email.** SMTP ke `MAIL_HOST:MAIL_PORT` (Mailpit di compose Laptop A, UI port 8025). Bila gagal, kode dicetak di log edge-api.
5. **voter-sim ikut login.** Saat start, edge-api membuat 150 akun simulasi yang langsung aktif (NIM dengan pola lama
   A121/C301/F551 × angkatan 19,22–25 × 001–010), password `SIM_PASSWORD`, kode `SIM_KODE` dari `.env`. voter-sim masuk dulu,
   menyimpan token per NIM, lalu memilih. Sesekali tetap mengirim NIM salah supaya penolakan terlihat.
6. **Partisipasi di papan Laptop B.** Laptop B tidak tahu jumlah akun, jadi setiap kiriman setor membawa `terdaftar`
   (jumlah akun aktif di TPS itu). Papan memakai jumlah terbaru per TPS sebagai pembagi.
7. **Tampilan** mengikuti tema slate project Blockchain (rel 5 langkah, kertas suara, dialog Setuju/Batal fokus di Batal).
   Endpoint Praktikum 5 (`/bilik`, `/daftar`, `/status`, `/suara`, `/bukti/{kode}`) tetap ada.

## Bukan sasaran

Kunci RSA per pemilih dan suara terenkripsi (itu fitur project Blockchain); login panitia untuk papan Laptop B.
