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

Le sonde vengono scoperte da sole fra le integrazioni già configurate:
- la scheda Wi-Fi del server, tramite il Supervisor (HA OS e Supervised);
- gli Shelly di seconda generazione e successivi, con il comando Wifi.Scan.

Ogni sonda restituisce le reti viste come `analysis.Network`.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.hassio import is_hassio

from .analysis import Network, band_of, channel_from_frequency
from .const import PROBE_HOST, PROBE_SHELLY, SCAN_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class ProbeError(Exception):
    """La sonda non ha risposto o ha rifiutato la scansione."""


@dataclass(slots=True)
class Probe:
    """Una sonda disponibile."""

    probe_id: str
    kind: str
    name: str
    area: str | None = None
    bands: tuple[str, ...] = ("2.4",)
    # Sonde con la radio occupata dalla connessione: la scansione le disturba.
    disruptive: bool = True
    rssi: int | None = None
    entry_id: str | None = None
    interface: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.probe_id, "kind": self.kind, "name": self.name,
            "area": self.area, "bands": list(self.bands),
            "disruptive": self.disruptive, "rssi": self.rssi,
        }


def _device_for_entry(hass: HomeAssistant, entry_id: str) -> tuple[str | None, str | None]:
    """Nome e area del dispositivo di una config entry."""
    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry_id)
    if not devices:
        return None, None
    device = devices[0]
    area = None
    if device.area_id and (item := ar.async_get(hass).async_get_area(device.area_id)):
        area = item.name
    return device.name_by_user or device.name, area


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
    """Elenca le sonde disponibili adesso."""
    probes: list[Probe] = []
    probes.extend(await _discover_host(hass))
    probes.extend(_discover_shelly(hass))
    return probes


async def _discover_host(hass: HomeAssistant) -> list[Probe]:
    if not is_hassio(hass):
        return []
    try:
        from homeassistant.components.hassio import get_supervisor_client

        info = await get_supervisor_client(hass).network.info()
    except Exception as err:  # noqa: BLE001 - il Supervisor può mancare o non rispondere
        _LOGGER.debug("Supervisor non disponibile per le schede Wi-Fi: %s", err)
        return []
    probes = []
    for iface in info.interfaces:
        if str(iface.type) != "wireless":
            continue
        probes.append(
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
        )
    return probes


def _discover_shelly(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in hass.config_entries.async_entries("shelly"):
        # Gen1 non ha la scansione; quelli a batteria dormono.
        if entry.data.get("gen", 1) < 2 or entry.data.get("sleep_period"):
            continue
        if shelly_rpc_device(hass, entry.entry_id) is None:
            continue
        name, area = _device_for_entry(hass, entry.entry_id)
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


def default_probes(probes: list[Probe], limit: int) -> list[str]:
    """Sonde proposte di default: la scheda del server e uno Shelly per stanza.

    Nella stessa stanza vince lo Shelly col segnale migliore, che si ricollega
    prima dopo la scansione.
    """
    chosen = [p.probe_id for p in probes if p.kind == PROBE_HOST]
    best: dict[str, Probe] = {}
    for probe in probes:
        if probe.kind != PROBE_SHELLY:
            continue
        key = probe.area or probe.probe_id
        current = best.get(key)
        if current is None or (probe.rssi or -100) > (current.rssi or -100):
            best[key] = probe
    ranked = sorted(best.values(), key=lambda p: -(p.rssi or -100))
    chosen.extend(p.probe_id for p in ranked[:limit])
    return chosen


async def async_scan(hass: HomeAssistant, probe: Probe) -> list[Network]:
    """Esegue la scansione di una sonda."""
    if probe.kind == PROBE_SHELLY:
        return await _scan_shelly(hass, probe)
    if probe.kind == PROBE_HOST:
        return await _scan_host(hass, probe)
    raise ProbeError(f"Tipo di sonda sconosciuto: {probe.kind}")


async def _scan_shelly(hass: HomeAssistant, probe: Probe) -> list[Network]:
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
    return networks


async def _scan_host(hass: HomeAssistant, probe: Probe) -> list[Network]:
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
    return networks
