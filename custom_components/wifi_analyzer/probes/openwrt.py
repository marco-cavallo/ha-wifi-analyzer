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
"""Sonda: router e access point OpenWrt (>= 19.07), via ubus JSON-RPC.

Le integrazioni OpenWrt di Home Assistant non hanno un client riutilizzabile
per ubus, quindi qui ci si collega da soli a http(s)://<host>/ubus, con le
credenziali di un'integrazione già configurata (luci, openwrt, openwrt_ubus)
o con quelle inserite nelle opzioni di Wi-Fi Analyzer.

- `iwinfo.info` per i propri access point (BSSID, SSID, canale);
- `iwinfo.survey` per l'occupazione: contatori cumulativi in ms, quindi due
  letture a distanza e busy% = Δbusy / Δactive;
- `iwinfo.scan` per le reti vicine: su un AP che trasmette il kernel di
  solito la rifiuta e torna vuota, senza disturbare. Va bene così.
L'utente root ha accesso a tutto; un utente dedicato ha bisogno di un ACL
rpcd con iwinfo devices/info/survey/scan (vedi README).

Scritta sul sorgente di rpcd/iwinfo, mai provata: "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..analysis import Network, band_of, channel_from_frequency
from ..const import CONF_ROUTERS
from .base import Probe, ProbeError, ScanResult, norm_bssid, to_int

_LOGGER = logging.getLogger(__name__)

KIND = "openwrt"
NULL_SID = "0" * 32
SURVEY_GAP = 2.0
# Integrazioni da cui prendere host e credenziali: dominio -> chiave https.
SOURCES = {"luci": "ssl", "openwrt": "use_ssl", "openwrt_ubus": "use_https"}


def _probe_from(config: dict[str, Any], key: str, name: str) -> Probe:
    return Probe(
        probe_id=f"{KIND}:{config['host']}",
        kind=KIND,
        name=name,
        bands=("2.4", "5"),
        disruptive=False,
        experimental=True,
        extra={"config": config, "key": key},
    )


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes: dict[str, Probe] = {}
    for domain, ssl_key in SOURCES.items():
        for entry in hass.config_entries.async_entries(domain):
            data = entry.data
            if not data.get("host") or not data.get("password"):
                continue
            config = {
                "host": data["host"], "username": data.get("username") or "root",
                "password": data["password"], "ssl": bool(data.get(ssl_key)),
                "port": data.get("port"), "verify_ssl": bool(data.get("verify_ssl")),
            }
            probes.setdefault(config["host"], _probe_from(config, domain, f"OpenWrt {entry.title}"))
    for entry in hass.config_entries.async_entries("wifi_analyzer"):
        for router in entry.options.get(CONF_ROUTERS, []):
            if router.get("type") == KIND and router.get("host"):
                probes.setdefault(router["host"], _probe_from(router, "manual", f"OpenWrt {router['host']}"))
    return list(probes.values())


class _Ubus:
    def __init__(self, session: aiohttp.ClientSession, config: dict[str, Any]) -> None:
        scheme = "https" if config.get("ssl") else "http"
        port = f":{config['port']}" if config.get("port") else ""
        self._url = f"{scheme}://{config['host']}{port}/ubus"
        self._session = session
        self._config = config
        self._verify = bool(config.get("verify_ssl"))
        self._sid = NULL_SID

    async def _rpc(self, sid: str, obj: str, method: str, args: dict[str, Any]) -> Any:
        body = {"jsonrpc": "2.0", "id": 1, "method": "call", "params": [sid, obj, method, args]}
        async with self._session.post(self._url, json=body, ssl=self._verify, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json(content_type=None)
        if "error" in data:
            raise ProbeError(f"ubus {obj}.{method}: {data['error'].get('message')}")
        result = data.get("result") or []
        if not result or result[0] != 0:
            raise ProbeError(f"ubus {obj}.{method}: codice {result[0] if result else '?'}")
        return result[1] if len(result) > 1 else {}

    async def login(self) -> None:
        reply = await self._rpc(NULL_SID, "session", "login", {
            "username": self._config.get("username") or "root",
            "password": self._config.get("password") or "",
        })
        self._sid = reply.get("ubus_rpc_session") or NULL_SID

    async def call(self, obj: str, method: str, args: dict[str, Any] | None = None) -> Any:
        return await self._rpc(self._sid, obj, method, args or {})


def _survey_map(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(i["mhz"]): i for i in items if i.get("mhz")}


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    ubus = _Ubus(async_get_clientsession(hass, verify_ssl=False), probe.extra["config"])
    try:
        await ubus.login()
        devices = (await ubus.call("iwinfo", "devices")).get("devices", [])
    except ProbeError:
        raise
    except Exception as err:  # noqa: BLE001
        raise ProbeError(f"Router non raggiungibile: {err}") from err

    result = ScanResult()
    first_survey: dict[str, dict[int, dict[str, Any]]] = {}
    for dev in devices:
        try:
            info = await ubus.call("iwinfo", "info", {"device": dev})
        except ProbeError:
            continue
        channel = to_int(info.get("channel"))
        if str(info.get("mode", "")).lower() in ("master", "access point") and info.get("bssid") and channel:
            result.own_aps.append({
                "bssid": norm_bssid(info["bssid"]), "ssid": info.get("ssid"),
                "channel": channel, "band": band_of(channel), "name": dev,
            })
        try:
            first_survey[dev] = _survey_map((await ubus.call("iwinfo", "survey", {"device": dev})).get("results", []))
        except ProbeError:
            pass
        try:
            scan = (await ubus.call("iwinfo", "scan", {"device": dev})).get("results", [])
        except ProbeError:
            scan = []
        for item in scan:
            ch = to_int(item.get("channel")) or channel_from_frequency(to_int(item.get("mhz")) or 0)
            rssi = to_int(item.get("signal"))
            if ch and rssi is not None and item.get("bssid"):
                result.networks.append(Network(bssid=norm_bssid(item["bssid"]), ssid=item.get("ssid") or "",
                                               channel=ch, rssi=rssi, probe=probe.probe_id, band=band_of(ch)))

    if first_survey:
        await asyncio.sleep(SURVEY_GAP)
        seen: set[int] = set()
        for dev, before in first_survey.items():
            try:
                after = _survey_map((await ubus.call("iwinfo", "survey", {"device": dev})).get("results", []))
            except ProbeError:
                continue
            for mhz, now in after.items():
                old = before.get(mhz)
                if old is None or mhz in seen:
                    continue
                active = (now.get("active_time") or 0) - (old.get("active_time") or 0)
                busy = (now.get("busy_time") or 0) - (old.get("busy_time") or 0)
                ch = channel_from_frequency(mhz)
                if active > 0 and ch:
                    seen.add(mhz)
                    result.utilization.append({"band": band_of(ch), "channel": ch,
                                               "busy": round(max(0.0, min(100.0, busy * 100 / active)), 1)})
    if not result.networks and not result.utilization and not result.own_aps:
        raise ProbeError("Nessun dato: controlla i permessi rpcd dell'utente (iwinfo)")
    return result
