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
"""Sonda: la scheda Wi-Fi del server Home Assistant, tramite il Supervisor.

Funziona su HA OS e Supervised (Raspberry Pi, mini PC, chiavetta USB). Non
serve che la scheda sia collegata a una rete: NetworkManager scansiona anche
con l'interfaccia disattivata.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.hassio import is_hassio

from ..analysis import Network, band_of, channel_from_frequency
from ..const import PROBE_HOST, SCAN_TIMEOUT
from .base import Probe, ProbeError, ScanResult

_LOGGER = logging.getLogger(__name__)


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    if not is_hassio(hass):
        return []
    try:
        from homeassistant.components.hassio import get_supervisor_client

        info = await get_supervisor_client(hass).network.info()
    except Exception as err:  # noqa: BLE001 - il Supervisor può mancare o non rispondere
        _LOGGER.debug("Supervisor non disponibile per le schede Wi-Fi: %s", err)
        return []
    return [
        Probe(
            probe_id=f"{PROBE_HOST}:{iface.interface}",
            kind=PROBE_HOST,
            name=f"Home Assistant ({iface.interface})",
            # Le bande vere dipendono dalla scheda: si vedono dalla prima
            # scansione (una vecchia chiavetta 802.11g vede solo il 2,4 GHz).
            bands=(),
            disruptive=bool(iface.connected),
            interface=iface.interface,
        )
        for iface in info.interfaces
        if str(iface.type) == "wireless"
    ]


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    from homeassistant.components.hassio import get_supervisor_client

    try:
        access_points = await asyncio.wait_for(
            get_supervisor_client(hass).network.access_points(probe.interface),
            SCAN_TIMEOUT,
        )
    except Exception as err:  # noqa: BLE001
        raise ProbeError(str(err) or type(err).__name__) from err
    networks = []
    for ap in access_points:
        channel = channel_from_frequency(ap.frequency)
        if channel is None:
            continue
        networks.append(
            Network(
                bssid=ap.mac.lower(),
                ssid=ap.ssid or "",
                channel=channel,
                # NetworkManager dà la qualità in percentuale, non i dBm:
                # nm_wifi_utils_level_to_quality() mappa -100..-40 dBm su
                # 0..100% in modo lineare, qui si fa l'inverso (100% = -40 o più).
                rssi=round(ap.signal * 0.6 - 100),
                probe=probe.probe_id,
                band=band_of(channel),
            )
        )
    return ScanResult(networks=networks)
