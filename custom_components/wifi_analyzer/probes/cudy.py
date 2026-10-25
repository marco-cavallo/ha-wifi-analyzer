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
"""Sonda: router mesh Cudy, tramite l'integrazione cudy_m3000.

Il firmware non ha una pagina "reti vicine", ma la scansione c'è: è quella
della modalità ripetitore (WDS), che serve a scegliere la rete da estendere.
La si avvia per ogni radio e se ne legge la tabella:
- POST /admin/network/wireless/wds/doscan/<iface> con il token della pagina;
- GET  /admin/network/wireless/wds/scan?iface=<iface>&mode=ap.
Prima dell'avvio la tabella contiene i risultati vecchi, che vanno ignorati:
si legge solo dopo aver lasciato al router il tempo di finire.
Vede anche il 5 GHz, che Shelly ed ESP non vedono. Provata su M3000 fw
2.5.28: nessun pacchetto perso dai client durante la scansione, solo qualche
ritardo (fino a 0,6 s).

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import html
import re

from homeassistant.core import HomeAssistant

from ..analysis import Network, band_of
from .base import Probe, ProbeError, ScanResult, loaded_entries, norm_bssid

KIND = "cudy"
DOMAIN_CUDY = "cudy_m3000"

PATH_CONFIG = "/admin/network/wireless/wds/config"
PATH_DOSCAN = "/admin/network/wireless/wds/doscan/{iface}"
PATH_RESULTS = "/admin/network/wireless/wds/scan?embedded=&nomodal=&iface={iface}&mode=ap"

# Il router impiega ~10 s per radio; si legge quando la tabella smette di crescere.
FIRST_READ = 8
POLL_EVERY = 2
MAX_WAIT = 30

_RE_TOKEN = re.compile(r"token: '([0-9a-f]+)'")
_RE_IFACE = re.compile(r'href="#cbi-scan-collapse-ap-(wlan\d+)">\s*Connect to ([\d.]+)GHz', re.I)
_RE_CELL = re.compile(
    r'id="cbi-table-(\d+)-(bssid|ssid|channel|signal)">\s*<p class="form-control-static[^"]*">(.*?)</p>',
    re.S,
)


def _client(hass: HomeAssistant, entry_id: str):
    for entry in loaded_entries(hass, DOMAIN_CUDY):
        if entry.entry_id == entry_id:
            return getattr(getattr(entry, "runtime_data", None), "client", None)
    return None


async def async_discover(hass: HomeAssistant) -> list[Probe]:
    probes = []
    for entry in loaded_entries(hass, DOMAIN_CUDY):
        client = getattr(getattr(entry, "runtime_data", None), "client", None)
        if client is None:
            continue
        probes.append(
            Probe(
                probe_id=f"{KIND}:{entry.unique_id or entry.entry_id}",
                kind=KIND,
                name=entry.title,
                bands=("2.4", "5"),
                disruptive=False,
                entry_id=entry.entry_id,
            )
        )
    return probes


def parse_results(page: str) -> list[dict[str, str]]:
    """Righe della tabella dei risultati (una per rete)."""
    rows: dict[str, dict[str, str]] = {}
    for match in _RE_CELL.finditer(page):
        rows.setdefault(match.group(1), {})[match.group(2)] = html.unescape(match.group(3).strip())
    return [r for r in rows.values() if r.get("bssid")]


async def async_scan(hass: HomeAssistant, probe: Probe) -> ScanResult:
    client = _client(hass, probe.entry_id) if probe.entry_id else None
    if client is None:
        raise ProbeError("Integrazione Cudy non caricata")
    try:
        page = await client.async_get_html(PATH_CONFIG)
    except Exception as err:  # noqa: BLE001 - errori del client Cudy
        raise ProbeError(str(err)) from err
    ifaces = _RE_IFACE.findall(page) or [("wlan00", "2.4"), ("wlan10", "5")]

    networks: list[Network] = []
    for iface, _ghz in sorted(ifaces, key=lambda i: i[1]):
        token = _RE_TOKEN.search(page)
        if token is None:
            raise ProbeError("Pagina di scansione senza token")
        try:
            await client.async_post_action(PATH_DOSCAN.format(iface=iface), token=token.group(1))
            rows = await _async_wait_results(client, iface)
            # Il token della pagina vale per una richiesta: per la radio
            # successiva serve una pagina nuova.
            page = await client.async_get_html(PATH_CONFIG)
        except ProbeError:
            raise
        except Exception as err:  # noqa: BLE001
            raise ProbeError(str(err)) from err
        for row in rows:
            try:
                channel = int(row.get("channel", ""))
                rssi = int(row.get("signal", "").split()[0])
            except (ValueError, IndexError):
                continue
            networks.append(
                Network(
                    bssid=norm_bssid(row["bssid"]),
                    ssid=row.get("ssid", ""),
                    channel=channel,
                    rssi=rssi,
                    probe=probe.probe_id,
                    band=band_of(channel),
                )
            )
    return ScanResult(networks=networks, own_aps=_own_aps(hass, probe.entry_id))


def _own_aps(hass: HomeAssistant, entry_id: str | None) -> list[dict]:
    """Canali dei nodi del mesh, dai dati che l'integrazione Cudy ha già.

    La scansione del router non vede le sue stesse reti: senza questo il
    canale attuale del 5 GHz resterebbe sconosciuto. I BSSID dei nodi li
    riconosce l'analisi (regola dei BSSID "fratelli").
    """
    aps = []
    for entry in loaded_entries(hass, DOMAIN_CUDY):
        if entry.entry_id != entry_id:
            continue
        data = getattr(getattr(entry, "runtime_data", None), "data", None)
        for node in (getattr(data, "nodes", None) or {}).values():
            for radio in (getattr(node, "radios", None) or {}).values():
                try:
                    channel = int(radio.get("channel") or 0)
                except (TypeError, ValueError):
                    continue
                if channel and str(radio.get("disabled")) != "1":
                    aps.append({"bssid": None, "ssid": None, "channel": channel,
                                "band": band_of(channel), "name": getattr(node, "name", None),
                                # Canali permessi dal paese impostato sul router.
                                "allowed": [int(c) for c in radio.get("chanlist") or [] if str(c).isdigit()]})
    return aps


async def _async_wait_results(client, iface: str) -> list[dict[str, str]]:
    await asyncio.sleep(FIRST_READ)
    waited, last = FIRST_READ, -1
    rows: list[dict[str, str]] = []
    while waited <= MAX_WAIT:
        rows = parse_results(await client.async_get_html(PATH_RESULTS.format(iface=iface)))
        if rows and len(rows) == last:
            return rows
        last = len(rows)
        await asyncio.sleep(POLL_EVERY)
        waited += POLL_EVERY
    return rows
