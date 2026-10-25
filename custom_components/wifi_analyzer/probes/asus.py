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
"""Sonda: router ASUS (Asuswrt, Merlin), tramite asuswrt o AsusRouter (HACS).

Due strade, secondo come l'utente ha configurato l'integrazione:
- SSH/telnet (integrazione asuswrt, protocollo ssh/telnet): si usano i
  comandi Broadcom `wl` sulla connessione già aperta:
    nvram get wl_ifnames                  radio, in ordine (2,4 / 5 / 5-2 o 6)
    wl -i <if> chanspec / bssid           canale e BSSID propri
    wl -i <if> chanim_stats               occupazione (tx+inbss+obss+nocat)
    wl -i <if> scan ; wl -i <if> scanresults   reti vicine in dBm
  La connessione ha un timeout fisso di 9 s per comando: scan e lettura sono
  due comandi separati.
- HTTP (asuswrt in http/https, o AsusRouter): la "site survey" del router
  (servizio restart_wlcscan, poi hook get_ap_info()), che dà la qualità in %
  invece dei dBm; occupazione non disponibile.
Mai provata su un router vero: "sperimentale".

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import unquote

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from .base import Probe, ProbeError, ScanResult, loaded_entries, norm_bssid, to_int

_LOGGER = logging.getLogger(__name__)

KIND = "asus"
SCAN_WAIT = 5
SURVEY_MAX_WAIT = 40


def _ssh(entry):
    """Connessione SSH/telnet di aioasuswrt, se l'integrazione la usa."""
    bridge = getattr(getattr(entry, "runtime_data", None), "_api", None)
    lib = getattr(bridge, "_api", None)
    connection = getattr(lib, "connection", None)
    return connection if hasattr(connection, "async_run_command") else None


def _http(hass: HomeAssistant, entry):
    """Client asusrouter (HTTP) dall'integrazione core o da AsusRouter (HACS)."""
    if entry.domain == "asusrouter":
        device = ((hass.data.get("asusrouter") or {}).get(entry.entry_id) or {}).get("asusrouter")
        return getattr(device, "api", None)
    bridge = getattr(getattr(entry, "runtime_data", None), "_api", None)
    lib = getattr(bridge, "_api", None)
    return lib if hasattr(lib, "async_api_hook") else None


def _entries(hass: HomeAssistant):
    return loaded_entries(hass, "asuswrt") + loaded_entries(hass, "asusrouter")


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in _entries(hass):
        if _ssh(entry) is None and _http(hass, entry) is None:
            continue
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=f"ASUS {entry.title}",
                bands=("2.4", "5"),
                disruptive=False,
                experimental=True,
                entry_id=entry.entry_id,
            )
        )
    return probes


def parse_scanresults(lines: list[str], probe_id: str) -> list[Network]:
    """Record di `wl scanresults`: iniziano con 'SSID:'."""
    networks, cur = [], {}
    def flush():
        ch = cur.get("primary") or cur.get("channel")
        if cur.get("bssid") and ch and cur.get("rssi") is not None:
            networks.append(Network(bssid=norm_bssid(cur["bssid"]), ssid=cur.get("ssid", ""), channel=ch,
                                    rssi=cur["rssi"], probe=probe_id, band=band_of(ch)))
    for line in lines:
        if line.startswith("SSID:"):
            flush()
            cur = {"ssid": line[5:].strip().strip('"')}
            continue
        if m := re.search(r"RSSI:\s*(-?\d+)", line):
            cur["rssi"] = int(m.group(1))
        if m := re.search(r"Channel:\s*(\d+)", line):
            cur["channel"] = int(m.group(1))
        if m := re.search(r"BSSID:\s*([0-9A-Fa-f:]{17})", line):
            cur["bssid"] = m.group(1)
        if m := re.search(r"Primary channel:\s*(\d+)", line):
            cur["primary"] = int(m.group(1))
    flush()
    return networks


def parse_chanim(lines: list[str]) -> float | None:
    """Occupazione da `wl chanim_stats`: colonne per nome, versioni diverse."""
    header = next((i for i, line in enumerate(lines) if line.strip().startswith("chanspec")), None)
    if header is None or header + 1 >= len(lines):
        return None
    names = lines[header].split()
    values = lines[header + 1].split()
    row = dict(zip(names, values))
    if "busy" in row and to_int(row["busy"]) is not None:
        return float(to_int(row["busy"]))
    parts = [to_int(row.get(k)) for k in ("tx", "inbss", "obss", "nocat")]
    if all(p is None for p in parts):
        return None
    return float(min(100, sum(p or 0 for p in parts)))


async def _scan_ssh(connection, probe: Probe) -> ScanResult:
    async def run(cmd: str) -> list[str]:
        return [line.rstrip() for line in await connection.async_run_command(cmd) or []]

    result = ScanResult()
    ifnames = " ".join(await run("nvram get wl_ifnames")).split()
    for unit, ifname in enumerate(ifnames):
        chanspec = " ".join(await run(f"wl -i {ifname} chanspec"))
        channel = to_int(chanspec)
        if not channel:
            continue
        band = band_of(channel)
        bssid = " ".join(await run(f"wl -i {ifname} bssid")).strip()
        ssid = " ".join(await run(f"nvram get wl{unit}_ssid")).strip()
        if bssid:
            result.own_aps.append({"bssid": norm_bssid(bssid), "ssid": ssid, "channel": channel,
                                   "band": band, "name": ifname})
        busy = parse_chanim(await run(f"wl -i {ifname} chanim_stats"))
        if busy is not None:
            result.utilization.append({"band": band, "channel": channel, "busy": busy})
        await run(f"wl -i {ifname} scan")
        await asyncio.sleep(SCAN_WAIT)
        result.networks.extend(parse_scanresults(await run(f"wl -i {ifname} scanresults"), probe.probe_id))
    return result


def _quality_to_dbm(quality: int) -> int:
    """Inverso della scala qualità della site survey ASUS."""
    if quality >= 100:
        return -50
    if quality > 26:
        return round(-80 + (quality - 24) * 30 / 76)
    return round(-90 + quality * 10 / 26)


async def _scan_http(api, probe: Probe) -> ScanResult:
    await api.async_run_service("restart_wlcscan")
    rows: list[Any] = []
    waited = 0
    while waited < SURVEY_MAX_WAIT:
        await asyncio.sleep(3)
        waited += 3
        data = await api.async_api_hook("get_ap_info()")
        rows = (data or {}).get("get_ap_info") or []
        if rows:
            break
    result = ScanResult()
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            continue
        channel = to_int(row[2])
        quality = to_int(row[5])
        if channel and quality is not None and row[6]:
            result.networks.append(Network(bssid=norm_bssid(row[6]), ssid=unquote(str(row[1])), channel=channel,
                                           rssi=_quality_to_dbm(quality), probe=probe.probe_id, band=band_of(channel)))
    return result


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    entry = next((e for e in _entries(hass) if e.entry_id == probe.entry_id), None)
    if entry is None:
        raise ProbeError("Integrazione ASUS non caricata")
    try:
        if (connection := _ssh(entry)) is not None:
            result = await _scan_ssh(connection, probe)
        elif (api := _http(hass, entry)) is not None:
            result = await _scan_http(api, probe)
        else:
            raise ProbeError("Nessuna connessione utilizzabile verso il router")
    except ProbeError:
        raise
    except Exception as err:  # noqa: BLE001
        raise ProbeError(str(err)) from err
    if not result.networks and not result.utilization:
        raise ProbeError("Il router non ha restituito dati")
    return result
