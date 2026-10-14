
import os
import hmac
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import lamport as clock
import pengumuman
import penyimpanan as db


TPS_TOKEN = os.getenv("TPS_TOKEN", "")

app = FastAPI(title="cloud-api (pusat rekap)")


class Suara(BaseModel):
    request_id: str
    tps_id: str
    seq: int
    pemilih_id: str
    pilihan: int
    waktu: int
    lamport: int = 0


@app.post("/suara", status_code=201)
def terima_suara(
    s: Suara,
    x_tps_token: str = Header(default="")
):
    # FITUR 2: Autentikasi TPS
    # Tolak jika token kosong, salah, atau belum dikonfigurasi.
    if (
        not TPS_TOKEN
        or not x_tps_token
        or not hmac.compare_digest(x_tps_token, TPS_TOKEN)
    ):
        raise HTTPException(
            status_code=401,
            detail="token TPS salah"
        )

    # Hanya pesan yang lolos autentikasi
    # yang dicatat dalam Lamport Clock.
    clock.terima(
        s.lamport,
        "terima",
        dari="edge-api",
        seq=s.seq
    )

    hasil = db.simpan(s.model_dump())

    return {
        **hasil,
        "lamport": clock.kirim(
            "balas",
            ke="edge-api",
            seq=s.seq
        )
    }


@app.get("/suara")
def daftar_suara(terakhir: int = 10):
    return db.ambil(terakhir)


@app.get("/rekap")
def rekap():
    return {
        "pemungutan": db.status(),
        **db.rekap()
    }


@app.post("/pemungutan/{nilai}")
def ubah_pemungutan(nilai: str):
    if nilai not in ("buka", "tutup"):
        raise HTTPException(
            status_code=422,
            detail="nilai harus buka atau tutup"
        )

    db.ubah_status(nilai)
    return pengumuman.umumkan(nilai)


@app.get("/papan", response_class=HTMLResponse)
def papan():
    return Path("papan.html").read_text(
        encoding="utf-8"
    )


@app.get("/event")
def daftar_event(terakhir: int = 400):
    return clock.baca_log(terakhir)
