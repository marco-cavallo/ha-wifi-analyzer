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
"""Integrazione Wi-Fi Analyzer.

Usa i dispositivi che ci sono già in casa (scheda Wi-Fi del server, Shelly)
come sonde per vedere i canali occupati e consigliare quello migliore.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError

from . import websocket_api as analyzer_ws
from .const import (
    CONF_PANEL,
    DEFAULT_PANEL,
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_MODULE_IMPORT_URL,
    PANEL_MODULE_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
)
from .coordinator import WifiAnalyzerCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

type WifiAnalyzerConfigEntry = ConfigEntry[WifiAnalyzerCoordinator]

SERVICE_SCAN = "scan"


async def async_setup_entry(hass: HomeAssistant, entry: WifiAnalyzerConfigEntry) -> bool:
    """Configura l'integrazione."""
    coordinator = WifiAnalyzerCoordinator(hass, entry)
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    coordinator.async_schedule_scans()
    entry.async_on_unload(coordinator.async_shutdown_schedule)

    analyzer_ws.async_register(hass)
    _async_register_services(hass)
    await _async_setup_panel(hass, entry.options.get(CONF_PANEL, DEFAULT_PANEL))

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SCAN):
        return

    async def _scan(call: ServiceCall):
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            try:
                return await entry.runtime_data.async_run_scan()
            except RuntimeError as err:
                raise HomeAssistantError("Scansione già in corso") from err
        return {}

    hass.services.async_register(
        DOMAIN, SERVICE_SCAN, _scan, supports_response=SupportsResponse.OPTIONAL
    )


async def _async_setup_panel(hass: HomeAssistant, enabled: bool) -> None:
    """Registra (o rimuove) il pannello nella barra laterale."""
    registered = PANEL_URL_PATH in hass.data.get("frontend_panels", {})

    if not enabled:
        if registered:
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
        return

    if registered:
        return

    if not hass.data.get(f"{DOMAIN}_static_registered"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    PANEL_MODULE_URL,
                    hass.config.path(f"custom_components/{DOMAIN}/panel/panel.js"),
                    False,  # il file cambia con l'integrazione: niente cache lunga
                )
            ]
        )
        hass.data[f"{DOMAIN}_static_registered"] = True

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        module_url=PANEL_MODULE_IMPORT_URL,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=True,
        config={},
    )


async def async_unload_entry(hass: HomeAssistant, entry: WifiAnalyzerConfigEntry) -> bool:
    """Rimuove l'integrazione."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        if PANEL_URL_PATH in hass.data.get("frontend_panels", {}):
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
        hass.services.async_remove(DOMAIN, SERVICE_SCAN)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: WifiAnalyzerConfigEntry) -> None:
    """Ricarica quando cambiano le opzioni.

    La scelta delle sonde dal pannello non ricarica: interromperebbe il
    pannello aperto per una modifica che il coordinator legge già al volo.
    """
    coordinator = entry.runtime_data
    if coordinator.skip_reload:
        coordinator.skip_reload = False
        return
    await hass.config_entries.async_reload(entry.entry_id)
