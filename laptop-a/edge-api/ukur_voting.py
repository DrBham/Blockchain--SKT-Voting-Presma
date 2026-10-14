# Mengukur kinerja penyetoran suara dari sisi TPS.
#   python ukur_voting.py beban 150   -> kirim 150 suara secepatnya, lalu ukur
#   python ukur_voting.py log         -> ukur dari catatan event yang sudah ada
import json
import os
import random
import sys
import time

import httpx

from daftar import KANDIDAT, PEMILIH

TPS = os.getenv("TPS_URL", "http://localhost:8000")
LOG_FILE = os.path.join(os.getenv("LOG_DIR", "/log"), "edge-api.jsonl")


def status():
    return httpx.get(TPS + "/status", timeout=5).json()


def persentil(data, p):
    return sorted(data)[min(len(data) - 1, int(len(data) * p / 100))]


def latensi(sejak_ms=0):
    # selisih waktu antara event simpan dan event terima-balasan untuk seq yang
    # sama. Keduanya dicatat jam Laptop A, jadi clock skew tidak ikut campur
    simpan, hasil = {}, []
    with open(LOG_FILE) as f:
        for baris in f:
            e = json.loads(baris)
            if e["fisik"] < sejak_ms:
                continue
            if e["event"] == "simpan":
                simpan[e["seq"]] = e["fisik"]
            elif e["event"] == "terima-balasan" and e.get("seq") in simpan:
                hasil.append((e["fisik"] - simpan.pop(e["seq"])) / 1000)
    return hasil


def laporkan(hasil):
    s = status()
    print(f"Suara dengan latensi terukur : {len(hasil)}")
    if hasil:
        print(f"Latensi simpan -> terkirim   : p50 {persentil(hasil, 50):.2f} s | "
              f"p95 {persentil(hasil, 95):.2f} s | maks {max(hasil):.2f} s")
    print(f"Masuk ke TPS                 : {s['masuk']}")
    print(f"Ditolak di TPS               : {s['ditolak']}")
    print(f"Disetor ke pusat rekap       : {s['terkirim']}")
    if s["masuk"]:
        saring = 100 * s["ditolak"] / s["masuk"]
        print(f"Disaring di TPS              : {saring:.1f}% dari yang masuk")


if len(sys.argv) > 1 and sys.argv[1] == "beban":
    jumlah = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    awal = status()
    if awal["pemungutan"] != "buka":
        sys.exit("Pemungutan belum dibuka. Klik Buka di papan hasil lebih dulu.")
    if awal["masuk"] > 0:
        sys.exit("TPS belum kosong. Jalankan down -v di kedua laptop, lalu ulangi.")
    mulai = time.time()
    diterima = 0
    for pemilih in sorted(PEMILIH)[:jumlah]:
        r = httpx.post(TPS + "/suara", timeout=10, json={
            "pemilih_id": pemilih, "pilihan": random.choice(list(KANDIDAT))})
        diterima += r.json()["diterima"]
    selesai_terima = time.time()
    while status()["antre"] > 0:
        if time.time() - mulai > 300:
            sys.exit("Antrean tidak habis dalam 5 menit. Periksa pusat rekap.")
        time.sleep(0.2)
    selesai_setor = time.time()
    time.sleep(0.5)
    print(f"Suara dikirim ke TPS         : {jumlah}")
    print(f"Diterima TPS                 : {diterima}")
    lama_terima, lama_setor = selesai_terima - mulai, selesai_setor - mulai
    print(f"Laju terima di TPS           : {diterima / lama_terima:.1f} suara/detik")
    print(f"Semua sampai di pusat dalam  : {lama_setor:.1f} detik")
    print(f"Throughput sampai pusat      : {diterima / lama_setor:.1f} suara/detik")
    laporkan(latensi(int(mulai * 1000)))
else:
    laporkan(latensi())
