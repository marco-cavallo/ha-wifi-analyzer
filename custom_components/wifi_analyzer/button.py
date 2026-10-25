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
"""Pulsante per avviare una scansione.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import WifiAnalyzerEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ScanButton(entry.runtime_data, "scan")])


class ScanButton(WifiAnalyzerEntity, ButtonEntity):
    """Avvia una scansione con le sonde scelte."""

    async def async_press(self) -> None:
        try:
            await self.coordinator.async_run_scan()
        except RuntimeError as err:
            raise HomeAssistantError("Scansione già in corso") from err
