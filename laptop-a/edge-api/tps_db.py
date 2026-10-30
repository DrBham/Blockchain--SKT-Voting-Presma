import os
import sqlite3
import threading
import time
import uuid

import bukti

DB_PATH = os.getenv("TPS_DB", "/data/tps.db")

_kunci = threading.Lock()
_db = sqlite3.connect(DB_PATH, check_same_thread=False)
_db.row_factory = sqlite3.Row
_db.execute("""
    CREATE TABLE IF NOT EXISTS suara (
        seq        INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        pemilih_id TEXT UNIQUE,  -- satu pemilih hanya boleh punya satu baris
        pilihan    INTEGER,
        waktu      INTEGER,
        status     TEXT,         -- 'antre' atau 'terkirim'
        bukti      TEXT          -- kode bukti suara untuk pemilih
    )""")
_db.execute("""
    CREATE TABLE IF NOT EXISTS tolak (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        pemilih_id TEXT,
        alasan     TEXT,
        waktu      INTEGER
    )""")


def sudah_memilih(pemilih_id):
    with _kunci:
        return _db.execute("SELECT 1 FROM suara WHERE pemilih_id = ?",
                           (pemilih_id,)).fetchone() is not None


def simpan_lokal(pemilih_id, pilihan, tps_id):
    # suara disimpan di TPS lebih dulu, dengan status 'antre'.
    # Mengembalikan (seq, kode bukti), atau None bila pemilih sudah memilih.
    pesan = {"request_id": str(uuid.uuid4()), "tps_id": tps_id, "pemilih_id": pemilih_id,
             "pilihan": pilihan, "waktu": int(time.time() * 1000)}
    with _kunci:
        try:
            cur = _db.execute(
                "INSERT INTO suara (request_id, pemilih_id, pilihan, waktu, status)"
                " VALUES (?, ?, ?, ?, 'antre')",
                (pesan["request_id"], pemilih_id, pilihan, pesan["waktu"]))
        except sqlite3.IntegrityError:
            return None  # pemilih_id sudah ada: pemilih ini sudah memilih
        seq = cur.lastrowid  # nomor urut suara di TPS ini
        kode = bukti.hitung({**pesan, "seq": seq})
        _db.execute("UPDATE suara SET bukti = ? WHERE seq = ?", (kode, seq))
        _db.commit()
        return seq, kode


def status_bukti(kode):
    kode = bukti.rapikan(kode)
    with _kunci:
        baris = _db.execute("SELECT status FROM suara WHERE bukti = ?", (kode,)).fetchone()
    if baris is None:
        return "tidak ditemukan"
    return "antre di TPS" if baris["status"] == "antre" else "terkirim"


def bukti_milik(pemilih_id):
    with _kunci:
        baris = _db.execute("SELECT bukti FROM suara WHERE pemilih_id = ?", (pemilih_id,)).fetchone()
    return baris["bukti"] if baris else None


def catat_tolak(pemilih_id, alasan):
    with _kunci:
        _db.execute("INSERT INTO tolak (pemilih_id, alasan, waktu) VALUES (?, ?, ?)",
                    (pemilih_id, alasan, int(time.time() * 1000)))
        _db.commit()


def ambil_antre(maks=20):
    # suara yang belum disetor, dari yang paling lama
    with _kunci:
        baris = _db.execute(
            "SELECT * FROM suara WHERE status = 'antre' ORDER BY seq LIMIT ?",
            (maks,)).fetchall()
    return [dict(b) for b in baris]


def tandai_terkirim(request_id):
    with _kunci:
        _db.execute("UPDATE suara SET status = 'terkirim' WHERE request_id = ?",
                    (request_id,))
        _db.commit()


def hitung():
    with _kunci:
        diterima, antre = _db.execute(
            "SELECT COUNT(*), COALESCE(SUM(status = 'antre'), 0) FROM suara").fetchone()
        ditolak = _db.execute("SELECT COUNT(*) FROM tolak").fetchone()[0]
    return {"masuk": diterima + ditolak, "diterima": diterima, "ditolak": ditolak,
            "antre": antre, "terkirim": diterima - antre}
