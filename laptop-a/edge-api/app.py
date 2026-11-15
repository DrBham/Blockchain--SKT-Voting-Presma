import os
import socket
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import akun
import lamport as clock
import pengumuman
import tps_db as db
from daftar import KANDIDAT
from nim import periksa_nim
from setor import mulai_setor

TPS_ID = os.getenv("TPS_ID", "tps-1")
HALAMAN = Path(__file__).parent / "halaman"
TANPA_SESI = "belum masuk atau sesi habis"

app = FastAPI(title="edge-api (TPS)")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
akun.buat_akun_simulasi()
mulai_setor()  # penyetor bekerja di latar, terpisah dari pelayanan pemilih


@app.middleware("http")
async def hanya_json(request: Request, call_next):
    # cookie sesi ikut terkirim dari situs lain, tetapi situs lain tidak bisa mengirim
    # application/json tanpa preflight CORS. Jadi mewajibkan JSON cukup sebagai pelindung CSRF.
    jenis = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if request.method == "POST" and jenis != "application/json":
        return JSONResponse({"alasan": "Content-Type harus application/json"}, status_code=415)
    return await call_next(request)


class SuaraMasuk(BaseModel):
    pilihan: int
    pemilih_id: str = ""  # hanya untuk catatan penolakan; identitas pemilih diambil dari sesi
    asal: str = "bilik"  # "bilik" (halaman bilik suara) atau "voter-sim"
    lamport: int = 0


class Daftar(BaseModel):
    nim: str
    password: str


class Kode(BaseModel):
    nim: str
    kode: str = ""


class Masuk(BaseModel):
    nim: str
    password: str
    kode: str = ""


def token_dari(request):
    return request.cookies.get("sesi") or request.headers.get("X-Sesi")


def tolak(alasan, status=400):
    return JSONResponse({"alasan": alasan}, status_code=status)


@app.get("/")
def echo():
    # echo service dari Praktikum 1 tetap dipertahankan untuk ukur.py
    return {
        "host": socket.gethostname(),
        "waktu_unix": time.time(),
        "waktu_lokal": time.strftime("%H:%M:%S"),
    }


# ---------- halaman pemilih ----------

@app.get("/pemilih/daftar")
def halaman_daftar():
    return FileResponse(HALAMAN / "daftar.html")


@app.get("/pemilih/verifikasi")
def halaman_verifikasi():
    return FileResponse(HALAMAN / "verifikasi.html")


@app.get("/pemilih/masuk")
def halaman_masuk():
    return FileResponse(HALAMAN / "masuk.html")


@app.get("/bilik")
def bilik(request: Request):
    if not akun.nim_sesi(token_dari(request)):
        return RedirectResponse("/pemilih/masuk", status_code=303)
    return FileResponse(HALAMAN / "bilik.html")


@app.get("/pemilih/bukti")
def halaman_bukti(request: Request):
    if not akun.nim_sesi(token_dari(request)):
        return RedirectResponse("/pemilih/masuk", status_code=303)
    return FileResponse(HALAMAN / "bukti.html")


# ---------- API akun ----------

@app.post("/api/daftar")
def api_daftar(d: Daftar):
    nim = d.nim.strip().upper()
    alasan = akun.daftar(nim, d.password)
    return tolak(alasan) if alasan else {"nim": nim, "email": f"{nim}@untad.ac.id"}


@app.post("/api/verifikasi")
def api_verifikasi(k: Kode):
    alasan = akun.verifikasi(k.nim.strip().upper(), k.kode.strip())
    return tolak(alasan) if alasan else {"aktif": True}


@app.post("/api/kirim-ulang")
def api_kirim_ulang(k: Kode):
    alasan, kode_http = akun.kirim_ulang(k.nim.strip().upper())
    return tolak(alasan, kode_http) if alasan else {"terkirim": True}


@app.post("/api/masuk")
def api_masuk(m: Masuk):
    alasan, token, sudah = akun.masuk(m.nim.strip().upper(), m.password, m.kode.strip())
    if alasan:
        return tolak(alasan, 401)
    r = JSONResponse({"token": token, "sudah_memilih": sudah})
    r.set_cookie("sesi", token, max_age=akun.TTL_SESI, httponly=True, samesite="lax")
    return r


@app.post("/api/keluar")
def api_keluar(request: Request):
    akun.keluar(token_dari(request))
    r = JSONResponse({"keluar": True})
    r.delete_cookie("sesi")
    return r


@app.get("/api/saya")
def api_saya(request: Request):
    nim = akun.nim_sesi(token_dari(request))
    if not nim:
        return tolak(TANPA_SESI, 401)
    return {"nim": nim, "sudah_memilih": db.sudah_memilih(nim), "bukti": db.bukti_milik(nim)}


# ---------- endpoint Praktikum 5 ----------

@app.get("/daftar")
def daftar():
    return {"tps_id": TPS_ID, "kandidat": KANDIDAT, "jumlah_pemilih": akun.jumlah_aktif()}


@app.get("/status")
def status():
    return {"tps_id": TPS_ID, **pengumuman.status, **db.hitung(),
            "akun_terdaftar": akun.jumlah_aktif()}


def periksa(nim, s):
    # pemeriksaan lokal: dikerjakan di TPS, tanpa bertanya ke pusat rekap
    # [FITUR 1] suara hanya diterima selama pemungutan dibuka
    pemungutan = pengumuman.status["pemungutan"]
    # LENGKAPI: bila pemungutan bernilai "tutup", kembalikan "pemungutan sudah ditutup"
    if pemungutan == "tutup":
        return "pemungutan sudah ditutup"
    # LENGKAPI: bila pemungutan bukan "buka", kembalikan "pemungutan belum dibuka"
    if pemungutan != "buka":
        return "pemungutan belum dibuka"
    if nim is None:
        return TANPA_SESI
    alasan = periksa_nim(nim) or akun.alasan_tidak_boleh(nim)
    if alasan:
        return alasan
    if s.pilihan not in KANDIDAT:
        return "pilihan tidak sah"
    if db.sudah_memilih(nim):
        return "pemilih sudah memilih"
    return None


@app.post("/suara")
def terima_suara(s: SuaraMasuk, request: Request):
    nim = akun.nim_sesi(token_dari(request))
    pemilih = nim or s.pemilih_id
    if s.asal == "voter-sim":
        clock.terima(s.lamport, "terima", dari="voter-sim", pemilih_id=pemilih)
    else:
        clock.lokal("pilih-di-bilik", pemilih_id=pemilih)

    # periksa, simpan di TPS, lalu langsung jawab pemilih.
    # Penyetoran ke pusat rekap diurus setor.py, tidak ditunggu di sini.
    alasan = periksa(nim, s)
    seq = kode = None
    if alasan is None:
        hasil = db.simpan_lokal(nim, s.pilihan, TPS_ID)
        if hasil is None:
            alasan = "pemilih sudah memilih"
        else:
            seq, kode = hasil
            akun.tandai_terpakai(nim)  # kode pemilih hangus setelah memilih
    if alasan is None:
        clock.lokal("simpan", seq=seq)
    else:
        db.catat_tolak(pemilih, alasan)
        clock.lokal("tolak", alasan=alasan)

    balasan = {"diterima": alasan is None, "alasan": alasan, "seq": seq, "bukti": kode}
    if s.asal == "voter-sim":
        balasan["lamport"] = clock.kirim("balas", ke="voter-sim", seq=seq)
    return balasan


@app.get("/bukti/{kode}")
def cek_bukti(kode: str):
    # status lokal kode bukti di TPS: antre di TPS / terkirim / tidak ditemukan
    return {"bukti": kode, "status": db.status_bukti(kode)}
