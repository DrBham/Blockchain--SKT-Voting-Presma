import json
import os
import random
import time
import urllib.request

import lamport as clock

EDGE_URL = os.getenv("EDGE_URL", "http://edge-api:8000")
INTERVAL_S = float(os.getenv("INTERVAL_S", "2"))


def pemilih_acak():
    # sesekali datang orang dengan format NIM salah atau yang tidak ada di DPT
    if random.random() < 0.05:
        return f"XX{random.randint(1, 99):03d}"
    if random.random() < 0.05:
        return f"F55125{random.randint(11, 99):03d}"
    # pemilih diambil acak dari DPT, jadi orang yang sama bisa datang dua kali
    fak, prodi = random.choice((("A", "121"), ("C", "301"), ("F", "551")))
    th = random.choice(("19", "22", "23", "24", "25"))
    return f"{fak}{prodi}{th}{random.randint(1, 10):03d}"


def pilihan_acak():
    # sesekali ada yang memilih paslon yang tidak ada
    if random.random() < 0.03:
        return 9
    return random.choice([1, 2])

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
