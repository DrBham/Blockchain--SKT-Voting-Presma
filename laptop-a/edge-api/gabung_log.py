import glob
import json
import os
import sys

import httpx

CLOUD_HOST = os.environ["CLOUD_HOST"]
LOG_DIR = os.getenv("LOG_DIR", "/log")
URUT = {
    "fisik": lambda e: (e["fisik"], e["service"]),
    "lamport": lambda e: (e["lamport"], e["service"]),
}


def ambil_event():
    # event Laptop A dibaca dari volume /log,
    # event Laptop B diminta ke cloud-api lewat REST
    semua = []
    for file in glob.glob(os.path.join(LOG_DIR, "*.jsonl")):
        with open(file) as f:
            semua += [json.loads(baris) for baris in f if baris.strip()][-400:]
    semua += httpx.get(f"http://{CLOUD_HOST}:9090/event", timeout=5).json()
    return semua


def pasangkan(semua):
    # setiap event terima dipasangkan dengan event kirim asalnya
    kirim = {(e["service"], e["lamport"]): e for e in semua if "ke" in e}
    pasangan = []
    for e in semua:
        asal = kirim.get((e.get("dari"), e.get("dari_lamport")))
        if asal and asal["ke"] == e["service"]:
            pasangan.append((asal, e))
    return pasangan


def jam(ms):
    # menit:detik.milidetik, cukup untuk membandingkan dua laptop
    return f"{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


if __name__ == "__main__":
    urut = sys.argv[1] if len(sys.argv) > 1 else "lamport"
    seq = int(sys.argv[2]) if len(sys.argv) > 2 else None
    semua = sorted(ambil_event(), key=URUT[urut])
    posisi = {id(e): i for i, e in enumerate(semua)}
    terbalik = {id(t) for k, t in pasangkan(semua) if posisi[id(t)] < posisi[id(k)]}
    if seq is not None:
        semua = [e for e in semua if e.get("seq") == seq]
    print(f"diurutkan menurut: {urut}")
    print(f"{'fisik':<11}{'lamport':>7}  {'service':<12}{'event':<16}"
          f"{'seq':>4}{'coba':>5}{'bawa':>6}")
    for e in semua[-18:]:
        print(f"{jam(e['fisik']):<11}{e['lamport']:>7}  {e['service']:<12}{e['event']:<16}"
              f"{str(e.get('seq') or '-'):>4}{str(e.get('coba') or '-'):>5}"
              f"{str(e.get('dari_lamport', '-')):>6}"
              + ("   <-- terima sebelum kirim" if id(e) in terbalik else ""))
