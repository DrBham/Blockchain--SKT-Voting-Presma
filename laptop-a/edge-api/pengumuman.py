import json
import logging
import os

import paho.mqtt.client as mqtt

import lamport as clock

CLOUD_HOST = os.environ["CLOUD_HOST"]
TPS_ID = os.getenv("TPS_ID", "tps-1")
TOPIK = "voting/pemungutan"
log = logging.getLogger("uvicorn.error")
status = {"pemungutan": "belum ada pengumuman"}


def _saat_terhubung(client, userdata, flags, reason_code, properties):
    log.info("pengumuman: terhubung ke broker")
    client.subscribe(TOPIK, qos=1)


def _saat_pesan(client, userdata, msg):
    pesan = json.loads(msg.payload)
    # aturan 3: pengumuman dari pusat rekap diterima
    clock.terima(pesan.get("lamport", 0), "terima-pengumuman", dari="cloud-api",
                 pemungutan=pesan["pemungutan"])
    status["pemungutan"] = pesan["pemungutan"]
    log.info("pengumuman <- %s", pesan)


_klien = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                     client_id=f"{TPS_ID}-pengumuman", clean_session=False)
_klien.on_connect = _saat_terhubung
_klien.on_message = _saat_pesan
_klien.connect_async(CLOUD_HOST, 1883)
_klien.loop_start()
