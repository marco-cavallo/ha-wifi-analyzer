# Copyright 2026 Marco Cavallo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Sonda: dispositivi Tasmota (firmware >= 12.1), via MQTT.

Comando `WifiScan 1` su cmnd/<topic>/WifiScan; i risultati arrivano
asincroni su stat/<topic>/RESULT (o WIFISCAN con SetOption4), un messaggio
per rete, 10 al secondo:
  {"WiFiScan":{"NET1":{"SSId":..,"BSSId":..,"Channel":"6","Signal":"-67",..}}}
Tutti i valori sono stringhe, "Signal" è in dBm ("RSSI" è una percentuale).
Non c'è un messaggio di fine: si chiude dopo qualche secondo di silenzio.

Gli indirizzi MQTT dei dispositivi vengono dai dati di discovery che
l'integrazione tasmota tiene in hass.data (struttura interna di HA 2026.10).
Scritta sul sorgente di Tasmota e HA, mai provata su un dispositivo:
"sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr

from ..analysis import Network, band_of
from .base import Probe, ProbeError, ScanResult, loaded_entries, norm_bssid, to_int

_LOGGER = logging.getLogger(__name__)

KIND = "tasmota"
DISCOVERY_DATA = "tasmota_discovery_data"
FIRST_RESULT_TIMEOUT = 15
QUIET_AFTER = 3


def _topic(config: dict[str, Any], prefix_index: int) -> str:
    """Prefisso MQTT (cmnd/stat/tele) del dispositivo, come lo calcola hatasmota."""
    mac = str(config.get("mac", "")).replace(":", "").upper()
    topic = str(config.get("ft", "%prefix%/%topic%/"))
    topic = topic.replace("%hostname%", str(config.get("hn", "")))
    topic = topic.replace("%id%", mac[-6:])
    topic = topic.replace("%prefix%", str(config.get("tp", ["cmnd", "stat", "tele"])[prefix_index]))
    topic = topic.replace("%topic%", str(config.get("t", "")))
    return topic if topic.endswith("/") else f"{topic}/"


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    entries = loaded_entries(hass, "tasmota")
    if not entries:
        return []
    tasmota_entry_id = entries[0].entry_id
    data: dict[str, Any] = hass.data.get(DISCOVERY_DATA) or {}
    registry = dr.async_get(hass)
    areas = ar.async_get(hass)
    probes = []
    for mac, config in data.items():
        if not isinstance(config, dict) or not config.get("t"):
            continue
        pretty = ":".join(mac[i:i + 2] for i in range(0, 12, 2)).lower()
        connection = (dr.CONNECTION_NETWORK_MAC, pretty)
        if hasattr(registry, "async_get_device_by_connection"):
            device = registry.async_get_device_by_connection(connection, tasmota_entry_id)
        else:  # Home Assistant precedente alla 2026.10
            device = registry.async_get_device(connections={connection})
        area = None
        if device and device.area_id and (item := areas.async_get_area(device.area_id)):
            area = item.name
        probes.append(
            Probe(
                probe_id=f"{KIND}:{mac}",
                kind=KIND,
                name=(device.name_by_user or device.name) if device else config.get("dn") or config.get("hn") or mac,
                area=area,
                experimental=True,
                extra={"cmnd": _topic(config, 0), "stat": _topic(config, 1)},
            )
        )
    return probes


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    from homeassistant.components import mqtt

    found: dict[str, dict[str, Any]] = {}
    last_message = 0.0
    first = asyncio.Event()

    @callback
    def _on_message(msg) -> None:
        nonlocal last_message
        try:
            payload = json.loads(msg.payload)
        except (TypeError, ValueError):
            return
        scan = next((v for k, v in payload.items() if k.lower() == "wifiscan"), None)
        if not isinstance(scan, dict):
            return
        for item in scan.values():
            if isinstance(item, dict) and item.get("BSSId"):
                found[norm_bssid(item["BSSId"])] = item
        last_message = time.monotonic()
        first.set()

    stat = probe.extra["stat"]
    unsubs = [
        await mqtt.async_subscribe(hass, f"{stat}RESULT", _on_message),
        await mqtt.async_subscribe(hass, f"{stat}WIFISCAN", _on_message),
    ]
    try:
        await mqtt.async_publish(hass, f"{probe.extra['cmnd']}WifiScan", "1")
        try:
            await asyncio.wait_for(first.wait(), FIRST_RESULT_TIMEOUT)
        except TimeoutError as err:
            raise ProbeError("Nessuna risposta (firmware < 12.1 o dispositivo spento?)") from err
        while time.monotonic() - last_message < QUIET_AFTER:
            await asyncio.sleep(0.5)
    finally:
        for unsub in unsubs:
            unsub()

    networks = []
    for bssid, item in found.items():
        channel = to_int(item.get("Channel"))
        rssi = to_int(item.get("Signal"))
        if channel and rssi is not None:
            networks.append(Network(bssid=bssid, ssid=item.get("SSId") or "", channel=channel,
                                    rssi=rssi, probe=probe.probe_id, band=band_of(channel)))
    return ScanResult(networks=networks)
