# Akun pemilih di TPS: daftar -> verifikasi email -> masuk (sesi 15 menit).
# Password dan kode pemilih hanya disimpan sebagai hash scrypt.
import hashlib
import hmac
import logging
import math
import os
import secrets
import smtplib
import threading
import time
from email.message import EmailMessage

import tps_db as db
from nim import NIM_SIMULASI, periksa_nim

BATAS_SALAH = 5
JEDA_KIRIM_ULANG = 60
MASA_TUNGGU_VERIFIKASI = 15 * 60  # akun belum aktif tidak bisa didaftar ulang orang lain selama ini
TTL_SESI = 15 * 60
MAIL_HOST = os.getenv("MAIL_HOST", "")
MAIL_PORT = int(os.getenv("MAIL_PORT", "1025"))
MAIL_FROM = os.getenv("MAIL_FROM", "pemira@tps.local")
SIM_PASSWORD = os.getenv("SIM_PASSWORD", "pemilih-simulasi")
SIM_KODE = os.getenv("SIM_KODE", "123456")
log = logging.getLogger("uvicorn.error")

with db._kunci:
    db._db.execute("""
        CREATE TABLE IF NOT EXISTS akun (
            nim           TEXT PRIMARY KEY,
            password_hash TEXT,
            kode_hash     TEXT,
            terverifikasi INTEGER DEFAULT 0,
            kode_terpakai INTEGER DEFAULT 0,  -- 1 setelah suara diterima: kode hangus
            salah_kode    INTEGER DEFAULT 0,
            kode_dikirim  REAL,               -- detik unix kode terakhir dikirim
            simulasi      INTEGER DEFAULT 0
        )""")
    db._db.commit()

_sesi = {}  # token -> (nim, habis pada time.monotonic())
_kunci_sesi = threading.Lock()


def buat_hash(teks):
    garam = secrets.token_bytes(16)
    h = hashlib.scrypt(teks.encode(), salt=garam, n=2 ** 14, r=8, p=1)
    return f"scrypt${garam.hex()}${h.hex()}"


def cocok(teks, simpanan):
    if not simpanan:
        return False
    _, garam, h = simpanan.split("$")
    uji = hashlib.scrypt(teks.encode(), salt=bytes.fromhex(garam), n=2 ** 14, r=8, p=1)
    return hmac.compare_digest(uji.hex(), h)


def _ambil(nim):
    with db._kunci:
        return db._db.execute("SELECT * FROM akun WHERE nim = ?", (nim,)).fetchone()


def _ubah(nim, **kolom):
    isi = ", ".join(f"{k} = ?" for k in kolom)
    with db._kunci:
        db._db.execute(f"UPDATE akun SET {isi} WHERE nim = ?", (*kolom.values(), nim))
        db._db.commit()


def kirim_kode(nim, kode):
    """Kirim kode ke NIM@untad.ac.id. Bila SMTP tidak ada atau gagal, kode dicetak di log."""
    email = f"{nim}@untad.ac.id"
    pesan = EmailMessage()
    pesan["Subject"] = "Kode pemilih Pemira Presma"
    pesan["From"] = MAIL_FROM
    pesan["To"] = email
    pesan.set_content(f"Kode pemilihmu: {kode}\n\nKode ini mengaktifkan akun dan dipakai lagi saat "
                      "masuk ke bilik suara. Jangan bagikan ke siapa pun.\n")
    if MAIL_HOST:
        try:
            with smtplib.SMTP(MAIL_HOST, MAIL_PORT, timeout=5) as smtp:
                smtp.send_message(pesan)
            return
        except (OSError, smtplib.SMTPException) as e:
            log.warning("email gagal dikirim lewat %s:%s (%s)", MAIL_HOST, MAIL_PORT, e)
    log.warning("KODE PEMILIH untuk %s: %s", email, kode)


def _kode_baru(nim):
    # kode baru menggantikan yang lama, jadi kode lama langsung hangus
    kode = f"{secrets.randbelow(10 ** 6):06d}"
    _ubah(nim, kode_hash=buat_hash(kode), kode_dikirim=time.time(), salah_kode=0)
    kirim_kode(nim, kode)


def _sisa_jeda(a):
    return max(0, math.ceil(JEDA_KIRIM_ULANG - (time.time() - (a["kode_dikirim"] or 0))))


def _cek_kode(a, kode):
    """None bila kode benar, selain itu alasan. Salah ke-5 menghanguskan kode."""
    if a["salah_kode"] >= BATAS_SALAH:
        return "Kode sudah hangus karena 5 kali salah. Kirim ulang kode baru"
    if len(kode) == 6 and cocok(kode, a["kode_hash"]):
        return None
    salah = a["salah_kode"] + 1
    _ubah(a["nim"], salah_kode=salah)
    sisa = BATAS_SALAH - salah
    return f"Kode salah. Sisa {sisa} percobaan" if sisa else \
        "Kode salah 5 kali dan sudah hangus. Kirim ulang kode baru"


def daftar(nim, password):
    """None bila akun dibuat dan kode dikirim, selain itu alasan penolakan."""
    alasan = periksa_nim(nim)
    if alasan:
        return alasan
    if len(password) < 8:
        return "Password minimal 8 karakter"
    a = _ambil(nim)
    if a and a["terverifikasi"]:
        return "NIM ini sudah punya akun. Silakan masuk"
    if a and time.time() - (a["kode_dikirim"] or 0) < MASA_TUNGGU_VERIFIKASI:
        return "NIM ini sedang menunggu verifikasi. Cek email kampus, atau coba lagi setelah 15 menit"
    with db._kunci:
        db._db.execute("INSERT OR REPLACE INTO akun (nim, password_hash) VALUES (?, ?)",
                       (nim, buat_hash(password)))
        db._db.commit()
    _kode_baru(nim)
    return None


def verifikasi(nim, kode):
    a = _ambil(nim)
    if a is None:
        return "NIM ini belum mendaftar"
    if a["terverifikasi"]:
        return None
    alasan = _cek_kode(a, kode)
    if alasan is None:
        _ubah(nim, terverifikasi=1, salah_kode=0)
    return alasan


def kirim_ulang(nim):
    """(alasan, kode status HTTP). Alasan None berarti kode baru terkirim."""
    a = _ambil(nim)
    if a is None:
        return "NIM ini belum mendaftar", 400
    if a["kode_terpakai"]:
        return "NIM ini sudah memilih. Kode tidak dikirim lagi", 400
    sisa = _sisa_jeda(a)
    if sisa:
        return f"Tunggu {sisa} detik sebelum kirim ulang", 429
    _kode_baru(nim)
    return None, 200


def masuk(nim, password, kode):
    """(alasan, token, sudah_memilih). Pemilih yang sudah memilih tetap boleh masuk untuk melihat bukti."""
    alasan = periksa_nim(nim)
    if alasan:
        return alasan, None, False
    a = _ambil(nim)
    if a is None or not cocok(password, a["password_hash"]):
        return "NIM atau password salah", None, False
    if not a["terverifikasi"]:
        return "Akun belum aktif. Masukkan kode dari email pendaftaran", None, False
    if not a["kode_terpakai"]:
        alasan = _cek_kode(a, kode)
        if alasan:
            return alasan, None, False
        if a["salah_kode"]:
            _ubah(nim, salah_kode=0)
    token = secrets.token_urlsafe(32)
    with _kunci_sesi:
        sekarang = time.monotonic()
        for t in [t for t, (_, habis) in _sesi.items() if habis <= sekarang]:
            del _sesi[t]
        _sesi[token] = (nim, sekarang + TTL_SESI)
    return None, token, bool(a["kode_terpakai"])


def nim_sesi(token):
    """NIM pemilik token, atau None bila tidak ada atau sudah habis."""
    with _kunci_sesi:
        isi = _sesi.get(token or "")
    return isi[0] if isi and isi[1] > time.monotonic() else None


def keluar(token):
    with _kunci_sesi:
        _sesi.pop(token or "", None)


def alasan_tidak_boleh(nim):
    a = _ambil(nim)
    if a is None or not a["terverifikasi"]:
        return "akun belum aktif"
    if a["kode_terpakai"]:
        return "pemilih sudah memilih"
    return None


def tandai_terpakai(nim):
    _ubah(nim, kode_terpakai=1)


def jumlah_aktif():
    with db._kunci:
        return db._db.execute("SELECT COUNT(*) FROM akun WHERE terverifikasi = 1").fetchone()[0]


def buat_akun_simulasi():
    # shortcut: satu hash dipakai bersama oleh 150 akun simulasi (password dan kode sama),
    # supaya start tidak menunggu 300 kali scrypt. Akun nyata selalu punya garam sendiri.
    pw, kode = buat_hash(SIM_PASSWORD), buat_hash(SIM_KODE)
    with db._kunci:
        db._db.executemany(
            "INSERT OR IGNORE INTO akun (nim, password_hash, kode_hash, terverifikasi, simulasi)"
            " VALUES (?, ?, ?, 1, 1)", [(n, pw, kode) for n in NIM_SIMULASI])
        db._db.commit()
