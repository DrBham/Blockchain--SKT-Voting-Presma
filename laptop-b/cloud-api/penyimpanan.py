
import os
import random
import sqlite3
import threading
import time


DB_PATH = os.getenv("DB_PATH", "/data/pusat.db")
IDEMPOTEN = os.getenv("IDEMPOTEN", "1") == "1"
LAMBAT_PERSEN = int(os.getenv("LAMBAT_PERSEN", "0"))
LAMBAT_MS = int(os.getenv("LAMBAT_MS", "1500"))

# Jumlah pemilih di DPT Presma (lihat laptop-a/edge-api/daftar.py)
JUMLAH_PEMILIH = 150

_kunci = threading.Lock()

_db = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

_db.row_factory = sqlite3.Row

_db.execute("""
    CREATE TABLE IF NOT EXISTS suara (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        tps_id     TEXT,
        seq        INTEGER,
        pemilih_id TEXT,
        pilihan    INTEGER,
        waktu      INTEGER,
        bukti      TEXT,     -- kode bukti suara (aturan unik)
        block      INTEGER   -- nomor block di rantai, NULL bila belum ditambang
    )
""")

_db.execute("""
    CREATE TABLE IF NOT EXISTS pengaturan (
        kunci TEXT PRIMARY KEY,
        nilai TEXT
    )
""")

_db.commit()


def simpan(s):
    duplikat = False

    with _kunci:
        if IDEMPOTEN:
            sudah_ada = _db.execute(
                "SELECT 1 FROM suara WHERE request_id = ?",
                (s["request_id"],)
            ).fetchone()

            duplikat = sudah_ada is not None

        if not duplikat:
            _db.execute(
                """
                INSERT INTO suara (
                    request_id,
                    tps_id,
                    seq,
                    pemilih_id,
                    pilihan,
                    waktu,
                    bukti
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["request_id"],
                    s["tps_id"],
                    s["seq"],
                    s["pemilih_id"],
                    s["pilihan"],
                    s["waktu"],
                    s["bukti"]
                )
            )

            _db.commit()

    # Simulasi respons pusat yang terlambat.
    if random.randint(1, 100) <= LAMBAT_PERSEN:
        time.sleep(LAMBAT_MS / 1000)

    return {
        "tersimpan": not duplikat,
        "duplikat": duplikat
    }


def catatan(per_kandidat, pemilih):
    # FITUR 3: Catatan partisipasi Paket C
    # Jumlah pemilih terdaftar = 150

    if not per_kandidat:
        return "Belum ada suara."

    persentase = (
        pemilih / JUMLAH_PEMILIH
    ) * 100

    return (
        f"Partisipasi: {pemilih} dari "
        f"{JUMLAH_PEMILIH} pemilih "
        f"({persentase:.1f}%)."
    )


def rekap():
    with _kunci:
        total, kiriman, pemilih = _db.execute(
            """
            SELECT
                COUNT(*),
                COUNT(DISTINCT request_id),
                COUNT(DISTINCT pemilih_id)
            FROM suara
            """
        ).fetchone()

        per_kandidat = _db.execute(
            """
            SELECT pilihan, COUNT(*)
            FROM suara
            GROUP BY pilihan
            ORDER BY pilihan
            """
        ).fetchall()

        per_tps = _db.execute(
            """
            SELECT tps_id, COUNT(*)
            FROM suara
            GROUP BY tps_id
            ORDER BY tps_id
            """
        ).fetchall()

    return {
        "total_suara": total,
        "kiriman_ganda": total - kiriman,
        "pemilih_ganda": kiriman - pemilih,
        "per_kandidat": {
            str(k): n
            for k, n in per_kandidat
        },
        "per_tps": {
            t: n
            for t, n in per_tps
        },
        "catatan": catatan(
            {k: n for k, n in per_kandidat},
            pemilih
        )
    }


def ambil(terakhir=10):
    with _kunci:
        baris = _db.execute(
            """
            SELECT *
            FROM suara
            ORDER BY id DESC
            LIMIT ?
            """,
            (terakhir,)
        ).fetchall()

    return [dict(b) for b in baris]


def status():
    with _kunci:
        baris = _db.execute(
            """
            SELECT nilai
            FROM pengaturan
            WHERE kunci = 'pemungutan'
            """
        ).fetchone()

    return (
        baris["nilai"]
        if baris
        else "belum dibuka"
    )


def ubah_status(nilai):
    with _kunci:
        _db.execute(
            """
            INSERT OR REPLACE INTO pengaturan
            VALUES ('pemungutan', ?)
            """,
            (nilai,)
        )

        _db.commit()


def tandai_block(daftar_bukti, index):
    with _kunci:
        _db.executemany("UPDATE suara SET block = ? WHERE bukti = ?",
                        [(index, kode) for kode in daftar_bukti])
        _db.commit()


def semua_suara():
    # dipakai saat start untuk mencocokkan isi SQLite dengan rantai
    with _kunci:
        baris = _db.execute("SELECT * FROM suara ORDER BY id").fetchall()
    return [dict(b) for b in baris]
