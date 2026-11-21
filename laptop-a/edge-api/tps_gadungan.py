# TPS gadungan: menyetor suara palsu langsung ke pusat rekap, tanpa lewat TPS
# dan tanpa token. Dipakai untuk menguji Fitur 2.
import os
import time
import uuid

import httpx

CLOUD_HOST = os.environ["CLOUD_HOST"]

for n in range(1, 6):
    suara = {
        "request_id": str(uuid.uuid4()),
        "tps_id": "tps-gadungan",
        "seq": n,
        "pemilih_id": f"PALSU{n}",
        "pilihan": 3,
        "waktu": int(time.time() * 1000),
    }
    # tanpa header X-TPS-Token: pusat rekap harus menjawab 401 (kemampuan 6)
    r = httpx.post(f"http://{CLOUD_HOST}:9090/suara", json=suara, timeout=3)
    print(f"suara palsu {n} -> {r.status_code} {r.text}")