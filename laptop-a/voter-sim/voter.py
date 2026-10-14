import json
import os
import random
import time
import urllib.request

import lamport as clock

EDGE_URL = os.getenv("EDGE_URL", "http://edge-api:8000")
INTERVAL_S = float(os.getenv("INTERVAL_S", "2"))


def pemilih_acak():
    # sesekali datang orang yang tidak ada di daftar pemilih
    if random.random() < 0.05:
        return f"XX{random.randint(1, 99):03d}"
    # pemilih diambil acak, jadi orang yang sama bisa datang dua kali
    return f"TI{random.randint(1, 200):03d}"


def pilihan_acak():
    # sesekali ada yang memilih kandidat yang tidak ada
    if random.random() < 0.03:
        return 9
    # [FITUR 3] LENGKAPI: tambahkan kandidat baru, lengkap dengan bobotnya
    # bobot 5 untuk kandidat 1, bobot 3 untuk kandidat 2, bobot 2 untuk kandidat 3, bobot 1 untuk kandidat 4
    return random.choices([1, 2, 3, 4], weights=[5, 3, 2, 1])[0]    


while True:
    pemilih, pilihan = pemilih_acak(), pilihan_acak()
    clock.lokal("pilih", pemilih_id=pemilih)
    badan = json.dumps({
        "pemilih_id": pemilih,
        "pilihan": pilihan,
        "asal": "voter-sim",
        "lamport": clock.kirim("kirim", ke="edge-api"),
    }).encode("utf-8")
    req = urllib.request.Request(
        EDGE_URL + "/suara",
        data=badan,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            balasan = json.loads(r.read())
        clock.terima(balasan.get("lamport", 0), "terima-balasan",
                     dari="edge-api", seq=balasan.get("seq"))
        hasil = f"diterima, seq {balasan['seq']}" if balasan["diterima"] \
            else f"DITOLAK: {balasan['alasan']}"
        print(f"voter -> {pemilih} memilih {pilihan} -> {hasil}", flush=True)
    except Exception as e:
        print("voter -> gagal menghubungi edge-api:", e, flush=True)
    time.sleep(INTERVAL_S)
