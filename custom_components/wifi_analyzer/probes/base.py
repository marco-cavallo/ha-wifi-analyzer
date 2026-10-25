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
"""Tipi comuni a tutte le sonde.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr

from ..analysis import Network


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
    # Scritte seguendo la documentazione ma non ancora provate su un
    # apparecchio vero: il pannello lo dice.
    experimental: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.probe_id, "kind": self.kind, "name": self.name,
            "area": self.area, "bands": list(self.bands),
            "disruptive": self.disruptive, "rssi": self.rssi,
            "experimental": self.experimental,
        }


@dataclass(slots=True)
class ScanResult:
    """Quello che una sonda riporta da una scansione.

    `utilization`: occupazione reale del canale dove la sonda la misura
    (router che la espongono, sniffer ESP32), una voce per canale:
    {"band", "channel", "busy"} con busy in percentuale.
    """

    networks: list[Network] = field(default_factory=list)
    utilization: list[dict[str, Any]] = field(default_factory=list)
    # Access point di casa noti al router: {"bssid", "ssid", "channel", "band", "name"}.
    # Servono a riconoscere la propria rete e il canale attuale anche quando
    # nessun'altra sonda li vede.
    own_aps: list[dict[str, Any]] = field(default_factory=list)


def loaded_entries(hass: HomeAssistant, domain: str) -> list[ConfigEntry]:
    """Config entry caricate di un'altra integrazione."""
    return [
        e for e in hass.config_entries.async_entries(domain)
        if e.state is ConfigEntryState.LOADED
    ]


def device_for_entry(hass: HomeAssistant, entry_id: str) -> tuple[str | None, str | None]:
    """Nome e area del primo dispositivo di una config entry."""
    registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(registry, entry_id)
    if not devices:
        return None, None
    device = devices[0]
    area = None
    if device.area_id and (item := ar.async_get(hass).async_get_area(device.area_id)):
        area = item.name
    return device.name_by_user or device.name, area


BAND_BY_RADIO = {"ng": "2.4", "na": "5", "2g": "2.4", "5g": "5"}


def to_int(value: Any) -> int | None:
    """Primo numero intero in un valore ("36 / 5180MHz" -> 36)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = ""
    for ch in str(value).strip():
        if ch.isdigit() or (ch == "-" and not digits):
            digits += ch
        elif digits:
            break
    try:
        return int(digits)
    except ValueError:
        return None


def norm_bssid(value: Any) -> str:
    """BSSID in minuscolo con i due punti, qualunque formato arrivi."""
    raw = str(value or "").strip().lower().replace("-", ":")
    if len(raw) == 12 and ":" not in raw:
        raw = ":".join(raw[i:i + 2] for i in range(0, 12, 2))
    return raw
