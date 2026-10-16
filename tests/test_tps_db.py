import os
import sys

from conftest import EDGE


def test_simpan_dan_status_bukti(tmp_path):
    os.environ["TPS_DB"] = str(tmp_path / "tps.db")
    sys.path.insert(0, str(EDGE))
    sys.modules.pop("tps_db", None)
    import tps_db

    seq, kode = tps_db.simpan_lokal("F55125001", 1, "tps-ft")
    assert seq == 1 and tps_db.status_bukti(kode) == "antre di TPS"
    assert tps_db.ambil_antre()[0]["bukti"] == kode
    tps_db.tandai_terkirim(tps_db.ambil_antre()[0]["request_id"])
    assert tps_db.status_bukti(kode) == "terkirim"
    assert tps_db.simpan_lokal("F55125001", 2, "tps-ft") is None
    assert tps_db.status_bukti("0" * 16) == "tidak ditemukan"
