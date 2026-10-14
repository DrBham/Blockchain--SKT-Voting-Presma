import json
import logging
import os

import paho.mqtt.client as mqtt

import lamport as clock

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
TOPIK = "voting/pemungutan"
log = logging.getLogger("uvicorn.error")

_klien = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                     client_id="cloud-api-pengumuman")
_klien.connect_async(MQTT_HOST, 1883)
_klien.loop_start()


def umumkan(nilai):
    # retain=True: broker menyimpan pengumuman terakhir, sehingga TPS yang
    # baru tersambung langsung menerimanya
    pesan = {"pemungutan": nilai,
             "lamport": clock.kirim("umumkan", ke="edge-api", pemungutan=nilai)}
    _klien.publish(TOPIK, json.dumps(pesan), qos=1, retain=True)
    log.info("pengumuman -> %s", pesan)
    return pesan
