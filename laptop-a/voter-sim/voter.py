import json
import os
import random
import time
import urllib.error
import urllib.request

import lamport as clock

EDGE_URL = os.getenv("EDGE_URL", "http://edge-api:8000")
INTERVAL_S = float(os.getenv("INTERVAL_S", "2"))
SIM_PASSWORD = os.getenv("SIM_PASSWORD", "pemilih-simulasi")
SIM_KODE = os.getenv("SIM_KODE", "123456")
TANPA_SESI = "belum masuk atau sesi habis"
token = {}  # NIM -> token sesi, supaya tiap akun cukup masuk sekali


def post(path, isi, sesi=None):
    req = urllib.request.Request(
        EDGE_URL + path,
        data=json.dumps(isi).encode("utf-8"),
        headers={"Content-Type": "application/json", **({"X-Sesi": sesi} if sesi else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())  # 4xx tetap membawa alasan


def masuk(pemilih):
    # akun simulasi dibuat edge-api saat start dengan SIM_PASSWORD dan SIM_KODE
    if pemilih not in token:
        r = post("/api/masuk", {"nim": pemilih, "password": SIM_PASSWORD, "kode": SIM_KODE})
        if "token" in r:
            token[pemilih] = r["token"]
            print(f"voter -> {pemilih} masuk", flush=True)
        else:
            print(f"voter -> {pemilih} gagal masuk: {r.get('alasan')}", flush=True)
    return token.get(pemilih)


def pemilih_acak():
    # sesekali datang orang dengan format NIM salah atau yang belum punya akun
    if random.random() < 0.05:
        return f"XX{random.randint(1, 99):03d}"
    if random.random() < 0.05:
        return f"F55125{random.randint(11, 99):03d}"
    # pemilih diambil acak dari akun simulasi, jadi orang yang sama bisa datang dua kali
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
    try:
        sesi = masuk(pemilih)  # gagal masuk: suara tetap dikirim tanpa sesi dan ditolak TPS
        clock.lokal("pilih", pemilih_id=pemilih)
        balasan = post("/suara", {
            "pemilih_id": pemilih,
            "pilihan": pilihan,
            "asal": "voter-sim",
            "lamport": clock.kirim("kirim", ke="edge-api"),
        }, sesi)
        clock.terima(balasan.get("lamport", 0), "terima-balasan",
                     dari="edge-api", seq=balasan.get("seq"))
        if balasan["alasan"] == TANPA_SESI:
            token.pop(pemilih, None)  # sesi habis 15 menit: masuk lagi lain kali
        hasil = f"diterima, seq {balasan['seq']}" if balasan["diterima"]             else f"DITOLAK: {balasan['alasan']}"
        print(f"voter -> {pemilih} memilih {pilihan} -> {hasil}", flush=True)
    except Exception as e:
        print("voter -> gagal menghubungi edge-api:", e, flush=True)
    time.sleep(INTERVAL_S)
