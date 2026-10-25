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
"""Sonda: AVM FRITZ!Box, tramite l'integrazione fritz.

TR-064 non ha un elenco delle reti vicine. Ha però la topologia mesh in JSON
(Hosts1 X_AVM-DE_GetMeshListPath, fritzconnection get_mesh_topology), che
per ogni radio di ogni nodo della mesh riporta:
  channel_utilization  occupazione in %
  current_channel, ssid, mac_address, opmode
Quindi questa sonda dà occupazione e canali dei propri access point, ma non
i vicini (vanno viste con un'altra sonda). Solo il FRITZ!Box principale della
mesh restituisce la topologia.
Mai provata su un box vero: "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from ..analysis import band_of
from .base import Probe, ProbeError, ScanResult, loaded_entries, norm_bssid, to_int

KIND = "fritz"
UNKNOWN = 255


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    return [
        Probe(
            probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
            kind=KIND,
            name=f"FRITZ!Box {entry.title}",
            bands=("2.4", "5"),
            disruptive=False,
            experimental=True,
            entry_id=entry.entry_id,
        )
        for entry in loaded_entries(hass, "fritz")
        if getattr(getattr(entry, "runtime_data", None), "fritz_hosts", None) is not None
    ]


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    entry = next((e for e in loaded_entries(hass, "fritz") if e.entry_id == probe.entry_id), None)
    hosts = getattr(getattr(entry, "runtime_data", None), "fritz_hosts", None)
    if hosts is None:
        raise ProbeError("Integrazione FRITZ!Box non caricata")
    try:
        topology: dict[str, Any] = await hass.async_add_executor_job(hosts.get_mesh_topology)
    except Exception as err:  # noqa: BLE001 - FritzActionError sui box non principali
        raise ProbeError(f"Topologia mesh non disponibile (box secondario?): {err}") from err

    result = ScanResult()
    seen: set[tuple[str, int]] = set()
    for node in topology.get("nodes", []):
        for iface in node.get("node_interfaces", []):
            if str(iface.get("type", "")).upper() != "WLAN":
                continue
            channel = to_int(iface.get("current_channel"))
            if not channel or channel == UNKNOWN:
                continue
            band = band_of(channel)
            if str(iface.get("opmode", "")).upper() in ("AP", "AP_GUEST"):
                if iface.get("mac_address"):
                    result.own_aps.append({"bssid": norm_bssid(iface["mac_address"]), "ssid": iface.get("ssid"),
                                           "channel": channel, "band": band, "name": node.get("device_name")})
                busy = to_int(iface.get("channel_utilization"))
                key = (str(node.get("device_mac_address")), channel)
                if busy is not None and busy != UNKNOWN and key not in seen:
                    seen.add(key)
                    result.utilization.append({"band": band, "channel": channel, "busy": float(busy),
                                               "ap": node.get("device_name")})
    if not result.utilization and not result.own_aps:
        raise ProbeError("Nessuna radio Wi-Fi nella topologia")
    return result
