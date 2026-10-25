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
"""Sonda: controller LED WLED (>= 0.14), tramite l'integrazione wled.

GET /json/net: la prima chiamata avvia una scansione e risponde vuoto; a
scansione finita restituisce
  {"networks":[{"ssid","rssi" (dBm),"bssid","channel","enc"}]}
e ne avvia subito un'altra. Quindi si interroga per qualche secondo e ci si
ferma al primo elenco non vuoto: interrogarlo di continuo terrebbe la radio
sempre in scansione.

Il client HTTP è quello dell'integrazione (entry.runtime_data.wled).
Scritta sul sorgente di WLED e HA 2026.10, mai provata: "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from .base import Probe, ProbeError, ScanResult, device_for_entry, loaded_entries, norm_bssid, to_int

KIND = "wled"
POLL_EVERY = 1.5
MAX_WAIT = 15


def _client(hass: HomeAssistant, entry_id: str):
    for entry in loaded_entries(hass, "wled"):
        if entry.entry_id == entry_id:
            return getattr(getattr(entry, "runtime_data", None), "wled", None)
    return None


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in loaded_entries(hass, "wled"):
        coordinator = getattr(entry, "runtime_data", None)
        if getattr(coordinator, "wled", None) is None:
            continue
        name, area = device_for_entry(hass, entry.entry_id)
        wifi = getattr(getattr(getattr(coordinator, "data", None), "info", None), "wifi", None)
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=name or entry.title,
                area=area,
                rssi=getattr(wifi, "rssi", None),
                experimental=True,
                entry_id=entry.entry_id,
            )
        )
    return probes


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    client = _client(hass, probe.entry_id) if probe.entry_id else None
    if client is None:
        raise ProbeError("Integrazione WLED non caricata")
    items: list = []
    waited = 0.0
    try:
        while waited <= MAX_WAIT:
            data = await client.request("/json/net")
            items = (data or {}).get("networks") or []
            if items:
                break
            await asyncio.sleep(POLL_EVERY)
            waited += POLL_EVERY
    except Exception as err:  # noqa: BLE001 - errori del client WLED
        raise ProbeError(str(err)) from err
    if not items:
        raise ProbeError("Nessun risultato (firmware precedente alla 0.14?)")
    networks = []
    for item in items:
        channel = to_int(item.get("channel"))
        rssi = to_int(item.get("rssi"))
        bssid = norm_bssid(item.get("bssid"))
        if channel and rssi is not None and bssid:
            networks.append(Network(bssid=bssid, ssid=item.get("ssid") or "", channel=channel,
                                    rssi=rssi, probe=probe.probe_id, band=band_of(channel)))
    return ScanResult(networks=networks)
