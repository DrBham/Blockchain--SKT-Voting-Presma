# SKT Presma Blockchain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the group's finished Praktikum 5 voting system into a Presma UNTAD voting app whose central tally (Laptop B) records every vote in a proof-of-work hash chain and gives each voter a checkable vote receipt (kode bukti).

**Architecture:** Copy `skt-voting` (Praktikum 5, group version) into a new repo and keep its services, files, ports, endpoints, and log format. Add a shared `bukti.py` (receipt hash) to both laptops, a stdlib `rantai.py` (blocks, PoW, validation, JSON persistence) plus a background miner to `cloud-api`, and receipt lookups on both sides.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, httpx, paho-mqtt (as in Praktikum 5), SQLite, Docker Compose, Mosquitto. Blockchain code uses only `hashlib`/`json`.

**Spec:** `docs/superpowers/specs/2026-11-26-skt-presma-blockchain-design.md`

## Global Constraints

- New folder `E:\Kuliah\Semester 5\Sistem Komputasi Terdistribusi\skt-presma-blockchain\`, its own git repo. Never touch `E:\Kuliah\Semester 5\Block Chain\Project Base 1` or `skt-voting`.
- Keep Praktikum 5 file names, ports (8080, 9090, 1883), endpoints, `lamport.py`, and log format so `uji_urutan.py`, `ukur_voting.py`, `tps_gadungan.py` run unchanged.
- Candidates exactly `{1: "Paslon 1", 2: "Paslon 2"}`; no candidate names anywhere.
- DPT (150): `{f"{fak}{prodi}{th}{n:03d}" for fak, prodi in (("A", "121"), ("C", "301"), ("F", "551")) for th in ("19", "22", "23", "24", "25") for n in range(1, 11)}`, `JUMLAH_PEMILIH = 150`. `TPS_ID=tps-ft`.
- Voter check order (rules from the Blockchain project, no intake-year limit): NIM format `[A-Z]\d{7,8}` → faculty code in `ABCDEFGKLNP` (`Kode Fakultas 'X' tidak terdaftar di UNTAD!`) → in DPT (`pemilih tidak terdaftar`) → not voted yet.
- Kode bukti = first 16 hex chars of SHA-256 over `json.dumps({request_id, tps_id, seq, pemilih_id, pilihan, waktu}, sort_keys=True)`.
- Receipt statuses on Laptop B: `belum diterima pusat rekap`, `diterima, menunggu ditambang`, `tercatat di block N`; unknown code → `tidak ditemukan`. Laptop A: `antre di TPS`, `terkirim`, `tidak ditemukan`. Board never shows the chosen candidate for a code.
- `.env` (Laptop B) adds `DIFFICULTY=3`, `TAMBANG_TIAP_S=3`. Chain file `/data/rantai.json`.
- `.env` is git-ignored; commit `.env.example` with `TPS_TOKEN=ganti-dengan-token-kelompok`.
- Compose project names `presma-a` / `presma-b` (not `voting-a/b`) so old Praktikum volumes are not reused.
- Mining runs in a background thread; PoW never runs inside `POST /suara`.

## Review Focus

- `tps_gadungan.py` posts without `bukti`: must still get **401** (token is checked before receipt), not a 422 validation error. → Task 4 test.
- The same vote resent (same `request_id`, e.g. lost reply during partition) must not enter the pool or chain twice. → Task 4 test.
- `cloud-api` restarted while votes wait in the pool: after restart those votes are mined, none lost. → Task 3 + Task 4 tests.
- Receipt typed with spaces/uppercase, or shorter than 16 chars: normalize (strip, lowercase); wrong length → `tidak ditemukan`, never a 500. → Task 2 and Task 4 tests.
- Tampered `rantai.json` (edited vote): `/rantai/validasi` reports the first broken index instead of crashing on load. → Task 3 test.

---

### Task 1: New repo from Praktikum 5 and Presma case data

**Files:**
- Create: repo root from copy of `..\skt-voting\*` (exclude `.env` contents' token, `__pycache__`, `*.db`, `.venv`)
- Create: `.gitignore`, `laptop-a/.env.example`, `laptop-b/.env.example`
- Create: `laptop-a/edge-api/nim.py`
- Modify: `laptop-a/edge-api/daftar.py`, `laptop-a/edge-api/app.py:54-70` (`periksa`), `laptop-a/voter-sim/voter.py:13-27`, `laptop-b/cloud-api/penyimpanan.py:14-16`, `laptop-a/docker-compose.yml:1`, `laptop-b/docker-compose.yml:1`
- Test: `tests/test_daftar.py`

**Interfaces:**
- Produces: `daftar.PEMILIH: set[str]`, `daftar.KANDIDAT: dict[int, str]`, `nim.periksa_nim(nim: str) -> str | None` (reason or None), adapted from Blockchain `validasi_nim_untad`

- [ ] **Step 1: Copy and init.** Copy `skt-voting` contents into the repo root (spec doc already there), `git init`. `.gitignore`: `.env`, `__pycache__/`, `*.db`, `.venv/`, `*.jsonl`. Create both `.env.example` from current `.env` with token replaced by `ganti-dengan-token-kelompok`, Laptop A `TPS_ID=tps-ft`, Laptop B plus `DIFFICULTY=3` and `TAMBANG_TIAP_S=3`. Local `.env` files: copy from examples (keep the group's real token value from `skt-voting` in the untracked `.env`).
- [ ] **Step 2: Commit baseline** `chore: import Praktikum 5 voting base` (before edits, so the diff shows our changes).
- [ ] **Step 3: Write failing test** `tests/test_daftar.py` (adds `laptop-a/edge-api` to `sys.path`):

```python
def test_daftar_presma():
    assert KANDIDAT == {1: "Paslon 1", 2: "Paslon 2"}
    assert len(PEMILIH) == 150
    assert {"F55119001", "A12125010", "C30122005"} <= PEMILIH and "F55125011" not in PEMILIH

def test_periksa_nim():
    assert periksa_nim("F55119001") is None              # angkatan lama tetap boleh
    assert periksa_nim("Z55125001") == "Kode Fakultas 'Z' tidak terdaftar di UNTAD!"
    assert periksa_nim("f55125001") and periksa_nim("XX001") # format salah -> alasan
```

- [ ] **Step 4: Run** `python -m pytest tests/test_daftar.py -q` → FAIL.
- [ ] **Step 5: Implement.** `daftar.py`: PEMILIH per Global Constraints, KANDIDAT as above. `nim.py` `periksa_nim`; `periksa()` in `app.py` calls it right after the voting-open checks, then the DPT check. `voter.py`: valid voter = random pick from the same DPT formula, 5% NIM not in DPT (e.g. `F55125099`), keep the 5% `XX` branch (wrong format), `pilihan_acak` returns 9 at 3% else `random.choice([1, 2])`. `penyimpanan.py` comment: voters F55125001–F55125150. Compose `name:` → `presma-a` / `presma-b`.
- [ ] **Step 6: Run** test → PASS. `docker compose config` in both laptop folders → valid.
- [ ] **Step 7: Commit** `feat: Presma UNTAD case data (2 paslon, 150 voters)`.

### Task 2: Receipt (kode bukti) at the TPS

**Files:**
- Create: `laptop-a/edge-api/bukti.py`, `laptop-b/cloud-api/bukti.py` (identical copies, like `lamport.py`)
- Modify: `laptop-a/edge-api/tps_db.py`, `laptop-a/edge-api/setor.py:18-25`, `laptop-a/edge-api/app.py:73-97`
- Test: `tests/test_bukti.py`, `tests/test_tps_db.py`

**Interfaces:**
- Produces: `bukti.hitung(pesan: dict) -> str` (16 hex); `bukti.rapikan(kode: str) -> str | None` (strip+lowercase, None unless 16 hex chars)
- Produces: `tps_db.simpan_lokal(pemilih_id: str, pilihan: int, tps_id: str) -> tuple[int, str] | None` (seq, bukti); `tps_db.status_bukti(kode: str) -> str`; rows from `ambil_antre` include `bukti`
- Produces: `POST /suara` reply gains `"bukti": str | None`; `GET /bukti/{kode}` → `{"bukti": kode, "status": ...}`

- [ ] **Step 1: Failing tests.**

```python
# test_bukti.py
P = {"request_id": "r1", "tps_id": "tps-ft", "seq": 1, "pemilih_id": "F55125001", "pilihan": 1, "waktu": 1}
def test_hitung_stabil_dan_sensitif():
    assert hitung(P) == hitung(dict(reversed(P.items())))
    assert len(hitung(P)) == 16 and hitung(P) != hitung({**P, "pilihan": 2})
    assert hitung({**P, "lamport": 9, "bukti": "x"}) == hitung(P)   # only the six fields count
def test_rapikan():
    k = hitung(P)
    assert rapikan(f"  {k.upper()} ") == k
    assert rapikan("abc") is None and rapikan("z" * 16) is None

# test_tps_db.py (set TPS_DB to a tmp file before import)
def test_simpan_dan_status_bukti():
    seq, kode = tps_db.simpan_lokal("F55125001", 1, "tps-ft")
    assert tps_db.status_bukti(kode) == "antre di TPS"
    tps_db.tandai_terkirim(tps_db.ambil_antre()[0]["request_id"])
    assert tps_db.status_bukti(kode) == "terkirim"
    assert tps_db.simpan_lokal("F55125001", 2, "tps-ft") is None
    assert tps_db.status_bukti("0" * 16) == "tidak ditemukan"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** `bukti.py` per Global Constraints. `tps_db`: add column `bukti TEXT`; `simpan_lokal` inserts, then computes `hitung` from the stored row (request_id, tps_id, seq, pemilih_id, pilihan, waktu) and updates `bukti` in the same lock. `setor.py` adds `"bukti": s["bukti"]` to `pesan`. `app.py`: pass `TPS_ID`, put `bukti` in reply, add `GET /bukti/{kode}` (uses `rapikan`; invalid → `tidak ditemukan`).
- [ ] **Step 4: Run** tests → PASS.
- [ ] **Step 5: Commit** `feat: vote receipt (kode bukti) at TPS`.

### Task 3: Hash chain module for the tally center

**Files:**
- Create: `laptop-b/cloud-api/rantai.py`
- Test: `tests/test_rantai.py`

**Interfaces:**
- Produces: `class Rantai(path: str, difficulty: int)`; `.tambah_pool(tx: dict) -> bool` (False if `bukti` already in pool or chain); `.tambang() -> dict | None` (mined block, saved to `path`; PoW done without holding the lock); `.cari(kode: str) -> int | None` (block index); `.di_pool(kode: str) -> bool`; `.validasi() -> tuple[bool, int | None, str]`; `.ringkas() -> dict` (`panjang`, `difficulty`, `pool`, `terakhir`)
- Block dict keys: `index`, `timestamp`, `transaksi` (list of vote dicts incl. `bukti`), `previous_hash`, `nonce`, `hash`. Genesis: index 0, timestamp 0, previous_hash `"0"`, no tx.

- [ ] **Step 1: Failing tests** (tmp path):

```python
def test_tambang_dan_cari(tmp_path):
    r = Rantai(str(tmp_path / "c.json"), 2)
    assert r.tambah_pool(TX) and not r.tambah_pool(TX)
    b = r.tambang()
    assert b["index"] == 1 and b["hash"].startswith("00") and r.cari(TX["bukti"]) == 1
    assert not r.tambah_pool(TX) and r.tambang() is None
def test_persisten(tmp_path):      # reload from file keeps blocks
def test_validasi_deteksi_ubah(tmp_path):
    # mine 2 blocks, edit pilihan in block 1 inside the JSON file, reload
    assert Rantai(p, 2).validasi()[:2] == (False, 1)
def test_validasi_normal(tmp_path):
    assert r.validasi() == (True, None, "rantai valid")
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `rantai.py`, adapting `Block.hitung_hash`, `tambang`, and `validasi_rantai` from Blockchain PB1 `node.py` (dict blocks, no signatures). Write `path` via temp file + `os.replace`. Missing/corrupt-JSON file → start from genesis and log a warning (do not crash).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: proof-of-work hash chain for tally center`.

### Task 4: Wire chain and receipts into cloud-api

**Files:**
- Modify: `laptop-b/cloud-api/app.py`, `laptop-b/cloud-api/penyimpanan.py`
- Test: `tests/test_cloud_api.py` (FastAPI `TestClient`; env `DB_PATH`, `RANTAI_PATH`, `TPS_TOKEN=t`, `DIFFICULTY=1`, `TAMBANG_TIAP_S=0.2`, `MQTT_HOST=127.0.0.1`, `LOG_DIR` tmp set before import)

**Interfaces:**
- Consumes: `bukti.hitung/rapikan`, `Rantai`
- Produces: `Suara.bukti: str = ""`; `POST /suara` order: token (401) → receipt recompute mismatch (422 `bukti tidak cocok`) → `db.simpan` → if new, `rantai.tambah_pool`; `GET /bukti/{kode}`, `GET /rantai`, `GET /rantai/validasi`; `penyimpanan.status_bukti(kode) -> str`, `penyimpanan.tandai_block(bukti_list: list[str], index: int)`, `penyimpanan.belum_ditambang() -> list[dict]`; Lamport event `lokal("tambang", block=index, jumlah=n)`.

- [ ] **Step 1: Failing tests.**

```python
def test_tanpa_token_401_walau_tanpa_bukti():  # tps_gadungan payload
    assert c.post("/suara", json=PALSU).status_code == 401
def test_bukti_salah_422():
    assert c.post("/suara", json={**S, "bukti": "0"*16}, headers=H).status_code == 422
def test_alur_bukti_sampai_block():
    assert c.get(f"/bukti/{S['bukti']}").json()["status"] == "belum diterima pusat rekap"
    assert c.post("/suara", json=S, headers=H).status_code == 201
    assert c.get(f"/bukti/{S['bukti']}").json()["status"] == "diterima, menunggu ditambang"
    tunggu_sampai(lambda: c.get(f"/bukti/{S['bukti']}").json()["status"] == "tercatat di block 1")
    assert c.get("/rantai/validasi").json()["valid"] is True
def test_kirim_ulang_tidak_dobel():
    c.post("/suara", json=S, headers=H)          # same request_id again
    assert sum(len(b["transaksi"]) for b in blok_semua()) == 1
    assert c.get("/rekap").json()["kiriman_ganda"] == 0
def test_pool_selamat_saat_restart():
    # insert via db.simpan without mining, re-create app module (reload), miner mines it
def test_bukti_input_aneh():
    assert c.get("/bukti/%20ABC").json()["status"] == "tidak ditemukan"
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** `penyimpanan`: add columns `bukti TEXT`, `block INTEGER`; `simpan` stores `bukti`. `app.py`: `Suara.bukti` default `""`; receipt check after token; on startup create `Rantai(os.getenv("RANTAI_PATH", "/data/rantai.json"), DIFFICULTY)`, re-pool `belum_ditambang()` rows whose bukti is not in the chain, start miner thread (loop: `tambang()` → `tandai_block` → Lamport `tambang`; sleep `TAMBANG_TIAP_S`). Status for `/bukti`: chain index → `tercatat di block N`; in pool → `diterima, menunggu ditambang`; else `belum diterima pusat rekap`; invalid format → `tidak ditemukan`. `/rantai/validasi` returns `{"valid", "index_rusak", "alasan", "panjang"}`.
- [ ] **Step 4: Run** all tests → PASS.
- [ ] **Step 5: Commit** `feat: record accepted votes on chain with receipt lookup`.

### Task 5: Bilik and board UI

**Files:**
- Modify: `laptop-a/edge-api/bilik.html`, `laptop-b/cloud-api/papan.html`

- [ ] **Step 1:** `bilik.html`: after an accepted vote, show the receipt prominently with a copy hint and a "Cek status" button calling `GET /bukti/{kode}` (local status). Labels `Paslon 1`/`Paslon 2` come from `/daftar`.
- [ ] **Step 2:** `papan.html`: add "Cek bukti suara" input → `GET /bukti/{kode}`; chain box (height, pool size, last hash prefix, valid/invalid with broken index from `/rantai/validasi`, refreshed with the existing 2 s timer). Reuse existing CSS classes; no candidate shown for a receipt.
- [ ] **Step 3:** Run both stacks (Task 6 setup) and check pages in the browser: vote in bilik → receipt → board shows `tercatat di block N`.
- [ ] **Step 4: Commit** `feat: show receipt in bilik and receipt check on board`.

### Task 6: End-to-end evidence on one machine

**Files:**
- Create: `docs/uji/` notes with real outputs (commands + output text), used later in the report
- Modify: `laptop-a/.env` locally only (`CLOUD_HOST=host.docker.internal` for single-machine runs)

- [ ] **Step 1:** `docker compose up --build -d` in `laptop-b` then `laptop-a`. Open voting on board (`POST /pemungutan/buka`).
- [ ] **Step 2:** Core 1, 4, 5: vote in bilik; `Z55125001` (faculty code), `F55125099` (not in DPT) and paslon 9 rejected with their reasons; board count rises.
- [ ] **Step 3:** Core 6: `docker compose exec edge-api python tps_gadungan.py` → five `401`.
- [ ] **Step 4:** Core 3: `docker compose exec edge-api python uji_urutan.py` → `Lamport clock : LULUS`. Group test: `docker compose restart cloud-api` mid-voting, rerun `uji_urutan.py` → LULUS, `/rantai/validasi` valid, `kiriman_ganda`=0.
- [ ] **Step 5:** Core 7: fresh volumes (`down -v` both), open voting, `docker compose exec edge-api python ukur_voting.py beban 150` → record throughput, p50/p95, rejected.
- [ ] **Step 6:** Core 8 + unique rule under partition: `docker compose stop cloud-api` (single-machine stand-in for unplugging) for ≥60 s while voting continues; record A `/status` and B `/rekap` before/during/after; one bilik receipt shows `belum diterima pusat rekap` during, `tercatat di block N` after; `kiriman_ganda`=`pemilih_ganda`=0.
- [ ] **Step 7:** Commit evidence `docs: single-machine test evidence`. Note in the file that the two-laptop run (real network cut) is still to be done by the group.

### Task 7: README

**Files:**
- Create: `README.md` (English, readme-pro skill)

- [ ] **Step 1:** Load `readme-pro`; write README: case, unique rule, architecture table, two-laptop setup (`.env` per laptop, firewall ports 9090/1883), demo order (4 demo points), test commands, link to spec. Run its checker.
- [ ] **Step 2: Commit** `docs: README for SKT Presma blockchain voting`.
