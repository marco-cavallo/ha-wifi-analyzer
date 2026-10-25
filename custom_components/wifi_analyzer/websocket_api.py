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

from .const import AUTHOR, DOMAIN, INTEGRATION_NAME, VERSION
from .coordinator import WifiAnalyzerCoordinator

WS_DATA = f"{DOMAIN}/data"
WS_SCAN = f"{DOMAIN}/scan"
WS_PROGRESS = f"{DOMAIN}/progress"
WS_HISTORY = f"{DOMAIN}/history"


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
    for command in (ws_data, ws_scan, ws_progress, ws_history):
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
@websocket_api.async_response
async def ws_scan(hass, connection, msg) -> None:
    """Esegue una scansione e risponde quando è finita."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    try:
        await coordinator.async_run_scan(msg.get("probes"))
    except RuntimeError:
        connection.send_error(msg["id"], "scan_running", "Scansione già in corso")
        return
    except Exception as err:  # noqa: BLE001 - il pannello deve sempre ricevere una risposta
        connection.send_error(msg["id"], "scan_failed", str(err))
        return
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
