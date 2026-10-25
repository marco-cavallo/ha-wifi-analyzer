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
"""Sonda: Freebox e Iliadbox, tramite l'integrazione freebox.

L'API Freebox OS ha tutto quello che serve, senza avviare scansioni:
- wifi/ap/                     radio del box (id, banda, canale)
- wifi/ap/<id>/neighbors/      reti vicine viste da quella radio
- wifi/ap/<id>/channel_usage/  occupazione per canale (busy_percent)
- wifi/bss/                    BSSID e SSID propri
Il client è quello dell'integrazione (FreeboxRouter._api, freebox-api 1.3).
Nomi dei campi presi dalla documentazione Freebox OS: letture difensive.
Mai provata su un box vero: "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from .base import Probe, ProbeError, ScanResult, loaded_entries, norm_bssid, to_int

_LOGGER = logging.getLogger(__name__)

KIND = "freebox"


def _api(hass: HomeAssistant, entry_id: str | None):
    for entry in loaded_entries(hass, "freebox"):
        if entry_id is None or entry.entry_id == entry_id:
            return getattr(getattr(entry, "runtime_data", None), "_api", None)
    return None


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    return [
        Probe(
            probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
            kind=KIND,
            name=f"Freebox {entry.title}",
            bands=("2.4", "5"),
            disruptive=False,
            experimental=True,
            entry_id=entry.entry_id,
        )
        for entry in loaded_entries(hass, "freebox")
        if getattr(getattr(entry, "runtime_data", None), "_api", None) is not None
    ]


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    api = _api(hass, probe.entry_id)
    wifi = getattr(api, "wifi", None)
    if wifi is None:
        raise ProbeError("Integrazione Freebox non caricata")
    result = ScanResult()
    try:
        aps: list[dict[str, Any]] = await wifi.get_ap_list() or []
    except Exception as err:  # noqa: BLE001
        raise ProbeError(f"Freebox non raggiungibile: {err}") from err

    for ap in aps:
        ap_id = ap.get("id")
        try:
            neighbors = await wifi.get_ap_neighbors(ap_id) or []
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Freebox AP %s: vicini non disponibili: %s", ap_id, err)
            neighbors = []
        for item in neighbors:
            channel = to_int(item.get("channel"))
            rssi = to_int(item.get("signal"))
            bssid = norm_bssid(item.get("bssid"))
            if channel and rssi is not None and bssid:
                result.networks.append(Network(bssid=bssid, ssid=item.get("ssid") or "", channel=channel,
                                               rssi=rssi, probe=probe.probe_id, band=band_of(channel)))
        try:
            usage = await wifi.get_wifi_access_point_channel_usage(ap_id) or []
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Freebox AP %s: occupazione non disponibile: %s", ap_id, err)
            usage = []
        for item in usage:
            channel = to_int(item.get("channel"))
            busy = item.get("busy_percent")
            if channel and busy is not None:
                result.utilization.append({"band": band_of(channel), "channel": channel, "busy": float(busy)})

    try:
        bss_list = await wifi.get_bss() or []
    except Exception:  # noqa: BLE001
        bss_list = []
    channels = {ap.get("id"): to_int((ap.get("status") or {}).get("primary_channel")) for ap in aps}
    for bss in bss_list:
        bssid = norm_bssid(bss.get("id"))
        channel = channels.get(bss.get("phy_id"))
        if bssid and channel:
            result.own_aps.append({"bssid": bssid, "ssid": (bss.get("config") or {}).get("ssid"),
                                   "channel": channel, "band": band_of(channel), "name": "Freebox"})
    if not result.networks and not result.utilization:
        raise ProbeError("Il box non ha restituito reti né occupazione")
    return result
