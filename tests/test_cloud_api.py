import importlib
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

from conftest import CLOUD

H = {"X-TPS-Token": "t"}


def buat_suara(n=1, pemilih="F55125001"):
    sys.path.insert(0, str(CLOUD))
    import bukti

    s = {"request_id": f"r{n}", "tps_id": "tps-ft", "seq": n, "pemilih_id": pemilih,
         "pilihan": 1, "waktu": 1000 + n}
    return {**s, "bukti": bukti.hitung(s)}


def muat_app(folder):
    os.environ.update(DB_PATH=str(folder / "pusat.db"), RANTAI_PATH=str(folder / "rantai.json"),
                      LOG_DIR=str(folder), TPS_TOKEN="t", DIFFICULTY="1", TAMBANG_TIAP_S="0.1",
                      MQTT_HOST="127.0.0.1", SERVICE="cloud-api")
    sys.path.insert(0, str(CLOUD))
    for nama in ("app", "penyimpanan", "lamport", "pengumuman", "rantai", "bukti"):
        sys.modules.pop(nama, None)
    return importlib.import_module("app")


def tunggu(cek, batas=5):
    akhir = time.time() + batas
    while time.time() < akhir:
        if cek():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def klien(tmp_path):
    app = muat_app(tmp_path)
    yield TestClient(app.app), app, tmp_path
    app.berhenti.set()


def status(c, kode):
    return c.get(f"/bukti/{kode}").json()["status"]


def test_tanpa_token_401_walau_tanpa_bukti(klien):
    c, _, _ = klien
    palsu = {k: v for k, v in buat_suara().items() if k != "bukti"}  # seperti tps_gadungan.py
    assert c.post("/suara", json=palsu).status_code == 401


def test_bukti_salah_422(klien):
    c, _, _ = klien
    assert c.post("/suara", json={**buat_suara(), "bukti": "0" * 16}, headers=H).status_code == 422


def test_alur_bukti_sampai_block(klien):
    c, app, _ = klien
    s = buat_suara()
    assert status(c, s["bukti"]) == "belum diterima pusat rekap"
    app.berhenti.set()  # tahan penambang agar status pool terlihat
    assert c.post("/suara", json=s, headers=H).status_code == 201
    assert status(c, s["bukti"]) == "diterima, menunggu ditambang"
    app.mulai_penambang()
    assert tunggu(lambda: status(c, s["bukti"]) == "tercatat di block 1")
    assert c.get("/rantai/validasi").json()["valid"] is True
    assert c.get("/rantai").json()["panjang"] == 2


def test_kirim_ulang_tidak_dobel(klien):
    c, app, _ = klien
    s = buat_suara()
    c.post("/suara", json=s, headers=H)
    c.post("/suara", json=s, headers=H)  # balasan pertama hilang, TPS kirim ulang
    assert tunggu(lambda: status(c, s["bukti"]).startswith("tercatat"))
    assert sum(len(b["transaksi"]) for b in app.rantai.chain) == 1
    assert c.get("/rekap").json()["kiriman_ganda"] == 0


def test_pool_selamat_saat_restart(tmp_path):
    app = muat_app(tmp_path)
    app.berhenti.set()
    s = buat_suara()
    assert TestClient(app.app).post("/suara", json=s, headers=H).status_code == 201
    app2 = muat_app(tmp_path)  # container cloud-api di-restart sebelum suara ditambang
    c2 = TestClient(app2.app)
    assert tunggu(lambda: status(c2, s["bukti"]) == "tercatat di block 1")
    app2.berhenti.set()


def test_bukti_input_aneh(klien):
    c, _, _ = klien
    assert status(c, "%20ABC") == "tidak ditemukan"
    assert status(c, "z" * 16) == "tidak ditemukan"
