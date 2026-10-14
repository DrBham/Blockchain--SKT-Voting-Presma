import glob
import json
import os
import threading
import time

SERVICE = os.getenv("SERVICE", "tanpa-nama")
GESER_MS = int(os.getenv("GESER_MS", "0"))  # hanya untuk percobaan C.4
LOG_DIR = os.getenv("LOG_DIR", "/log")
LOG_FILE = os.path.join(LOG_DIR, SERVICE + ".jsonl")

_kunci = threading.Lock()
_nilai = 0


def _baca(file):
    try:
        with open(file) as f:
            return [json.loads(baris) for baris in f if baris.strip()]
    except FileNotFoundError:
        return []


# bila container di-restart, clock melanjutkan nilai terakhir di log
for _event in _baca(LOG_FILE):
    _nilai = max(_nilai, _event["lamport"])


def _catat(event, info):
    baris = {"service": SERVICE, "event": event, "lamport": _nilai,
             "fisik": int(time.time() * 1000) + GESER_MS, **info}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(baris) + "\n")


def lokal(event, **info):
    # Aturan 1: setiap event menaikkan clock satu langkah
    global _nilai
    with _kunci:
        _nilai += 1
        _catat(event, info)
        return _nilai


def kirim(event, ke, **info):
    # Aturan 2: mengirim juga sebuah event. Nilai clock dititipkan di pesan
    return lokal(event, ke=ke, **info)


def terima(nilai_pesan, event, dari, **info):
    # Aturan 3: ambil yang lebih besar antara clock sendiri dan clock
    # di pesan, lalu naikkan satu langkah
    global _nilai
    with _kunci:
        _nilai = max(_nilai, nilai_pesan) + 1
        _catat(event, {"dari": dari, "dari_lamport": nilai_pesan, **info})
        return _nilai


def baca_log(terakhir=400):
    # event terbaru dari semua service di host ini
    semua = []
    for file in glob.glob(os.path.join(LOG_DIR, "*.jsonl")):
        semua += _baca(file)[-terakhir:]
    return semua
