# Hasil Uji Satu Mesin (26 November 2026)

Dijalankan di satu laptop: Laptop A (`presma-a`) dan Laptop B (`presma-b`) sebagai dua Docker Compose, `CLOUD_HOST=host.docker.internal`, `DIFFICULTY=3`, `TAMBANG_TIAP_S=3`. "Jaringan putus" disimulasikan dengan `docker compose stop cloud-api` selama 65 detik.

> Uji di dua laptop sungguhan (kabel/Wi-Fi diputus) belum dijalankan dan wajib diulang kelompok sebelum demo.

## Kemampuan 6: token

`tps_gadungan.py` tanpa token:

```text
suara palsu 1 -> 401 {"detail":"token TPS salah"}
suara palsu 2 -> 401 {"detail":"token TPS salah"}
```

Kiriman yang membawa token benar tetapi kode buktinya tidak cocok dengan isi suara ditolak `422 bukti tidak cocok dengan isi suara` (terlihat pada run pertama di bawah). Ini cek keutuhan isi suara, bukan pengganti token: pihak yang memegang token bisa menghitung kode bukti sendiri.

## Output lengkap

Bagian "Kemampuan 6" di bawah ini adalah run pertama, sebelum `tps_gadungan.py` diperbaiki (saat itu skrip masih mengirim token asli). Hasil setelah perbaikan ada di atas.

```text

### Kemampuan 6: tps_gadungan.py (tanpa token)
suara palsu 1 -> 422 {"detail":"bukti tidak cocok dengan isi suara"}
suara palsu 2 -> 422 {"detail":"bukti tidak cocok dengan isi suara"}
suara palsu 3 -> 422 {"detail":"bukti tidak cocok dengan isi suara"}
suara palsu 4 -> 422 {"detail":"bukti tidak cocok dengan isi suara"}
suara palsu 5 -> 422 {"detail":"bukti tidak cocok dengan isi suara"}

### Kemampuan 3: uji_urutan.py
arah pesan                 pasangan  terbalik (fisik)  terbalik (Lamport)
voter-sim -> edge-api            46                 0                   0
edge-api -> cloud-api            36                 0                   0
cloud-api -> edge-api            38                 0                   0
edge-api -> voter-sim            46                 0                   0

Timestamp fisik : LULUS
Lamport clock   : LULUS

### Uji rancangan kelompok: restart cloud-api di tengah voting
sebelum:
{"pemungutan":"buka","total_suara":36,"kiriman_ganda":0,"pemilih_ganda":0,"per_kandidat":{"1":19,"2":17},"per_tps":{"tps-ft":36},"catatan":"Partisipasi: 36 dari 150 pemilih (24.0%)."}
sesudah restart + 15 detik:
{"pemungutan":"buka","total_suara":41,"kiriman_ganda":0,"pemilih_ganda":0,"per_kandidat":{"1":20,"2":21},"per_tps":{"tps-ft":41},"catatan":"Partisipasi: 41 dari 150 pemilih (27.3%)."}
{"valid":true,"index_rusak":null,"alasan":"rantai valid","panjang":23}

Timestamp fisik : LULUS
Lamport clock   : LULUS

### Kemampuan 8 + aturan unik: pusat rekap tidak terjangkau 65 detik
sebelum:
{"tps_id":"tps-ft","pemungutan":"buka","masuk":57,"diterima":42,"ditolak":15,"antre":0,"terkirim":42}
{"pemungutan":"buka","total_suara":42,"kiriman_ganda":0,"pemilih_ganda":0,"per_kandidat":{"1":21,"2":21},"per_tps":{"tps-ft":42},"catatan":"Partisipasi: 42 dari 150 pemilih (28.0%)."}
suara bilik saat putus, kode bukti: 5f9b84ce18c975b3
status di TPS: {"bukti":"5f9b84ce18c975b3","status":"antre di TPS"}
selama putus (30 dtk):
{"tps_id":"tps-ft","pemungutan":"buka","masuk":73,"diterima":55,"ditolak":18,"antre":13,"terkirim":42}
selama putus (65 dtk):
{"tps_id":"tps-ft","pemungutan":"buka","masuk":91,"diterima":67,"ditolak":24,"antre":25,"terkirim":42}
sesudah tersambung + 20 detik:
{"tps_id":"tps-ft","pemungutan":"buka","masuk":101,"diterima":68,"ditolak":33,"antre":0,"terkirim":68}
{"pemungutan":"buka","total_suara":68,"kiriman_ganda":0,"pemilih_ganda":0,"per_kandidat":{"1":35,"2":33},"per_tps":{"tps-ft":68},"catatan":"Partisipasi: 68 dari 150 pemilih (45.3%)."}
{"valid":true,"index_rusak":null,"alasan":"rantai valid","panjang":26}
status bukti di pusat rekap: {"bukti":"5f9b84ce18c975b3","status":"tercatat di block 24"}
status bukti di TPS: {"bukti":"5f9b84ce18c975b3","status":"terkirim"}

### Kemampuan 7: ukur_voting.py beban 150 (volume baru)
Suara dikirim ke TPS         : 150
Diterima TPS                 : 150
Laju terima di TPS           : 103.3 suara/detik
Semua sampai di pusat dalam  : 18.6 detik
Throughput sampai pusat      : 8.1 suara/detik
Suara dengan latensi terukur : 150
Latensi simpan -> terkirim   : p50 8.35 s | p95 16.97 s | maks 17.03 s
Masuk ke TPS                 : 150
Ditolak di TPS               : 0
Disetor ke pusat rekap       : 150
Disaring di TPS              : 0.0% dari yang masuk
{"pemungutan":"buka","total_suara":150,"kiriman_ganda":0,"pemilih_ganda":0,"per_kandidat":{"1":67,"2":83},"per_tps":{"tps-ft":150},"catatan":"Partisipasi: 150 dari 150 pemilih (100.0%)."}
{"valid":true,"index_rusak":null,"alasan":"rantai valid","panjang":7}
```
