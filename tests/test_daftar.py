import sys

from conftest import EDGE

sys.path.insert(0, str(EDGE))
from daftar import KANDIDAT, PEMILIH  # noqa: E402
from nim import periksa_nim  # noqa: E402


def test_daftar_presma():
    assert KANDIDAT == {1: "Paslon 1", 2: "Paslon 2"}
    assert len(PEMILIH) == 150
    assert {"F55119001", "A12125010", "C30122005"} <= PEMILIH and "F55125011" not in PEMILIH


def test_periksa_nim():
    assert periksa_nim("F55119001") is None  # angkatan lama tetap boleh memilih
    assert periksa_nim("Z55125001") == "Kode Fakultas 'Z' tidak terdaftar di UNTAD!"
    assert periksa_nim("f55125001") and periksa_nim("XX001")  # format salah -> ada alasan
