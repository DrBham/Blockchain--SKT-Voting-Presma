import logging
import os

import httpx

import lamport as clock

CLOUD_HOST = os.environ["CLOUD_HOST"]
TIMEOUT_S = float(os.getenv("TIMEOUT_S", "1"))
MAKS_COBA = int(os.getenv("MAKS_COBA", "3"))
TPS_TOKEN = os.getenv("TPS_TOKEN", "")
log = logging.getLogger("uvicorn.error")


def kirim_rest(pesan):
    url = f"http://{CLOUD_HOST}:9090/suara"
    seq = pesan["seq"]
    for coba in range(1, MAKS_COBA + 1):
        # aturan 2: nilai clock dititipkan di pesan
        pesan["lamport"] = clock.kirim("kirim", ke="cloud-api", seq=seq, coba=coba)
        try:
            # [FITUR 2] LENGKAPI: kirim token TPS sebagai header X-TPS-Token
            r = httpx.post(url, json=pesan, timeout=TIMEOUT_S, headers={"X-TPS-Token": TPS_TOKEN})
            if r.status_code == 201:
                # aturan 3: balasan dari cloud-api diterima
                clock.terima(r.json().get("lamport", 0), "terima-balasan",
                             dari="cloud-api", seq=seq, coba=coba)
            log.info("SETOR seq=%s coba=%s -> %s %s",
                     seq, coba, r.status_code, r.text)
            return {"terkirim": r.status_code == 201, "coba": coba}
        except httpx.TimeoutException:
            clock.lokal("timeout", seq=seq, coba=coba)
            log.warning("SETOR seq=%s coba=%s -> timeout, kirim ulang",
                        seq, coba)
        except httpx.TransportError as e:
            # pusat rekap tidak terjangkau: tidak ada gunanya langsung mencoba lagi
            log.warning("SETOR seq=%s coba=%s -> gagal terhubung (%s)",
                        seq, coba, type(e).__name__)
            break
    return {"terkirim": False, "coba": coba}
