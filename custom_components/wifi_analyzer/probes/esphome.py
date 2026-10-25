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
"""Sonda: dispositivi ESPHome con l'azione `wifi_scan`.

ESPHome da solo espone solo nome e segnale delle reti (sensore scan_results,
senza canale né BSSID). Con il blocco YAML del README il dispositivo offre
un'azione API con risposta (ESPHome >= 2025.12) che Home Assistant registra
come servizio esphome.<nome_nodo>_wifi_scan: la sonda compare da sola appena
il servizio esiste.

Risposta attesa: {"aps": [{"ssid", "bssid", "channel", "rssi"}]}.
Facoltativo, per lo sniffer: {"busy": [{"channel", "busy"}]} con busy in %.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from ..const import SCAN_TIMEOUT
from .base import Probe, ProbeError, ScanResult, device_for_entry, loaded_entries, norm_bssid, to_int

KIND = "esphome"
ACTION = "wifi_scan"


def _service_name(entry) -> str | None:
    """Nome del servizio HA dell'azione, come lo costruisce l'integrazione esphome."""
    info = getattr(getattr(entry, "runtime_data", None), "device_info", None)
    node = getattr(info, "name", None)
    if not node:
        return None
    return f"{node.replace('-', '_')}_{ACTION}"


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in loaded_entries(hass, "esphome"):
        service = _service_name(entry)
        if not service or not hass.services.has_service("esphome", service):
            continue
        name, area = device_for_entry(hass, entry.entry_id)
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=name or entry.title,
                area=area,
                experimental=True,
                entry_id=entry.entry_id,
                extra={"service": service},
            )
        )
    return probes


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    service = probe.extra.get("service")
    if not service or not hass.services.has_service("esphome", service):
        raise ProbeError("Azione wifi_scan non disponibile sul dispositivo")
    try:
        response = await asyncio.wait_for(
            hass.services.async_call("esphome", service, {}, blocking=True, return_response=True),
            SCAN_TIMEOUT,
        )
    except Exception as err:  # noqa: BLE001
        raise ProbeError(str(err)) from err
    result = ScanResult()
    for item in (response or {}).get("aps", []):
        channel = to_int(item.get("channel"))
        rssi = to_int(item.get("rssi"))
        bssid = norm_bssid(item.get("bssid"))
        if channel and rssi is not None and bssid:
            result.networks.append(Network(bssid=bssid, ssid=item.get("ssid") or "", channel=channel,
                                           rssi=rssi, probe=probe.probe_id, band=band_of(channel)))
    for item in (response or {}).get("busy", []):
        channel = to_int(item.get("channel"))
        if channel and item.get("busy") is not None:
            result.utilization.append({"band": band_of(channel), "channel": channel, "busy": float(item["busy"])})
    return result
