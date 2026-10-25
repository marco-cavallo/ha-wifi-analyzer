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
"""Sonde: chi in casa sa fare una scansione Wi-Fi.

Ogni modulo gestisce un tipo di apparecchio e si appoggia all'integrazione
che l'utente ha già configurato (indirizzi e credenziali sono lì):
`async_discover(hass)` elenca le sonde, `async_scan(hass, probe)` scansiona.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from . import asus, cudy, esphome, freebox, fritz, host, mikrotik, omada, openwrt, shelly, tasmota, unifi, wled
from .base import Probe, ProbeError, ScanResult
from .shelly import shelly_rpc_device, shelly_wifi_status

_LOGGER = logging.getLogger(__name__)

MODULES = {
    "host": host,
    "cudy": cudy,
    "unifi": unifi,
    "omada": omada,
    "openwrt": openwrt,
    "mikrotik": mikrotik,
    "freebox": freebox,
    "fritz": fritz,
    "asus": asus,
    "shelly": shelly,
    "esphome": esphome,
    "tasmota": tasmota,
    "wled": wled,
}

__all__ = [
    "Probe", "ProbeError", "ScanResult", "async_discover", "async_scan",
    "default_probes", "shelly_rpc_device", "shelly_wifi_status",
]


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    """Tutte le sonde disponibili adesso. Un modulo che fallisce non blocca gli altri."""
    probes: list[Probe] = []
    for kind, module in MODULES.items():
        try:
            probes.extend(await module.async_discover(hass))
        except Exception:  # noqa: BLE001 - un'integrazione altrui può essere in uno stato strano
            _LOGGER.exception("Ricerca sonde %s non riuscita", kind)
    return probes


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    module = MODULES.get(probe.kind)
    if module is None:
        raise ProbeError(f"Tipo di sonda sconosciuto: {probe.kind}")
    return await module.async_scan(hass, probe)


def default_probes(probes: list[Probe], limit: int) -> list[str]:
    """Sonde proposte di default.

    Tutte quelle che non disturbano nessuno (scheda del server, router) più
    una per stanza tra quelle che si staccano dal Wi-Fi per scansionare: nella
    stessa stanza vince quella col segnale migliore, che si ricollega prima.
    """
    chosen = [p.probe_id for p in probes if not p.disruptive and not p.experimental]
    best: dict[str, Probe] = {}
    for probe in probes:
        if not probe.disruptive or probe.experimental:
            continue
        key = probe.area or probe.probe_id
        current = best.get(key)
        if current is None or (probe.rssi or -100) > (current.rssi or -100):
            best[key] = probe
    ranked = sorted(best.values(), key=lambda p: -(p.rssi or -100))
    chosen.extend(p.probe_id for p in ranked[:limit])
    return chosen
