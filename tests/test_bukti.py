import importlib.util

from conftest import CLOUD, EDGE


def muat(folder):
    spec = importlib.util.spec_from_file_location(f"bukti_{folder.name}", folder / "bukti.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


P = {"request_id": "r1", "tps_id": "tps-ft", "seq": 1, "pemilih_id": "F55125001", "pilihan": 1, "waktu": 1}


def test_hitung_stabil_dan_sensitif():
    b = muat(EDGE)
    assert b.hitung(P) == b.hitung(dict(reversed(P.items())))
    assert len(b.hitung(P)) == 16 and b.hitung(P) != b.hitung({**P, "pilihan": 2})
    assert b.hitung({**P, "lamport": 9, "bukti": "x"}) == b.hitung(P)  # hanya enam field


def test_rapikan():
    b = muat(EDGE)
    k = b.hitung(P)
    assert b.rapikan(f"  {k.upper()} ") == k
    assert b.rapikan(f"{k[:4]} {k[4:8]}-{k[8:]}") == k  # diketik dengan spasi/strip
    assert b.rapikan("abc") is None and b.rapikan("z" * 16) is None


def test_kedua_laptop_sama():
    assert (EDGE / "bukti.py").read_text() == (CLOUD / "bukti.py").read_text()
