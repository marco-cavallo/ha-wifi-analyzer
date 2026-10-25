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
"""Sonda: TP-Link Omada, tramite l'integrazione tplink_omada.

- Occupazione: ogni access point riporta per radio rx/tx/interferenza in %
  (OmadaAccessPoint.radio_status), già supportato dalla libreria.
- Reti vicine: "Rogue AP" del controller (Insights, controller >= 5.15, non
  su Omada Essentials) via OpenAPI insight/rogueaps, che la libreria non
  copre: si usa la sua connessione interna. Se il controller non lo permette
  (versione o permessi) restano solo occupazione e canali.
La "RF scan" di Omada fa cadere il Wi-Fi per minuti: qui non si usa.

Verificato sul sorgente di HA 2026.10 / tplink-omada-client 1.5.13, mai
provato su un controller vero: "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from .base import Probe, ProbeError, ScanResult, loaded_entries, norm_bssid, to_int

_LOGGER = logging.getLogger(__name__)

KIND = "omada"


def _controller(hass: HomeAssistant, entry_id: str | None):
    for entry in loaded_entries(hass, "tplink_omada"):
        if entry_id is None or entry.entry_id == entry_id:
            return getattr(entry, "runtime_data", None)
    return None


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in loaded_entries(hass, "tplink_omada"):
        if getattr(getattr(entry, "runtime_data", None), "omada_client", None) is None:
            continue
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=f"Omada {entry.title}",
                bands=("2.4", "5"),
                disruptive=False,
                experimental=True,
                entry_id=entry.entry_id,
            )
        )
    return probes


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    controller = _controller(hass, probe.entry_id)
    site = getattr(controller, "omada_client", None)
    if site is None:
        raise ProbeError("Integrazione Omada non caricata")
    result = ScanResult()

    # Reti vicine: OpenAPI non coperta dalla libreria, attributi interni.
    try:
        api = site._api  # noqa: SLF001
        url = api.format_openapi_url("insight/rogueaps", site=site._site_id)  # noqa: SLF001
        data = await api.request("get", url, params={"page": 1, "pageSize": 1000})
        for item in (data or {}).get("data", []):
            channel = to_int(item.get("channel"))
            rssi = to_int(item.get("signal"))
            bssid = norm_bssid(item.get("bssid"))
            if channel and rssi is not None and bssid:
                result.networks.append(
                    Network(bssid=bssid, ssid=item.get("ssid") or "", channel=channel,
                            rssi=rssi, probe=probe.probe_id, band=band_of(channel))
                )
    except Exception as err:  # noqa: BLE001 - versione o permessi del controller
        _LOGGER.info("Omada: reti vicine non disponibili (%s)", err)

    # Occupazione e canali dei propri access point.
    devices: dict[str, Any] = getattr(getattr(controller, "devices_coordinator", None), "data", None) or {}
    for mac, device in devices.items():
        if str(getattr(device, "type", "")).lower() != "ap":
            continue
        try:
            ap = await site.get_access_point(mac)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Omada: AP %s non leggibile: %s", mac, err)
            continue
        for radio_id in ap.radio_bands:
            status = ap.radio_status(radio_id)
            if status is None:
                continue
            channel = to_int(getattr(status, "actual_channel", None))
            if not channel or channel > 177:
                continue
            busy = sum(
                float(getattr(status, attr, 0) or 0)
                for attr in ("rx_utilization", "tx_utilization", "interference_utilization")
            )
            band = band_of(channel)
            result.utilization.append(
                {"band": band, "channel": channel, "busy": min(busy, 100.0), "ap": getattr(device, "name", mac)}
            )
            result.own_aps.append(
                {"bssid": None, "ssid": None, "channel": channel, "band": band, "name": getattr(device, "name", mac)}
            )
    if not result.networks and not result.utilization:
        raise ProbeError("Nessun dato dal controller Omada (versione o permessi?)")
    return result
