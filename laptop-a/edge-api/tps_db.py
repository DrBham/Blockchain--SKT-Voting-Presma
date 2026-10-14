import os
import sqlite3
import threading
import time
import uuid

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
        status     TEXT          -- 'antre' atau 'terkirim'
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


def simpan_lokal(pemilih_id, pilihan):
    # suara disimpan di TPS lebih dulu, dengan status 'antre'
    with _kunci:
        try:
            cur = _db.execute(
                "INSERT INTO suara (request_id, pemilih_id, pilihan, waktu, status)"
                " VALUES (?, ?, ?, ?, 'antre')",
                (str(uuid.uuid4()), pemilih_id, pilihan, int(time.time() * 1000)))
            _db.commit()
            return cur.lastrowid  # nomor urut suara di TPS ini
        except sqlite3.IntegrityError:
            return None  # pemilih_id sudah ada: pemilih ini sudah memilih


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
