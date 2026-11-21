import json
import sys

from conftest import CLOUD

sys.path.insert(0, str(CLOUD))
from rantai import Rantai  # noqa: E402

TX = {"request_id": "r1", "tps_id": "tps-ft", "seq": 1, "pemilih_id": "F55125001",
      "pilihan": 1, "waktu": 1, "bukti": "a" * 16}


def test_tambang_dan_cari(tmp_path):
    r = Rantai(str(tmp_path / "c.json"), 2)
    assert r.tambah_pool(TX) and not r.tambah_pool(TX)
    assert r.di_pool(TX["bukti"])
    b = r.tambang()
    assert b["index"] == 1 and b["hash"].startswith("00") and r.cari(TX["bukti"]) == 1
    assert not r.di_pool(TX["bukti"])
    assert not r.tambah_pool(TX) and r.tambang() is None
    assert r.ringkas()["panjang"] == 2 and r.ringkas()["pool"] == 0


def test_persisten(tmp_path):
    p = str(tmp_path / "c.json")
    r = Rantai(p, 2)
    r.tambah_pool(TX)
    r.tambang()
    r2 = Rantai(p, 2)
    assert r2.cari(TX["bukti"]) == 1 and r2.validasi() == (True, None, "rantai valid")


def test_validasi_deteksi_ubah(tmp_path):
    p = tmp_path / "c.json"
    r = Rantai(str(p), 2)
    for i in (1, 2):
        r.tambah_pool({**TX, "request_id": f"r{i}", "bukti": str(i) * 16})
        r.tambang()
    data = json.loads(p.read_text())
    data[1]["transaksi"][0]["pilihan"] = 2  # ubah suara di block lama
    p.write_text(json.dumps(data))
    ok, rusak, alasan = Rantai(str(p), 2).validasi()
    assert (ok, rusak) == (False, 1) and "hash" in alasan


def test_file_rusak_dilaporkan_dan_disimpan(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{bukan json")
    r = Rantai(str(p), 2)
    assert r.ringkas()["panjang"] == 1
    assert r.validasi()[:2] == (False, 0) and "rusak" in r.validasi()[2]
    assert (tmp_path / "c.json.rusak").read_text() == "{bukan json"
    r.tambah_pool(TX)
    r.tambang()  # block baru tidak menghapus laporan kerusakan
    assert Rantai(str(p), 2).validasi()[0] is False


def test_isi_aneh_tidak_crash(tmp_path):
    p = tmp_path / "c.json"
    r = Rantai(str(p), 2)
    r.tambah_pool(TX)
    r.tambang()
    data = json.loads(p.read_text())
    data[1]["transaksi"] = 5
    data[1]["hash"] = 123
    p.write_text(json.dumps(data))
    r2 = Rantai(str(p), 2)
    assert r2.validasi()[:2] == (False, 1) and r2.ringkas()["terakhir"] == "123"


def test_simpan_gagal_tidak_mengubah_memori(tmp_path, monkeypatch):
    r = Rantai(str(tmp_path / "c.json"), 2)
    r.tambah_pool(TX)
    monkeypatch.setattr(r, "_simpan", lambda chain: (_ for _ in ()).throw(OSError("disk penuh")))
    try:
        r.tambang()
    except OSError:
        pass
    assert len(r.chain) == 1 and r.di_pool(TX["bukti"]) and r.cari(TX["bukti"]) is None


def test_block_tanpa_field_tidak_crash(tmp_path):
    p = tmp_path / "c.json"
    r = Rantai(str(p), 2)
    r.tambah_pool(TX)
    r.tambang()
    data = json.loads(p.read_text())
    del data[1]["transaksi"]
    p.write_text(json.dumps(data))
    assert Rantai(str(p), 2).validasi()[:2] == (False, 1)
