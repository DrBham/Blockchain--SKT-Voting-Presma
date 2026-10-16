import logging
import os
import threading
import time

import tps_db as db
from kirim import kirim_rest

TPS_ID = os.getenv("TPS_ID", "tps-1")
SETOR_TIAP_S = float(os.getenv("SETOR_TIAP_S", "2"))
SETOR_MAKS = int(os.getenv("SETOR_MAKS", "20"))  # paling banyak sekian suara per putaran
log = logging.getLogger("uvicorn.error")


def _putaran():
    while True:
        for s in db.ambil_antre(SETOR_MAKS):
            pesan = {
                "request_id": s["request_id"],  # sama setiap kali suara ini dikirim
                "tps_id": TPS_ID,
                "seq": s["seq"],
                "pemilih_id": s["pemilih_id"],
                "pilihan": s["pilihan"],
                "waktu": s["waktu"],
                "bukti": s["bukti"],  # dicocokkan ulang oleh pusat rekap
            }
            if not kirim_rest(pesan)["terkirim"]:
                break  # pusat rekap belum terjangkau, coba lagi pada putaran berikutnya
            db.tandai_terkirim(s["request_id"])
        time.sleep(SETOR_TIAP_S)


def mulai_setor():
    threading.Thread(target=_putaran, daemon=True).start()
    log.info("penyetor: berjalan, tiap %s detik, paling banyak %s suara per putaran",
             SETOR_TIAP_S, SETOR_MAKS)
