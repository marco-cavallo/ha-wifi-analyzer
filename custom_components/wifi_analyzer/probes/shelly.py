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
"""Sonda: Shelly di seconda generazione e successivi (Gen2, Gen3, Gen4).

Il comando RPC Wifi.Scan dura circa 3 secondi, durante i quali lo Shelly si
stacca dal Wi-Fi. Si passa dall'oggetto RpcDevice dell'integrazione Shelly,
che ha già indirizzo e credenziali.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from ..const import PROBE_SHELLY, SCAN_TIMEOUT
from .base import Probe, ProbeError, ScanResult, device_for_entry


def shelly_rpc_device(hass: HomeAssistant, entry_id: str):
    """L'oggetto RpcDevice di aioshelly di una config entry Shelly, se pronto."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        return None
    coordinator = getattr(getattr(entry, "runtime_data", None), "rpc", None)
    device = getattr(coordinator, "device", None)
    if device is None or not getattr(device, "initialized", False):
        return None
    return device


def shelly_wifi_status(hass: HomeAssistant, entry) -> dict[str, Any] | None:
    """Stato Wi-Fi di uno Shelly dalla memoria dell'integrazione, senza richieste.

    Gen2+: componente `wifi` (ssid, bssid, rssi, dal fw 1.x anche channel).
    Gen1: `wifi_sta` (ssid, rssi; niente bssid).
    """
    if entry.state is not ConfigEntryState.LOADED:
        return None
    data = getattr(entry, "runtime_data", None)
    for attr, key in (("rpc", "wifi"), ("block", "wifi_sta")):
        device = getattr(getattr(data, attr, None), "device", None)
        if device is None or not getattr(device, "initialized", False):
            continue
        status = getattr(device, "status", None) or {}
        wifi = status.get(key)
        if isinstance(wifi, dict):
            return wifi
    return None


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in hass.config_entries.async_entries("shelly"):
        # Gen1 non ha la scansione; quelli a batteria dormono.
        if entry.data.get("gen", 1) < 2 or entry.data.get("sleep_period"):
            continue
        if shelly_rpc_device(hass, entry.entry_id) is None:
            continue
        name, area = device_for_entry(hass, entry.entry_id)
        wifi = shelly_wifi_status(hass, entry) or {}
        probes.append(
            Probe(
                probe_id=f"{PROBE_SHELLY}:{entry.unique_id or entry.entry_id}",
                kind=PROBE_SHELLY,
                name=name or entry.title,
                area=area,
                rssi=wifi.get("rssi"),
                entry_id=entry.entry_id,
            )
        )
    return probes



async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    device = shelly_rpc_device(hass, probe.entry_id) if probe.entry_id else None
    if device is None:
        raise ProbeError("Dispositivo non raggiungibile")
    try:
        result = await device.call_rpc("Wifi.Scan", timeout=SCAN_TIMEOUT)
    except Exception as err:  # noqa: BLE001 - aioshelly solleva tipi diversi per versione
        raise ProbeError(str(err) or type(err).__name__) from err
    networks = []
    for item in result.get("results", []):
        channel = item.get("channel")
        bssid = (item.get("bssid") or "").lower()
        if not channel or not bssid or item.get("rssi") is None:
            continue
        networks.append(
            Network(
                bssid=bssid,
                ssid=item.get("ssid") or "",
                channel=int(channel),
                rssi=int(item["rssi"]),
                probe=probe.probe_id,
                band=band_of(int(channel)),
            )
        )
    return ScanResult(networks=networks)
