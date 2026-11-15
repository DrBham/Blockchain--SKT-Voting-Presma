import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

from conftest import EDGE

NIM = "F55124111"
PW = "rahasia-panjang"


def muat_edge(folder):
    os.environ.update(TPS_DB=str(folder / "tps.db"), LOG_DIR=str(folder), CLOUD_HOST="127.0.0.1",
                      SERVICE="edge-api", MAIL_HOST="", SIM_PASSWORD="sim-rahasia", SIM_KODE="654321",
                      SETOR_TIAP_S="60")
    sys.path.insert(0, str(EDGE))
    for nama in ("app", "akun", "tps_db", "setor", "kirim", "lamport", "pengumuman", "bukti", "nim", "daftar"):
        sys.modules.pop(nama, None)
    return importlib.import_module("app")


@pytest.fixture
def edge(tmp_path, monkeypatch):
    app = muat_edge(tmp_path)
    surat = {}
    # kode yang "dikirim lewat email" ditangkap di sini
    monkeypatch.setattr(app.akun, "kirim_kode", lambda nim, kode: surat.__setitem__(nim, kode))
    app.pengumuman.status["pemungutan"] = "buka"
    return TestClient(app.app), app, surat


def daftar_aktif(c, surat, nim=NIM):
    assert c.post("/api/daftar", json={"nim": nim, "password": PW}).status_code == 200
    assert c.post("/api/verifikasi", json={"nim": nim, "kode": surat[nim]}).status_code == 200
    return surat[nim]


def test_akun_simulasi_dibuat_dan_bisa_masuk(edge):
    c, app, _ = edge
    assert app.akun.jumlah_aktif() == 150
    assert c.get("/status").json()["akun_terdaftar"] == 150
    r = c.post("/api/masuk", json={"nim": "F55119001", "password": "sim-rahasia", "kode": "654321"})
    assert r.status_code == 200 and r.json()["token"]


def test_hash_bukan_teks_asli(edge):
    c, app, surat = edge
    kode = daftar_aktif(c, surat)
    baris = app.db._db.execute("SELECT * FROM akun WHERE nim = ?", (NIM,)).fetchone()
    assert PW not in baris["password_hash"] and kode not in baris["kode_hash"]
    assert baris["password_hash"].startswith("scrypt$")


def test_daftar_menolak_nim_dan_password_buruk(edge):
    c, _, _ = edge
    r = c.post("/api/daftar", json={"nim": "Z55125001", "password": PW})
    assert r.status_code == 400 and "Kode Fakultas 'Z'" in r.json()["alasan"]
    assert c.post("/api/daftar", json={"nim": NIM, "password": "pendek"}).status_code == 400


def test_masuk_menolak_format_nim_dan_akun_belum_ada(edge):
    c, _, _ = edge
    r = c.post("/api/masuk", json={"nim": "XX013", "password": PW, "kode": "123456"})
    assert r.status_code == 401 and r.json()["alasan"].startswith("format NIM salah")
    r = c.post("/api/masuk", json={"nim": "F55125099", "password": PW, "kode": "123456"})
    assert r.json()["alasan"] == "NIM atau password salah"


def test_lima_kode_salah_menghanguskan(edge):
    c, _, surat = edge
    c.post("/api/daftar", json={"nim": NIM, "password": PW})
    for _ in range(5):
        assert c.post("/api/verifikasi", json={"nim": NIM, "kode": "000000"}).status_code == 400
    r = c.post("/api/verifikasi", json={"nim": NIM, "kode": surat[NIM]})
    assert r.status_code == 400 and "hangus" in r.json()["alasan"]


def test_kirim_ulang_menunggu_60_detik(edge):
    c, app, surat = edge
    c.post("/api/daftar", json={"nim": NIM, "password": PW})
    lama = surat[NIM]
    r = c.post("/api/kirim-ulang", json={"nim": NIM})
    assert r.status_code == 429 and "Tunggu" in r.json()["alasan"]
    app.db._db.execute("UPDATE akun SET kode_dikirim = kode_dikirim - 61")
    assert c.post("/api/kirim-ulang", json={"nim": NIM}).status_code == 200
    if surat[NIM] != lama:  # kode lama hangus begitu kode baru dikirim
        assert c.post("/api/verifikasi", json={"nim": NIM, "kode": lama}).status_code == 400


def test_akun_belum_aktif_dikunci_15_menit(edge):
    c, app, _ = edge
    c.post("/api/daftar", json={"nim": NIM, "password": PW})
    r = c.post("/api/daftar", json={"nim": NIM, "password": "password-penyerobot"})
    assert r.status_code == 400 and "menunggu verifikasi" in r.json()["alasan"]
    app.db._db.execute("UPDATE akun SET kode_dikirim = kode_dikirim - 15 * 60 - 1")
    assert c.post("/api/daftar", json={"nim": NIM, "password": "password-penyerobot"}).status_code == 200


def test_suara_tanpa_sesi_ditolak(edge):
    c, _, _ = edge
    r = c.post("/suara", json={"pemilih_id": "F55119001", "pilihan": 1})
    assert r.status_code == 200 and r.json()["diterima"] is False
    assert r.json()["alasan"] == "belum masuk atau sesi habis"
    assert c.get("/status").json()["ditolak"] == 1


def test_suara_memakai_nim_sesi_dan_kode_hangus(edge):
    c, app, surat = edge
    kode = daftar_aktif(c, surat)
    token = c.post("/api/masuk", json={"nim": NIM, "password": PW, "kode": kode}).json()["token"]
    # pemilih_id di badan diabaikan: identitas dari sesi
    r = c.post("/suara", json={"pemilih_id": "F55119001", "pilihan": 2}, headers={"X-Sesi": token})
    assert r.json()["diterima"] is True
    assert app.db.sudah_memilih(NIM) and not app.db.sudah_memilih("F55119001")
    assert c.post("/api/masuk", json={"nim": NIM, "password": PW, "kode": kode}).json()["sudah_memilih"]
    r = c.post("/suara", json={"pilihan": 1}, headers={"X-Sesi": token})
    assert r.json()["alasan"] == "pemilih sudah memilih"


def test_masuk_memasang_cookie_dan_bilik_butuh_sesi(edge):
    c, _, surat = edge
    assert c.get("/bilik", follow_redirects=False).headers["location"] == "/pemilih/masuk"
    kode = daftar_aktif(c, surat)
    r = c.post("/api/masuk", json={"nim": NIM, "password": PW, "kode": kode})
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()
    assert c.get("/bilik", follow_redirects=False).status_code == 200
    assert c.post("/suara", json={"pilihan": 1}).json()["diterima"] is True  # lewat cookie


def test_sesi_kedaluwarsa_ditolak(edge):
    c, app, surat = edge
    kode = daftar_aktif(c, surat)
    token = c.post("/api/masuk", json={"nim": NIM, "password": PW, "kode": kode}).json()["token"]
    app.akun._sesi[token] = (NIM, 0)  # habis
    r = c.post("/suara", json={"pilihan": 1}, headers={"X-Sesi": token})
    assert r.json()["alasan"] == "belum masuk atau sesi habis"


def test_post_tanpa_json_ditolak(edge):
    c, _, _ = edge
    r = c.post("/api/daftar", content=b'{"nim": "F55124111", "password": "rahasia-panjang"}')
    assert r.status_code == 415


def test_setor_membawa_terdaftar(edge, monkeypatch):
    _, app, _ = edge
    import setor

    terkirim = []
    monkeypatch.setattr(setor, "kirim_rest", lambda p: terkirim.append(dict(p)) or {"terkirim": True})
    app.db.simpan_lokal("F55119001", 1, "tps-ft")
    setor.setor_sekali()
    assert terkirim[0]["terdaftar"] == 150 and terkirim[0]["pemilih_id"] == "F55119001"
