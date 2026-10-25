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
"""Entità base di Wi-Fi Analyzer.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AUTHOR, DOMAIN, INTEGRATION_NAME, VERSION
from .coordinator import WifiAnalyzerCoordinator


class WifiAnalyzerEntity(CoordinatorEntity[WifiAnalyzerCoordinator]):
    """Tutte le entità stanno su un unico dispositivo di servizio."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WifiAnalyzerCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=INTEGRATION_NAME,
            manufacturer=AUTHOR,
            model=INTEGRATION_NAME,
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )
