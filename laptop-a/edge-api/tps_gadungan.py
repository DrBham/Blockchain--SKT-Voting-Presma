# TPS gadungan: menyetor suara palsu langsung ke pusat rekap, tanpa lewat TPS
# dan tanpa token. Dipakai untuk menguji Fitur 2.
import os
import time
import uuid

import httpx

CLOUD_HOST = os.environ["CLOUD_HOST"]
# Default: tanpa token -> pusat rekap harus menjawab 401 (kemampuan 6).
# TOKEN_GADUNGAN=<token asli> mensimulasikan token yang bocor: pusat rekap tetap
# menolak (422) karena kode bukti suara palsu tidak cocok (aturan unik).
TOKEN = os.getenv("TOKEN_GADUNGAN", "")

for n in range(1, 6):
    suara = {
        "request_id": str(uuid.uuid4()),
        "tps_id": "tps-gadungan",
        "seq": n,
        "pemilih_id": f"PALSU{n}",
        "pilihan": 3,
        "waktu": int(time.time() * 1000),
    }
    headers = {"X-TPS-Token": TOKEN} if TOKEN else {}
    r = httpx.post(f"http://{CLOUD_HOST}:9090/suara", json=suara, headers=headers, timeout=3)
    print(f"suara palsu {n} -> {r.status_code} {r.text}")