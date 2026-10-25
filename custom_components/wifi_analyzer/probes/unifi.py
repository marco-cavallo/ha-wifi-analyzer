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
"""Sonda: UniFi Network, tramite l'integrazione unifi di Home Assistant.

Non avvia scansioni: il controller raccoglie da solo le reti vicine viste
dagli access point (stat/rogueap) e l'occupazione di ogni radio
(radio_table_stats.cu_total). Lo "spectrum scan" esiste ma ferma il Wi-Fi
dell'access point, quindi qui non si usa.

Accesso: entry.runtime_data è UnifiHub, .api è un aiounifi.Controller già
autenticato; ApiRequest aggiunge da solo il prefisso del sito (e /proxy/network
sulle console UniFi OS). Verificato sul sorgente di HA 2026.10 / aiounifi 96;
mai provato su un controller vero, da qui "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from .base import BAND_BY_RADIO, Probe, ProbeError, ScanResult, loaded_entries, norm_bssid, to_int

KIND = "unifi"
# Reti viste nelle ultime ore: il default del controller (24 h) terrebbe
# anche vicini spenti da tempo.
WITHIN_HOURS = 2


def _hub(hass: HomeAssistant, entry_id: str | None):
    for entry in loaded_entries(hass, "unifi"):
        if entry_id is None or entry.entry_id == entry_id:
            return getattr(entry, "runtime_data", None)
    return None


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in loaded_entries(hass, "unifi"):
        hub = getattr(entry, "runtime_data", None)
        if getattr(hub, "api", None) is None:
            continue
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=f"UniFi {entry.title}",
                bands=("2.4", "5"),
                disruptive=False,
                experimental=True,
                entry_id=entry.entry_id,
            )
        )
    return probes


def _signal(item: dict[str, Any]) -> int | None:
    """dBm della rete vicina.

    `signal` è in dBm; `rssi` sui controller UniFi è positivo e si comporta
    come un rapporto segnale/rumore, quindi serve solo se `signal` manca.
    """
    signal = to_int(item.get("signal"))
    if signal is not None and signal < 0:
        return signal
    rssi = to_int(item.get("rssi"))
    if rssi is not None:
        noise = to_int(item.get("noise")) or -95
        return rssi + noise if rssi > 0 else rssi
    return None


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    hub = _hub(hass, probe.entry_id)
    api = getattr(hub, "api", None)
    if api is None:
        raise ProbeError("Integrazione UniFi non caricata")
    try:
        from aiounifi.models.api import ApiRequest

        response = await api.request(
            ApiRequest(method="post", path="/stat/rogueap", data={"within": WITHIN_HOURS})
        )
    except Exception as err:  # noqa: BLE001 - aiounifi solleva tipi diversi per versione
        raise ProbeError(f"Reti vicine non disponibili: {err}") from err

    result = ScanResult()
    for item in (response or {}).get("data", []):
        channel = to_int(item.get("channel"))
        rssi = _signal(item)
        bssid = norm_bssid(item.get("bssid"))
        if not channel or rssi is None or not bssid:
            continue
        result.networks.append(
            Network(bssid=bssid, ssid=item.get("essid") or "", channel=channel,
                    rssi=rssi, probe=probe.probe_id, band=band_of(channel))
        )

    # Dagli access point di casa: occupazione per radio e BSSID propri.
    devices = getattr(getattr(api, "devices", None), "values", lambda: [])()
    for device in devices:
        raw: dict[str, Any] = getattr(device, "raw", {}) or {}
        name = raw.get("name") or raw.get("mac")
        for radio in raw.get("radio_table_stats") or []:
            band = BAND_BY_RADIO.get(radio.get("radio"))
            channel = to_int(radio.get("channel"))
            busy = radio.get("cu_total")
            if band and channel and busy is not None:
                result.utilization.append(
                    {"band": band, "channel": channel, "busy": float(busy), "ap": name}
                )
        for vap in raw.get("vap_table") or []:
            channel = to_int(vap.get("channel"))
            if vap.get("bssid") and channel:
                result.own_aps.append({
                    "bssid": norm_bssid(vap["bssid"]), "ssid": vap.get("essid"),
                    "channel": channel, "band": band_of(channel), "name": name,
                })
    return result
