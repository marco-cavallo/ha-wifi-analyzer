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
"""Sensori: canale attuale e consigliato, punteggio, vicini, dispositivi.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .analysis import BAND_5, BAND_24
from .coordinator import AnalyzerData
from .entity import WifiAnalyzerEntity


@dataclass(frozen=True, kw_only=True)
class AnalyzerSensorDescription(SensorEntityDescription):
    value: Callable[[AnalyzerData], Any]
    attrs: Callable[[AnalyzerData], dict[str, Any]] | None = None
    band: str | None = None


def _band(data: AnalyzerData, band: str) -> dict[str, Any]:
    return data.bands.get(band) or {}


def _band_sensors(band: str, suffix: str) -> list[AnalyzerSensorDescription]:
    return [
        AnalyzerSensorDescription(
            key=f"current_channel_{suffix}",
            band=band,
            icon="mdi:access-point",
            value=lambda d, b=band: _band(d, b).get("current"),
        ),
        AnalyzerSensorDescription(
            key=f"recommended_channel_{suffix}",
            band=band,
            icon="mdi:star-circle-outline",
            value=lambda d, b=band: _band(d, b).get("recommended"),
            attrs=lambda d, b=band: {
                "advice": _band(d, b).get("advice"),
                "gain": _band(d, b).get("gain"),
                "width": _band(d, b).get("width"),
                "warnings": [w["code"] for w in _band(d, b).get("warnings", [])],
            },
        ),
        AnalyzerSensorDescription(
            key=f"channel_score_{suffix}",
            band=band,
            icon="mdi:gauge",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value=lambda d, b=band: _band(d, b).get("current_score"),
            attrs=lambda d, b=band: {
                "scores": {c["channel"]: c["score"] for c in _band(d, b).get("channels", [])},
            },
        ),
        AnalyzerSensorDescription(
            key=f"neighbors_{suffix}",
            band=band,
            icon="mdi:wifi-strength-2",
            state_class=SensorStateClass.MEASUREMENT,
            value=lambda d, b=band: len(_band(d, b).get("neighbors", []))
            if _band(d, b).get("probes") else None,
        ),
    ]


SENSORS: tuple[AnalyzerSensorDescription, ...] = (
    *_band_sensors(BAND_24, "24"),
    *_band_sensors(BAND_5, "5"),
    AnalyzerSensorDescription(
        key="wifi_devices",
        icon="mdi:devices",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: len(d.devices),
    ),
    AnalyzerSensorDescription(
        key="weak_devices",
        icon="mdi:wifi-strength-1-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: sum(1 for x in d.devices if x["quality"] == "weak"),
        attrs=lambda d: {
            "devices": [f'{x["name"]} ({x["rssi"]} dBm)' for x in d.devices if x["quality"] == "weak"],
        },
    ),
    AnalyzerSensorDescription(
        key="offline_devices",
        icon="mdi:wifi-off",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: sum(1 for x in d.devices if not x["available"]),
        attrs=lambda d: {"devices": [x["name"] for x in d.devices if not x["available"]]},
    ),
    AnalyzerSensorDescription(
        key="last_scan",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: dt_util.parse_datetime(d.last_scan["time"]) if d.last_scan else None,
        attrs=lambda d: {
            "duration": d.last_scan.get("duration"),
            "networks": d.last_scan.get("networks"),
            "probes_ok": sum(1 for p in d.last_scan.get("probes", []) if p.get("ok")),
            "probes_failed": [p["name"] for p in d.last_scan.get("probes", []) if not p.get("ok")],
        } if d.last_scan else {},
    ),
    AnalyzerSensorDescription(
        key="probes",
        icon="mdi:radar",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: len(d.probes),
        attrs=lambda d: {"probes": [p.name for p in d.probes]},
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(AnalyzerSensor(coordinator, description) for description in SENSORS)


class AnalyzerSensor(WifiAnalyzerEntity, SensorEntity):
    entity_description: AnalyzerSensorDescription

    def __init__(self, coordinator, description: AnalyzerSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attrs = self.entity_description.attrs
        return attrs(self.coordinator.data) if attrs else None
