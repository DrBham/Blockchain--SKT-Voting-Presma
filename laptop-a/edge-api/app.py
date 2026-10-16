import os
import socket
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import lamport as clock
import pengumuman
import tps_db as db
from daftar import KANDIDAT, PEMILIH
from nim import periksa_nim
from setor import mulai_setor

TPS_ID = os.getenv("TPS_ID", "tps-1")

app = FastAPI(title="edge-api (TPS)")
mulai_setor()  # penyetor bekerja di latar, terpisah dari pelayanan pemilih


class SuaraMasuk(BaseModel):
    pemilih_id: str
    pilihan: int
    asal: str = "bilik"  # "bilik" (halaman bilik suara) atau "voter-sim"
    lamport: int = 0


@app.get("/")
def echo():
    # echo service dari Praktikum 1 tetap dipertahankan untuk ukur.py
    return {
        "host": socket.gethostname(),
        "waktu_unix": time.time(),
        "waktu_lokal": time.strftime("%H:%M:%S"),
    }


@app.get("/bilik", response_class=HTMLResponse)
def bilik():
    return Path("bilik.html").read_text(encoding="utf-8")


@app.get("/daftar")
def daftar():
    return {"tps_id": TPS_ID, "kandidat": KANDIDAT, "jumlah_pemilih": len(PEMILIH)}


@app.get("/status")
def status():
    return {"tps_id": TPS_ID, **pengumuman.status, **db.hitung()}


def periksa(s):
    # pemeriksaan lokal: dikerjakan di TPS, tanpa bertanya ke pusat rekap
    # [FITUR 1] suara hanya diterima selama pemungutan dibuka
    pemungutan = pengumuman.status["pemungutan"]
    # LENGKAPI: bila pemungutan bernilai "tutup", kembalikan "pemungutan sudah ditutup"
    if pemungutan == "tutup":
        return "pemungutan sudah ditutup"
    # LENGKAPI: bila pemungutan bukan "buka", kembalikan "pemungutan belum dibuka"
    if pemungutan != "buka":
        return "pemungutan belum dibuka"
    alasan_nim = periksa_nim(s.pemilih_id)
    if alasan_nim:
        return alasan_nim
    if s.pemilih_id not in PEMILIH:
        return "pemilih tidak terdaftar"
    if s.pilihan not in KANDIDAT:
        return "pilihan tidak sah"
    if db.sudah_memilih(s.pemilih_id):
        return "pemilih sudah memilih"
    return None


@app.post("/suara")
def terima_suara(s: SuaraMasuk):
    if s.asal == "voter-sim":
        clock.terima(s.lamport, "terima", dari="voter-sim", pemilih_id=s.pemilih_id)
    else:
        clock.lokal("pilih-di-bilik", pemilih_id=s.pemilih_id)

    # periksa, simpan di TPS, lalu langsung jawab pemilih.
    # Penyetoran ke pusat rekap diurus setor.py, tidak ditunggu di sini.
    alasan = periksa(s)
    seq = None
    if alasan is None:
        seq = db.simpan_lokal(s.pemilih_id, s.pilihan)
        if seq is None:
            alasan = "pemilih sudah memilih"
    if alasan is None:
        clock.lokal("simpan", seq=seq)
    else:
        db.catat_tolak(s.pemilih_id, alasan)
        clock.lokal("tolak", alasan=alasan)

    balasan = {"diterima": alasan is None, "alasan": alasan, "seq": seq}
    if s.asal == "voter-sim":
        balasan["lamport"] = clock.kirim("balas", ke="voter-sim", seq=seq)
    return balasan
