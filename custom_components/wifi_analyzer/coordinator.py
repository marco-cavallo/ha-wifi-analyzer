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
"""Coordinator: scansioni, storico e analisi.

Due ritmi diversi:
- lo stato dei dispositivi si ricalcola ogni minuto, costa nulla (memoria);
- le scansioni partono a comando o ogni N ore, perché disturbano le sonde.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from . import devices as wifi_devices
from .analysis import DEFAULT_PLAN_24, Network, analyze
from .const import (
    CONF_CHANNEL_PLAN,
    CONF_OWN_SSIDS,
    CONF_PROBES,
    CONF_SCAN_HOURS,
    DEFAULT_SCAN_HOURS,
    DOMAIN,
    HISTORY_SIZE,
    PROBE_SHELLY,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .probes import Probe, ProbeError, async_discover, async_scan

_LOGGER = logging.getLogger(__name__)

# Pausa tra una sonda Shelly e la successiva: ognuna si stacca un attimo dal
# Wi-Fi per scansionare, meglio non farlo a più di una alla volta.
PAUSE_BETWEEN_PROBES = 2


@dataclass(slots=True)
class ScanProgress:
    """Avanzamento della scansione in corso, per il pannello.

    `probes` ha una voce per sonda con lo stato: waiting, scanning, done,
    error, skipped (interrotta prima di arrivarci).
    """

    running: bool = False
    cancelling: bool = False
    started: float | None = None
    started_at: str | None = None
    probes: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        done = sum(1 for p in self.probes if p["state"] in ("done", "error", "skipped"))
        current = next((p["name"] for p in self.probes if p["state"] == "scanning"), None)
        return {
            "running": self.running, "cancelling": self.cancelling,
            "total": len(self.probes), "done": done, "current": current,
            "started_at": self.started_at,
            "elapsed": round(time.monotonic() - self.started, 1) if self.started else None,
            "probes": self.probes,
        }


@dataclass(slots=True)
class AnalyzerData:
    """Tutto quello che entità e pannello mostrano."""

    probes: list[Probe] = field(default_factory=list)
    devices: list[dict[str, Any]] = field(default_factory=list)
    own_ssids: list[str] = field(default_factory=list)
    own_aps: list[dict[str, Any]] = field(default_factory=list)
    bands: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_scan: dict[str, Any] | None = None


class WifiAnalyzerCoordinator(DataUpdateCoordinator[AnalyzerData]):
    """Coordinator dell'integrazione."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.history: list[dict[str, Any]] = []
        self.progress = ScanProgress()
        # Esito dell'ultima scansione finita, per l'avviso nel pannello.
        self.last_result: dict[str, Any] | None = None
        self._lock = asyncio.Lock()
        self._cancel = asyncio.Event()
        self._unsub_schedule = None
        # Messo a True da async_set_probes: quella modifica non serve ricaricare.
        self.skip_reload = False

    # ------------------------------------------------------------ ciclo di vita

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self.history = stored.get("scans", [])[-HISTORY_SIZE:]

    @callback
    def async_schedule_scans(self) -> None:
        hours = self.config_entry.options.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS)
        if self._unsub_schedule:
            self._unsub_schedule()
            self._unsub_schedule = None
        if hours:
            self._unsub_schedule = async_track_time_interval(
                self.hass, self._scheduled_scan, timedelta(hours=hours)
            )

    async def _scheduled_scan(self, _now) -> None:
        if not self._lock.locked():
            await self.async_run_scan()

    @callback
    def async_shutdown_schedule(self) -> None:
        if self._unsub_schedule:
            self._unsub_schedule()
            self._unsub_schedule = None

    # -------------------------------------------------------------- dati

    async def _async_update_data(self) -> AnalyzerData:
        probes = await async_discover(self.hass)
        devices = wifi_devices.collect(self.hass)
        last = self.history[-1] if self.history else None
        # Access point dichiarati dai router: sono nostri per definizione.
        router_aps = last.get("own_aps", []) if last else []
        own_ssids = self._own_ssids(devices, router_aps)
        own_bssids = {
            d.bssid for d in devices if d.bssid and d.ssid and d.ssid in own_ssids
        }
        channels_hint = [
            d.channel for d in devices
            if d.channel and d.ssid in own_ssids and d.available
        ]

        networks = [Network(**n) for n in last["networks"]] if last else []
        # I BSSID visti nelle scansioni col nostro SSID sono nodi nostri anche se
        # nessun dispositivo noto ci è collegato.
        own_bssids |= {n.bssid for n in networks if n.ssid in own_ssids}
        own_bssids |= {a["bssid"] for a in router_aps if a.get("bssid")}
        channels_hint += [a["channel"] for a in router_aps if a.get("channel")]
        plan = self.config_entry.options.get(CONF_CHANNEL_PLAN, DEFAULT_PLAN_24)
        bands = analyze(
            networks, own_bssids, set(own_ssids), plan, channels_hint,
            last.get("utilization") if last else None,
        )

        return AnalyzerData(
            probes=probes,
            devices=[d.as_dict() for d in devices],
            own_ssids=own_ssids,
            own_aps=self._own_aps(devices, networks, own_bssids),
            bands=bands,
            last_scan=self._scan_summary(last),
        )

    def _own_ssids(self, devices, router_aps: list[dict[str, Any]]) -> list[str]:
        """Le reti di casa: scelte dall'utente o, di default, quelle dei
        dispositivi e quelle che i router dichiarano come proprie."""
        configured = self.config_entry.options.get(CONF_OWN_SSIDS) or []
        if configured:
            return list(configured)
        counts: dict[str, int] = {}
        for device in devices:
            if device.ssid:
                counts[device.ssid] = counts.get(device.ssid, 0) + 1
        for ap in router_aps:
            if ap.get("ssid"):
                counts[ap["ssid"]] = counts.get(ap["ssid"], 0) + 1
        return sorted(counts, key=lambda s: -counts[s])

    @staticmethod
    def _own_aps(devices, networks: list[Network], own_bssids: set[str]) -> list[dict[str, Any]]:
        """I punti di accesso di casa, con canale e dispositivi collegati."""
        aps: dict[str, dict[str, Any]] = {
            b: {"bssid": b, "ssid": None, "channel": None, "rssi": None, "devices": 0, "weak": 0}
            for b in own_bssids
        }
        for net in networks:
            if net.bssid in aps:
                ap = aps[net.bssid]
                ap["ssid"] = net.ssid
                ap["channel"] = net.channel
                ap["rssi"] = max(ap["rssi"] or -127, net.rssi)
        for device in devices:
            if device.bssid in aps:
                ap = aps[device.bssid]
                ap["devices"] += 1
                ap["ssid"] = ap["ssid"] or device.ssid
                ap["channel"] = ap["channel"] or device.channel
                if device.rssi is not None and device.rssi < -75:
                    ap["weak"] += 1
        return sorted(aps.values(), key=lambda a: (-a["devices"], a["bssid"]))

    @staticmethod
    def _scan_summary(scan: dict[str, Any] | None) -> dict[str, Any] | None:
        if not scan:
            return None
        return {
            "time": scan["time"],
            "duration": scan.get("duration"),
            "probes": scan.get("probes", []),
            "networks": len({n["bssid"] for n in scan["networks"]}),
        }

    # ------------------------------------------------------------ scansione

    async def async_set_probes(self, probe_ids: list[str]) -> None:
        """Salva le sonde scelte dal pannello, senza ricaricare l'integrazione."""
        self.skip_reload = True
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={**self.config_entry.options, CONF_PROBES: list(probe_ids)},
        )
        self.async_update_listeners()

    def selected_probes(self) -> list[Probe]:
        wanted = self.config_entry.options.get(CONF_PROBES)
        probes = self.data.probes if self.data else []
        if wanted is None:
            return probes
        return [p for p in probes if p.probe_id in wanted]

    @property
    def scanning(self) -> bool:
        return self._lock.locked()

    @callback
    def async_start_scan(self, probe_ids: list[str] | None = None) -> bool:
        """Avvia la scansione in background. False se ce n'è già una."""
        if self._lock.locked():
            return False
        self.config_entry.async_create_background_task(
            self.hass, self.async_run_scan(probe_ids), f"{DOMAIN}_scan"
        )
        return True

    @callback
    def async_cancel_scan(self) -> bool:
        """Chiede di fermare la scansione dopo la sonda in corso."""
        if not self._lock.locked():
            return False
        self._cancel.set()
        self.progress.cancelling = True
        self.async_update_listeners()
        return True

    async def async_run_scan(self, probe_ids: list[str] | None = None) -> dict[str, Any]:
        """Scansione con le sonde scelte, una alla volta.

        La scansione di una singola sonda non si può interrompere a metà
        (sono circa 3 secondi): l'interruzione vale dalla sonda successiva, e
        le reti già raccolte vengono comunque salvate.
        """
        if self._lock.locked():
            raise RuntimeError("scan_running")
        async with self._lock:
            self._cancel.clear()
            if not self.data:
                await self.async_refresh()
            probes = self.selected_probes()
            if probe_ids:
                probes = [p for p in self.data.probes if p.probe_id in probe_ids]

            self.progress = ScanProgress(
                running=True,
                started=time.monotonic(),
                started_at=dt_util.utcnow().isoformat(),
                probes=[
                    {"id": p.probe_id, "name": p.name, "area": p.area, "kind": p.kind,
                     "state": "waiting", "networks": None, "error": None, "duration": None}
                    for p in probes
                ],
            )
            self.async_update_listeners()
            networks: list[Network] = []
            utilization: list[dict[str, Any]] = []
            own_aps: list[dict[str, Any]] = []
            results: list[dict[str, Any]] = []
            cancelled = False
            try:
                for index, probe in enumerate(probes):
                    item = self.progress.probes[index]
                    if self._cancel.is_set():
                        cancelled = True
                        item["state"] = "skipped"
                        continue
                    item["state"] = "scanning"
                    self.async_update_listeners()
                    started = time.monotonic()
                    try:
                        result = await async_scan(self.hass, probe)
                        found = result.networks
                        networks.extend(found)
                        utilization.extend({**u, "probe": probe.probe_id} for u in result.utilization)
                        own_aps.extend(result.own_aps)
                        item.update(state="done", networks=len(found),
                                    duration=round(time.monotonic() - started, 1))
                        results.append({
                            **probe.as_dict(), "ok": True, "networks": len(found),
                            "bands": sorted({n.band for n in found}),
                            "duration": item["duration"],
                        })
                    except ProbeError as err:
                        _LOGGER.info("Sonda %s: %s", probe.name, err)
                        item.update(state="error", error=str(err))
                        results.append({**probe.as_dict(), "ok": False, "error": str(err)})
                    self.async_update_listeners()
                    if probe.kind == PROBE_SHELLY and index + 1 < len(probes):
                        try:
                            await asyncio.wait_for(self._cancel.wait(), PAUSE_BETWEEN_PROBES)
                        except TimeoutError:
                            pass
            finally:
                duration = round(time.monotonic() - (self.progress.started or time.monotonic()), 1)
                summary_probes = list(self.progress.probes)
                self.progress = ScanProgress()

            scan = {
                "time": dt_util.utcnow().isoformat(),
                "duration": duration,
                "probes": results,
                "networks": [n.as_dict() for n in networks],
                "utilization": utilization,
                "own_aps": own_aps,
                "cancelled": cancelled,
            }
            if networks:
                self.history.append(scan)
                self.history = self.history[-HISTORY_SIZE:]
                await self._store.async_save({"scans": self.history})
            self.last_result = {
                "time": scan["time"],
                "duration": duration,
                "cancelled": cancelled,
                "saved": bool(networks),
                "networks": len({n.bssid for n in networks}),
                "ok": sum(1 for p in summary_probes if p["state"] == "done"),
                "failed": sum(1 for p in summary_probes if p["state"] == "error"),
                "skipped": sum(1 for p in summary_probes if p["state"] == "skipped"),
                "total": len(summary_probes),
            }
            await self.async_refresh()
            return self.last_result

    def history_summary(self) -> list[dict[str, Any]]:
        """Andamento nel tempo: canale e punteggio per ogni scansione."""
        out = []
        own_ssids = set(self.data.own_ssids) if self.data else set()
        plan = self.config_entry.options.get(CONF_CHANNEL_PLAN, DEFAULT_PLAN_24)
        for scan in self.history:
            networks = [Network(**n) for n in scan["networks"]]
            own = {n.bssid for n in networks if n.ssid in own_ssids}
            bands = analyze(networks, own, own_ssids, plan)
            out.append({
                "time": scan["time"],
                "bands": {
                    band: {
                        "current": b["current"], "current_score": b["current_score"],
                        "recommended": b["recommended"],
                        "recommended_score": b["recommended_score"],
                        "neighbors": len(b["neighbors"]),
                    }
                    for band, b in bands.items() if b["probes"]
                },
            })
        return out
