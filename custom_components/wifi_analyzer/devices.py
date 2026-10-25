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
"""Stato dei dispositivi Wi-Fi di casa, da quello che Home Assistant sa già.

Nessuna richiesta ai dispositivi: gli Shelly si leggono dalla memoria della
loro integrazione (i sensori RSSI sono disattivati di default, quindi non
basterebbero), tutto il resto dai sensori di segnale in dBm.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .analysis import band_of, quality_of
from .const import NON_WIFI_PLATFORMS, NON_WIFI_WORDS
from .probes import shelly_wifi_status

_WORD = re.compile(r"[a-z0-9]+")


@dataclass(slots=True)
class WifiDevice:
    """Un dispositivo collegato al Wi-Fi."""

    key: str
    name: str
    source: str
    area: str | None = None
    rssi: int | None = None
    ssid: str | None = None
    bssid: str | None = None
    channel: int | None = None
    band: str | None = None
    available: bool = True
    entity_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "name": self.name, "source": self.source,
            "area": self.area, "rssi": self.rssi, "quality": quality_of(self.rssi),
            "ssid": self.ssid, "bssid": self.bssid, "channel": self.channel,
            "band": self.band, "available": self.available,
            "entity_id": self.entity_id,
        }


class _Names:
    """Nomi e aree dei dispositivi, con le ricerche nei registri in cache."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.devices = dr.async_get(hass)
        self.areas = ar.async_get(hass)

    def of_device(self, device_id: str | None) -> tuple[str | None, str | None]:
        device = self.devices.async_get(device_id) if device_id else None
        if device is None:
            return None, None
        area_id = device.area_id
        area = self.areas.async_get_area(area_id).name if area_id and self.areas.async_get_area(area_id) else None
        return device.name_by_user or device.name, area

    def of_entry(self, entry_id: str) -> tuple[str | None, str | None, str | None]:
        devices = dr.async_entries_for_config_entry(self.devices, entry_id)
        if not devices:
            return None, None, None
        name, area = self.of_device(devices[0].id)
        return name, area, devices[0].id


def _num(value: Any) -> int | None:
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None


def collect(hass: HomeAssistant) -> list[WifiDevice]:
    """Tutti i dispositivi Wi-Fi riconoscibili."""
    names = _Names(hass)
    found: dict[str, WifiDevice] = {}
    covered_devices: set[str] = set()

    for entry in hass.config_entries.async_entries("shelly"):
        name, area, device_id = names.of_entry(entry.entry_id)
        if device_id:
            covered_devices.add(device_id)
        wifi = shelly_wifi_status(hass, entry)
        available = entry.state is ConfigEntryState.LOADED and wifi is not None
        if entry.data.get("sleep_period") and not available:
            # A batteria: dorme quasi sempre, non è un dispositivo "giù".
            continue
        wifi = wifi or {}
        channel = _num(wifi.get("channel"))
        found[f"shelly:{entry.entry_id}"] = WifiDevice(
            key=f"shelly:{entry.entry_id}",
            name=name or entry.title,
            source="shelly",
            area=area,
            rssi=_num(wifi.get("rssi")),
            ssid=wifi.get("ssid"),
            bssid=(wifi.get("bssid") or "").lower() or None,
            channel=channel,
            band=band_of(channel) if channel else "2.4",
            available=available,
        )

    registry = er.async_get(hass)
    mobile_extra = _mobile_app_extras(hass, registry)
    for item in registry.entities.values():
        if item.domain != "sensor" or item.disabled_by is not None:
            continue
        if item.platform == "shelly" or item.platform in NON_WIFI_PLATFORMS:
            continue
        is_signal = (item.original_device_class or item.device_class) == "signal_strength"
        if not is_signal and item.unit_of_measurement != "dBm":
            continue
        label = " ".join(filter(None, (item.entity_id, item.original_name, item.name))).lower()
        words = set(_WORD.findall(label))
        if words & set(NON_WIFI_WORDS):
            continue
        if item.device_id in covered_devices:
            continue
        state = hass.states.get(item.entity_id)
        if state is None:
            continue
        name, area = names.of_device(item.device_id)
        key = f"entity:{item.device_id or item.entity_id}"
        if key in found:
            continue
        rssi = _num(state.state)
        device = WifiDevice(
            key=key,
            name=name or state.name,
            source=item.platform,
            area=area,
            rssi=rssi,
            available=state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN),
            entity_id=item.entity_id,
        )
        extra = mobile_extra.get(item.device_id or "")
        if extra:
            device.bssid = extra.get("bssid")
            device.ssid = extra.get("ssid")
            freq = _num(extra.get("frequency"))
            if freq:
                device.band = "2.4" if freq < 3000 else "5"
        found[key] = device

    # iPhone: nessun sensore di segnale, ma SSID e BSSID ci sono.
    for device_id, extra in mobile_extra.items():
        key = f"entity:{device_id}"
        if key in found or not extra.get("bssid"):
            continue
        name, area = names.of_device(device_id)
        found[key] = WifiDevice(
            key=key, name=name or device_id, source="mobile_app", area=area,
            ssid=extra.get("ssid"), bssid=extra.get("bssid"),
        )

    return sorted(found.values(), key=lambda d: (d.rssi is None, d.rssi or 0))


def _mobile_app_extras(hass: HomeAssistant, registry: er.EntityRegistry) -> dict[str, dict[str, str]]:
    """BSSID, SSID e frequenza dei telefoni con l'app Home Assistant.

    Android: wifi_bssid, wifi_connection, wifi_frequency. iOS: bssid, ssid.
    Il nome dell'entità cambia con la lingua, la chiave dello unique_id no.
    """
    extras: dict[str, dict[str, str]] = {}
    for item in registry.entities.values():
        if item.platform != "mobile_app" or not item.device_id or item.disabled_by:
            continue
        uid = (item.unique_id or "").lower()
        if uid.endswith("bssid"):
            field = "bssid"
        elif uid.endswith(("wifi_connection", "_ssid")):
            field = "ssid"
        elif uid.endswith("wifi_frequency"):
            field = "frequency"
        else:
            continue
        state = hass.states.get(item.entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, "<not connected>"):
            continue
        value = state.state.lower() if field == "bssid" else state.state
        extras.setdefault(item.device_id, {})[field] = value
    return extras
