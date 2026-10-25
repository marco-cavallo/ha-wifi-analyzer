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
"""Comandi WebSocket che alimentano il pannello.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import AUTHOR, DEFAULT_SHELLY_PROBES, DOMAIN, INTEGRATION_NAME, VERSION
from .coordinator import WifiAnalyzerCoordinator
from .probes import default_probes

WS_DATA = f"{DOMAIN}/data"
WS_SCAN = f"{DOMAIN}/scan"
WS_PROGRESS = f"{DOMAIN}/progress"
WS_HISTORY = f"{DOMAIN}/history"
WS_CANCEL = f"{DOMAIN}/cancel"
WS_SET_PROBES = f"{DOMAIN}/set_probes"


def _coordinator(hass: HomeAssistant) -> WifiAnalyzerCoordinator | None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is not None:
            return coordinator
    return None


def _require(hass: HomeAssistant, connection, msg) -> WifiAnalyzerCoordinator | None:
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_loaded", "Integrazione non caricata")
    return coordinator


def _payload(coordinator: WifiAnalyzerCoordinator) -> dict[str, Any]:
    data = coordinator.data
    selected = {p.probe_id for p in coordinator.selected_probes()}
    last = coordinator.history[-1] if coordinator.history else None
    return {
        "integration": {
            "name": INTEGRATION_NAME, "version": VERSION, "author": AUTHOR,
        },
        "probes": [{**p.as_dict(), "selected": p.probe_id in selected} for p in data.probes],
        "suggested_probes": default_probes(data.probes, DEFAULT_SHELLY_PROBES),
        "last_result": coordinator.last_result,
        "devices": data.devices,
        "own_ssids": data.own_ssids,
        "own_aps": data.own_aps,
        "bands": data.bands,
        "last_scan": data.last_scan,
        # Reti per sonda: il grafico può mostrare la casa intera o una stanza.
        "networks": last["networks"] if last else [],
        "progress": coordinator.progress.as_dict(),
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_data, ws_scan, ws_progress, ws_history, ws_cancel, ws_set_probes):
        websocket_api.async_register_command(hass, command)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): WS_DATA})
@callback
def ws_data(hass, connection, msg) -> None:
    """Tutti i dati per il pannello."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], _payload(coordinator))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): WS_SCAN, vol.Optional("probes"): [str]}
)
@callback
def ws_scan(hass, connection, msg) -> None:
    """Avvia una scansione in background; il pannello segue l'avanzamento."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    if not coordinator.async_start_scan(msg.get("probes")):
        connection.send_error(msg["id"], "scan_running", "Scansione già in corso")
        return
    connection.send_result(msg["id"], {"started": True})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): WS_CANCEL})
@callback
def ws_cancel(hass, connection, msg) -> None:
    """Interrompe la scansione dopo la sonda in corso."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], {"cancelling": coordinator.async_cancel_scan()})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): WS_SET_PROBES, vol.Required("probes"): [str]}
)
@websocket_api.async_response
async def ws_set_probes(hass, connection, msg) -> None:
    """Salva le sonde scelte."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    if coordinator.scanning:
        connection.send_error(msg["id"], "scan_running", "Scansione in corso")
        return
    await coordinator.async_set_probes(msg["probes"])
    connection.send_result(msg["id"], _payload(coordinator))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): WS_PROGRESS})
@callback
def ws_progress(hass, connection, msg) -> None:
    """Avanzamento della scansione in corso."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], coordinator.progress.as_dict())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): WS_HISTORY})
@callback
def ws_history(hass, connection, msg) -> None:
    """Storico delle scansioni."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], {"history": coordinator.history_summary()})
