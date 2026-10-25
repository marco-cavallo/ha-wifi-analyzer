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
"""Sonda: MikroTik RouterOS, con le credenziali dell'integrazione mikrotik.

Si apre una connessione API separata (librouteros, la stessa libreria
dell'integrazione): quella dell'integrazione non è protetta per l'uso da più
thread e in caso di errore ripete il comando, cosa da evitare con le scansioni.

Cosa si legge senza disturbare:
- canale e BSSID delle proprie interfacce Wi-Fi (pacchetto wifi di RouterOS 7
  oppure wireless classico);
- reti vicine solo col pacchetto wireless classico, con `scan background=yes`
  (documentato come non disturbante su AP a canale fisso).
Volutamente NON si usano `/interface/wifi/scan` e `frequency-scan` di
RouterOS 7: la documentazione dice che scollegano i client.

Scritta sulla documentazione MikroTik e su librouteros 4.2, mai provata:
"sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of, channel_from_frequency
from .base import Probe, ProbeError, ScanResult, norm_bssid, to_int

KIND = "mikrotik"
SCAN_SECONDS = 5


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in hass.config_entries.async_entries("mikrotik"):
        if not entry.data.get("host"):
            continue
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=f"MikroTik {entry.title}",
                bands=("2.4", "5"),
                disruptive=False,
                experimental=True,
                entry_id=entry.entry_id,
                extra={"config": dict(entry.data)},
            )
        )
    return probes


def _channel(value: Any) -> int | None:
    """Canale da stringhe RouterOS come "2412/20-Ce/gn" o "5180/ax/80"."""
    freq = to_int(value)
    if freq and freq > 1000:
        return channel_from_frequency(freq)
    return freq


def _scan_sync(config: dict[str, Any], probe_id: str) -> ScanResult:
    import librouteros

    kwargs: dict[str, Any] = {
        "host": config["host"], "username": config.get("username", "admin"),
        "password": config.get("password", ""), "timeout": SCAN_SECONDS + 10,
    }
    if config.get("port"):
        kwargs["port"] = int(config["port"])
    if config.get("verify_ssl"):
        import ssl

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl_wrapper"] = ctx.wrap_socket
    try:
        api = librouteros.connect(**kwargs)
    except Exception as err:  # noqa: BLE001
        raise ProbeError(f"Connessione al router non riuscita: {err}") from err

    result = ScanResult()
    try:
        for path in ("/interface/wifi/print", "/interface/wireless/print"):
            try:
                interfaces = list(api(path))
            except Exception:  # noqa: BLE001 - pacchetto non installato
                continue
            legacy = "wireless" in path
            for iface in interfaces:
                if str(iface.get("disabled")).lower() in ("true", "yes"):
                    continue
                channel = _channel(iface.get("frequency") or iface.get("channel") or iface.get(".about"))
                mac = iface.get("mac-address")
                ssid = iface.get("ssid") or iface.get("configuration.ssid")
                if mac and channel:
                    result.own_aps.append({"bssid": norm_bssid(mac), "ssid": ssid, "channel": channel,
                                           "band": band_of(channel), "name": iface.get("name")})
                if legacy and str(iface.get("mode", "")).startswith("ap"):
                    try:
                        rows = list(api("/interface/wireless/scan", number=iface.get("name"),
                                        duration=str(SCAN_SECONDS), background="yes"))
                    except Exception:  # noqa: BLE001
                        rows = []
                    for row in rows:
                        ch = _channel(row.get("channel"))
                        rssi = to_int(row.get("sig"))
                        if ch and rssi is not None and row.get("address"):
                            result.networks.append(Network(bssid=norm_bssid(row["address"]), ssid=row.get("ssid") or "",
                                                           channel=ch, rssi=rssi, probe=probe_id, band=band_of(ch)))
    finally:
        try:
            api.close()
        except Exception:  # noqa: BLE001
            pass
    if not result.networks and not result.own_aps:
        raise ProbeError("Nessuna interfaccia Wi-Fi trovata sul router")
    return result


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    return await hass.async_add_executor_job(_scan_sync, probe.extra["config"], probe.probe_id)
