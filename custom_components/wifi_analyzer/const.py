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
"""Costanti dell'integrazione Wi-Fi Analyzer.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "wifi_analyzer"
INTEGRATION_NAME: Final = "Wi-Fi Analyzer"
AUTHOR: Final = "Marco Cavallo"
VERSION: Final = "0.1.0"

CONF_PROBES: Final = "probes"
CONF_OWN_SSIDS: Final = "own_ssids"
CONF_SCAN_HOURS: Final = "scan_hours"
CONF_CHANNEL_PLAN: Final = "channel_plan"
CONF_PANEL: Final = "panel"

# 0 = solo a comando. Ogni scansione disturba per qualche secondo le sonde
# Shelly, quindi niente scansioni frequenti di default.
DEFAULT_SCAN_HOURS: Final = 0
DEFAULT_PANEL: Final = True
# Quante sonde Shelly proporre di default: una per stanza, non tutte.
DEFAULT_SHELLY_PROBES: Final = 6

# Scansioni conservate per lo storico.
HISTORY_SIZE: Final = 30
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.scans"

# Una scansione Shelly dura circa 3 s; oltre questo tempo la sonda è persa.
SCAN_TIMEOUT: Final = 20

PROBE_SHELLY: Final = "shelly"
PROBE_HOST: Final = "host"

# Integrazioni i cui sensori in dBm non sono Wi-Fi (Zigbee, Z-Wave, Bluetooth).
NON_WIFI_PLATFORMS: Final = frozenset({
    "zha", "zwave_js", "bthome", "xiaomi_ble", "ibeacon", "private_ble_device",
    "bluetooth_le_tracker", "ble_monitor", "switchbot", "govee_ble", "inkbird",
    "sensorpush", "oralb", "thermobeacon", "ruuvitag_ble", "matter", "thread",
    "deconz", "zigbee2mqtt",
})
# Parole che nel nome di un sensore indicano rete cellulare o Bluetooth.
NON_WIFI_WORDS: Final = ("sim", "cell", "lte", "5g", "ble", "bluetooth", "lqi", "zigbee")

PANEL_URL_PATH: Final = "wifi-analyzer"
PANEL_TITLE: Final = INTEGRATION_NAME
PANEL_ICON: Final = "mdi:wifi-star"
PANEL_COMPONENT: Final = "wifi-analyzer-panel"
PANEL_MODULE_URL: Final = f"/{DOMAIN}_panel/panel.js"
# La query string la ignora il server ma non il browser: cambiando versione
# il pannello si ricarica da solo, senza ricaricamento forzato.
PANEL_MODULE_IMPORT_URL: Final = f"{PANEL_MODULE_URL}?v={VERSION}"
