# Wi-Fi Analyzer

**English** · [Italiano](README.it.md)

*Home Assistant integration that finds the best Wi-Fi channel for your home, using the devices you already have as probes.*

*By Marco Cavallo*

---

## What it is

A Wi-Fi analyzer that lives inside Home Assistant. Instead of walking around with a phone app, it asks the devices already spread across your home to look at the air from their room, then combines what they see into one picture: which channels are crowded, how strong your neighbors are, which channel is the best choice for the whole house, and how your own devices are doing.

No cloud service, no extra hardware required, no Python dependencies.

## Probes

The integration discovers its probes on its own:

| Probe | Bands | Requirements |
|---|---|---|
| **Server Wi-Fi card** (Raspberry Pi, mini PC, USB dongle) | 2.4 GHz and 5 GHz, if the card supports them | Home Assistant OS or Supervised |
| **Shelly Gen2, Gen3, Gen4** | 2.4 GHz | Configured with the official Shelly integration, mains powered |

More probes in different rooms give a better picture: the right channel is the one that works everywhere, not only next to the router. A Shelly leaves Wi-Fi for about 3 seconds while scanning, so the integration scans one probe at a time and proposes one per room by default.

## What it shows

**Channel spectrum**: every network as a curve, your own highlighted, viewable for the whole home or room by room.

**Channel quality**: a 0-100 score per channel, averaged across probes, with the worst room in the details.

**Recommendation**: the best channel and width, with a plain-language explanation. It suggests a change only when the gain is worth reconnecting every device, and warns about partially overlapping neighbors, access points of yours on overlapping channels, and DFS channels.

**Your devices**: signal of every Wi-Fi device Home Assistant knows (Shelly read directly, plus any signal sensor in dBm and the Companion app on phones), the access point each is connected to, weak and unreachable ones.

## Entities

- `sensor.*`: current and recommended channel, channel quality, neighbor networks (per band), Wi-Fi devices, weak devices, unreachable devices, last scan, probes
- `button.*`: start scan
- service `wifi_analyzer.scan`, returns a summary

## Limits

- A scan sees access points, not traffic: a quiet neighbor weighs like a busy one. The score is an estimate.
- Shelly probes only see 2.4 GHz. For 5 GHz you need a Wi-Fi card on the Home Assistant server.
- The integration does not change the channel on your router: every brand is different. It tells you what to set.

## Installation

HACS → Integrations → ⋮ → Custom repositories → `https://github.com/marco-cavallo/ha-wifi-analyzer` (category: Integration). Install, restart Home Assistant, then Settings → Devices & services → Add integration → **Wi-Fi Analyzer**.

---

Apache License 2.0 · Copyright 2026 Marco Cavallo. See [NOTICE](NOTICE): attribution must not be removed from redistributions or derivative works.
