
import os
import hmac
import logging
import threading
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

import bukti
import lamport as clock
import pengumuman
import penyimpanan as db
from rantai import Rantai


TPS_TOKEN = os.getenv("TPS_TOKEN", "")
TAMBANG_TIAP_S = float(os.getenv("TAMBANG_TIAP_S", "3"))
log = logging.getLogger("uvicorn.error")

app = FastAPI(title="cloud-api (pusat rekap)")

# Rantai block pencatat suara. Suara yang sudah diterima tetapi tidak ada di rantai
# (cloud-api di-restart sebelum ditambang, atau berkas rantai rusak) dimasukkan lagi ke pool.
rantai = Rantai(os.getenv("RANTAI_PATH", "/data/rantai.json"), int(os.getenv("DIFFICULTY", "3")))
for _s in db.semua_suara():
    if rantai.cari(_s["bukti"]) is not None:
        db.tandai_block([_s["bukti"]], rantai.cari(_s["bukti"]))
    else:
        rantai.tambah_pool({k: _s[k] for k in (*bukti.FIELD, "bukti")})


def _penambang(berhenti):
    # bekerja di latar: proof of work tidak pernah memperlambat POST /suara
    while not berhenti.is_set():
        try:
            block = rantai.tambang()
            if block:
                db.tandai_block([tx["bukti"] for tx in block["transaksi"]], block["index"])
                clock.lokal("tambang", block=block["index"], jumlah=len(block["transaksi"]))
        except Exception:  # gangguan sesaat (disk, SQLite) tidak boleh mematikan penambang
            log.exception("penambang: gagal, dicoba lagi pada putaran berikutnya")
        berhenti.wait(TAMBANG_TIAP_S)


def mulai_penambang():
    global berhenti
    berhenti = threading.Event()
    threading.Thread(target=_penambang, args=(berhenti,), daemon=True).start()


mulai_penambang()


class Suara(BaseModel):
    request_id: str
    tps_id: str
    seq: int
    pemilih_id: str
    pilihan: int
    waktu: int
    lamport: int = 0
    bukti: str = ""  # boleh kosong agar kiriman tanpa token tetap dijawab 401
    terdaftar: int = 0  # jumlah akun pemilih aktif di TPS pengirim (pembagi partisipasi)


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

    # [ATURAN UNIK] kode bukti dihitung ulang; isi suara yang berubah ditolak
    if bukti.hitung(s.model_dump()) != s.bukti:
        raise HTTPException(
            status_code=422,
            detail="bukti tidak cocok dengan isi suara"
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
    if hasil["tersimpan"]:
        rantai.tambah_pool(s.model_dump(exclude={"lamport", "terdaftar"}))

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


@app.get("/logo-untad.png")
def logo():
    return FileResponse("logo-untad.png", media_type="image/png")


@app.get("/event")
def daftar_event(terakhir: int = 400):
    return clock.baca_log(terakhir)


@app.get("/bukti/{kode}")
def cek_bukti(kode: str):
    # [ATURAN UNIK] pemilih mengecek apakah suaranya sudah tercatat. Pilihan tidak ditampilkan.
    kode = bukti.rapikan(kode)
    if kode is None:
        return {"bukti": kode, "status": "tidak ditemukan"}
    index = rantai.cari(kode)
    if index is not None:
        status = f"tercatat di block {index}"
    elif rantai.di_pool(kode):
        status = "diterima, menunggu ditambang"
    else:
        status = "belum diterima pusat rekap"
    return {"bukti": kode, "status": status}


@app.get("/rantai")
def lihat_rantai(terakhir: int = 10):
    blok = [{"index": b.get("index"), "hash": str(b.get("hash", ""))[:16],
             "jumlah_suara": len(b.get("transaksi") or []), "waktu": b.get("timestamp")}
            for b in rantai.chain[-terakhir:]]
    return {**rantai.ringkas(), "block": blok}


@app.get("/rantai/validasi")
def validasi_rantai():
    valid, rusak, alasan = rantai.validasi()
    return {"valid": valid, "index_rusak": rusak, "alasan": alasan,
            "panjang": len(rantai.chain)}
