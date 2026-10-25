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
"""Analisi dei canali a partire dalle scansioni delle sonde.

Modulo puro, senza dipendenze da Home Assistant: riceve le reti viste da ogni
sonda e restituisce punteggi per canale, canale consigliato e avvisi.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

BAND_24 = "2.4"
BAND_5 = "5"

CHANNELS_24 = list(range(1, 14))
# Canali a 20 MHz del 5 GHz in Europa (UNII-1/2/2e/3). 52-144 richiedono DFS.
CHANNELS_5 = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120,
              124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]
DFS_5 = set(range(52, 145))
# Blocchi da 80 MHz: chi usa 80 MHz occupa tutto il blocco del suo canale.
BLOCKS_80 = [(36, 48), (52, 64), (100, 112), (116, 128), (132, 144), (149, 161)]

CHANNEL_PLANS_24 = {
    "1-6-11": [1, 6, 11],
    "1-5-9-13": [1, 5, 9, 13],
}
DEFAULT_PLAN_24 = "1-6-11"

# Sotto questa soglia una rete non disturba in modo misurabile.
RSSI_FLOOR = -95
RSSI_STRONG = -50
# Punti di punteggio sotto i quali non vale la pena cambiare canale: ogni
# cambio fa ricollegare tutti i dispositivi.
MIN_GAIN = 15


@dataclass(slots=True)
class Network:
    """Una rete (BSSID) vista da una sonda."""

    bssid: str
    ssid: str
    channel: int
    rssi: int
    probe: str
    band: str = BAND_24
    own: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "bssid": self.bssid, "ssid": self.ssid, "channel": self.channel,
            "rssi": self.rssi, "probe": self.probe, "band": self.band,
            "own": self.own,
        }


def band_of(channel: int) -> str:
    return BAND_24 if channel <= 14 else BAND_5


def channel_from_frequency(freq: int) -> int | None:
    """Canale dalla frequenza in MHz (formato del Supervisor)."""
    if freq == 2484:
        return 14
    if 2412 <= freq <= 2472:
        return (freq - 2407) // 5
    if 5000 <= freq <= 5900:
        return (freq - 5000) // 5
    return None


def weight(rssi: int) -> float:
    """Quanto pesa una rete in base al segnale, tra 0 e 1.

    Curva quadratica tra -95 e -50 dBm: una rete a -50 o più forte pesa 1,
    a -70 circa 0,3, a -85 quasi nulla. Con la potenza lineare in mW una
    sola rete forte coprirebbe tutte le altre, che invece contano.
    """
    x = (rssi - RSSI_FLOOR) / (RSSI_STRONG - RSSI_FLOOR)
    x = min(max(x, 0.0), 1.0)
    return x * x


def overlap_24(a: int, b: int) -> float:
    """Sovrapposizione spettrale di due canali a 20 MHz del 2,4 GHz.

    I canali distano 5 MHz e ogni segnale occupa 20 MHz: a 4 canali di
    distanza non si toccano più. Il canale 14 (Giappone) è a 12 MHz dal 13.
    """
    fa = 2484 if a == 14 else 2407 + 5 * a
    fb = 2484 if b == 14 else 2407 + 5 * b
    return max(0.0, 1.0 - abs(fa - fb) / 20.0)


def block_80(channel: int) -> tuple[int, int] | None:
    for start, end in BLOCKS_80:
        if start <= channel <= end:
            return (start, end)
    return None


def overlap_5(a: int, b: int) -> float:
    """Sovrapposizione nel 5 GHz.

    Le scansioni non dicono la larghezza dei vicini. Stesso canale pesa 1;
    stesso blocco da 80 MHz pesa 0,5, perché un vicino a 80 MHz lo occupa
    tutto ma non sappiamo se lo usa.
    """
    if a == b:
        return 1.0
    if block_80(a) is not None and block_80(a) == block_80(b):
        return 0.5
    return 0.0


def score_from_load(load: float) -> int:
    """Punteggio 0-100: 100 canale libero, 50 come una rete forte sopra."""
    return round(100 / (1 + load))


@dataclass(slots=True)
class BandAnalysis:
    """Risultato per una banda."""

    band: str
    probes: list[str] = field(default_factory=list)
    channels: list[dict[str, Any]] = field(default_factory=list)
    neighbors: list[dict[str, Any]] = field(default_factory=list)
    own: list[dict[str, Any]] = field(default_factory=list)
    current: int | None = None
    current_score: int | None = None
    recommended: int | None = None
    recommended_score: int | None = None
    width: str | None = None
    advice: str = "no_data"
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "band": self.band, "probes": self.probes, "channels": self.channels,
            "neighbors": self.neighbors, "own": self.own,
            "current": self.current, "current_score": self.current_score,
            "recommended": self.recommended,
            "recommended_score": self.recommended_score,
            "gain": (self.recommended_score - self.current_score)
            if self.recommended_score is not None and self.current_score is not None
            else None,
            "width": self.width, "advice": self.advice, "warnings": self.warnings,
        }


def _octets(bssid: str) -> list[str]:
    return bssid.lower().split(":")


def is_sibling(bssid: str, own_bssids: set[str]) -> bool:
    """BSSID virtuale di una radio di casa.

    I router creano reti in più sulla stessa radio (backhaul mesh nascosto,
    rete ospiti) con BSSID derivati dal principale: di solito cambiano il
    primo byte (bit "locally administered") e il quarto, il resto resta
    uguale. Esempio: a0:b1:c2:11:22:33 e a2:b1:c2:21:22:33. Sono la stessa
    antenna, quindi non sono vicini che disturbano.
    """
    mine = _octets(bssid)
    if len(mine) != 6:
        return False
    for own in own_bssids:
        other = _octets(own)
        if len(other) == 6 and mine != other and all(mine[i] == other[i] for i in (1, 2, 4, 5)):
            return True
    return False


def _merge(networks: list[Network]) -> list[dict[str, Any]]:
    """Una voce per BSSID, con il segnale migliore e le sonde che la vedono."""
    merged: dict[str, dict[str, Any]] = {}
    for net in networks:
        item = merged.get(net.bssid)
        if item is None:
            merged[net.bssid] = item = {
                "bssid": net.bssid, "ssid": net.ssid, "channel": net.channel,
                "rssi": net.rssi, "own": net.own, "seen_by": {},
            }
        item["seen_by"][net.probe] = net.rssi
        if net.rssi > item["rssi"]:
            item["rssi"] = net.rssi
            item["channel"] = net.channel
    return sorted(merged.values(), key=lambda n: -n["rssi"])


def analyze_band(
    band: str,
    networks: list[Network],
    own_bssids: set[str],
    own_ssids: set[str],
    plan_24: str = DEFAULT_PLAN_24,
    own_channels_hint: list[int] | None = None,
) -> BandAnalysis:
    """Analizza una banda.

    Il carico di un canale è la media, tra le sonde, della somma dei pesi delle
    reti vicine sovrapposte: ogni sonda è un punto della casa e il canale giusto
    è quello che va bene ovunque, non solo vicino al router.
    """
    result = BandAnalysis(band=band)
    for net in networks:
        net.own = net.bssid in own_bssids or (net.ssid in own_ssids and bool(net.ssid))
    known = own_bssids | {n.bssid for n in networks if n.own}
    for net in networks:
        if not net.own and is_sibling(net.bssid, known):
            net.own = True
    nets = [n for n in networks if n.band == band]
    probes = sorted({n.probe for n in nets})
    result.probes = probes
    if not probes:
        return result

    candidates = CHANNELS_24 if band == BAND_24 else CHANNELS_5
    overlap = overlap_24 if band == BAND_24 else overlap_5

    per_probe: dict[str, dict[int, float]] = {p: dict.fromkeys(candidates, 0.0) for p in probes}
    for net in nets:
        if net.own:
            continue
        w = weight(net.rssi)
        if w <= 0:
            continue
        loads = per_probe[net.probe]
        for ch in candidates:
            ov = overlap(net.channel, ch)
            if ov:
                loads[ch] += w * ov

    merged = _merge(nets)
    result.neighbors = [n for n in merged if not n["own"]]
    result.own = [n for n in merged if n["own"]]

    if band == BAND_24:
        preferred = CHANNEL_PLANS_24.get(plan_24, CHANNEL_PLANS_24[DEFAULT_PLAN_24])
    else:
        preferred = [c for c in CHANNELS_5 if c not in DFS_5 and c != 165]

    for ch in candidates:
        loads = [per_probe[p][ch] for p in probes]
        load = sum(loads) / len(loads)
        worst = max(loads)
        result.channels.append({
            "channel": ch,
            "load": round(load, 3),
            "score": score_from_load(load),
            "worst_score": score_from_load(worst),
            "networks": sum(1 for n in result.neighbors if n["channel"] == ch),
            "preferred": ch in preferred,
            "dfs": band == BAND_5 and ch in DFS_5,
        })
    by_channel = {c["channel"]: c for c in result.channels}

    own_channels = [n["channel"] for n in result.own] + list(own_channels_hint or [])
    own_channels = [c for c in own_channels if band_of(c) == band]
    if own_channels:
        result.current = Counter(own_channels).most_common(1)[0][0]
        result.current_score = by_channel.get(result.current, {}).get("score")

    best = max(
        (by_channel[c] for c in preferred if c in by_channel),
        # A parità di punteggio meglio la stanza peggiore, poi il canale attuale.
        key=lambda c: (c["score"], c["worst_score"], c["channel"] == result.current),
    )
    result.recommended = best["channel"]
    result.recommended_score = best["score"]

    if result.current is None:
        result.advice = "set_channel"
    elif result.current == result.recommended:
        result.advice = "keep"
    elif (result.recommended_score - (result.current_score or 0)) < MIN_GAIN:
        result.advice = "keep_close"
        result.recommended = result.current
        result.recommended_score = result.current_score
    else:
        result.advice = "change"

    result.width = _width_advice(band, result)
    result.warnings = _warnings(band, result, by_channel, preferred)
    return result


def _width_advice(band: str, result: BandAnalysis) -> str:
    """Larghezza consigliata.

    Sul 2,4 GHz i 40 MHz occupano due terzi della banda: hanno senso solo se
    attorno non c'è nessuno. Sul 5 GHz 80 MHz va bene se il blocco è libero.
    """
    ch = result.recommended
    if band == BAND_24:
        busy = [n for n in result.neighbors if n["rssi"] > -85]
        return "40" if not busy else "20"
    block = block_80(ch) if ch else None
    if block is None:
        return "20"
    in_block = [n for n in result.neighbors
                if block[0] <= n["channel"] <= block[1] and n["rssi"] > -80]
    if not in_block:
        return "80"
    return "40" if len(in_block) <= 1 else "20"


def _warnings(
    band: str,
    result: BandAnalysis,
    by_channel: dict[int, dict[str, Any]],
    preferred: list[int],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    own_channels = sorted({n["channel"] for n in result.own})

    # Nodi della stessa rete su canali vicini ma diversi: il caso peggiore,
    # si disturbano senza potersi coordinare.
    if band == BAND_24 and len(own_channels) > 1:
        for i, a in enumerate(own_channels):
            for b in own_channels[i + 1:]:
                if overlap_24(a, b) > 0:
                    warnings.append({"code": "own_overlap", "channels": [a, b]})
    elif len(own_channels) > 1:
        warnings.append({"code": "own_mixed", "channels": own_channels})

    if band == BAND_24 and result.current and result.current not in preferred:
        warnings.append({"code": "off_plan", "channel": result.current})

    # Vicino forte su un canale adiacente: è peggio che sullo stesso canale,
    # perché non rispetta i turni e arriva come rumore.
    if result.current:
        for net in result.neighbors:
            if net["rssi"] >= -70 and net["channel"] != result.current:
                ov = (overlap_24 if band == BAND_24 else overlap_5)(
                    net["channel"], result.current)
                if ov > 0:
                    warnings.append({"code": "adjacent_strong", "ssid": net["ssid"],
                                     "channel": net["channel"], "rssi": net["rssi"]})
    if band == BAND_5 and result.recommended in DFS_5:
        warnings.append({"code": "dfs", "channel": result.recommended})
    return warnings


def analyze(
    networks: list[Network],
    own_bssids: set[str],
    own_ssids: set[str],
    plan_24: str = DEFAULT_PLAN_24,
    own_channels_hint: list[int] | None = None,
) -> dict[str, dict[str, Any]]:
    """Analizza tutte le bande disponibili."""
    return {
        band: analyze_band(
            band, networks, own_bssids, own_ssids, plan_24, own_channels_hint
        ).as_dict()
        for band in (BAND_24, BAND_5)
    }


def quality_of(rssi: int | None) -> str:
    """Classe di qualità del segnale di un dispositivo."""
    if rssi is None:
        return "unknown"
    if rssi >= -60:
        return "excellent"
    if rssi >= -67:
        return "good"
    if rssi >= -75:
        return "fair"
    return "weak"
