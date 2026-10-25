# Wi-Fi Analyzer

**English** · [Italiano](README.it.md)

*Home Assistant integration that finds the best Wi-Fi channel for your home, using the devices you already have as probes.*

*By Marco Cavallo*

---

## What it is

A Wi-Fi analyzer that lives inside Home Assistant. Instead of walking around with a phone app, it asks the devices already spread across your home to look at the air from their room, then combines what they see into one picture: which channels are crowded, how strong your neighbors are, which channel is the best choice for the whole house, and how your own devices are doing.

No cloud service, no extra hardware required, no Python dependencies.

## Probes

The integration finds its probes among the integrations you already configured, and uses their connections and credentials.

| Probe | Neighbor networks | Occupancy | Tested | Experimental |
|---|---|---|---|---|
| Server Wi-Fi card (Raspberry Pi, mini PC, USB dongle) | 2,4/5 GHz | — | ✓ |  |
| Cudy router (cudy_m3000 integration) | 2,4 + 5 GHz | — | ✓ |  |
| Shelly Gen2/Gen3/Gen4 | 2,4 GHz | — | ✓ |  |
| UniFi Network | 2,4 + 5 GHz | ✓ |  | ✓ |
| TP-Link Omada | 2,4 + 5 GHz | ✓ |  | ✓ |
| OpenWrt (ubus) | 2,4 + 5 GHz | ✓ |  | ✓ |
| MikroTik RouterOS | 2,4 + 5 GHz | — |  | ✓ |
| FRITZ!Box | occupancy only | ✓ |  | ✓ |
| Freebox / Iliadbox | 2,4 + 5 GHz | ✓ |  | ✓ |
| ASUS (Asuswrt, Merlin, AsusRouter) | 2,4 + 5 GHz | ✓ (SSH) |  | ✓ |
| ESPHome (with the YAML block below) | 2,4 GHz | — |  | ✓ |
| Tasmota ≥ 12.1 | 2,4 GHz | — |  | ✓ |
| WLED ≥ 0.14 | 2,4 GHz | — |  | ✓ |

"Experimental" = written from the documentation and source code, not yet tested on a real device: reports welcome.

Probes that leave Wi-Fi to scan (Shelly, ESPHome, Tasmota, WLED) are used one at a time; routers are not, they read data they collect anyway. Scans that take Wi-Fi down (UniFi spectrum scan, Omada RF scan, MikroTik frequency-scan) are never used.

### ESPHome

Add this block to the device YAML (ESPHome ≥ 2026.10): the probe shows up by itself.

```yaml
text_sensor:
  - platform: wifi_info
    scan_results:
      name: "Wi-Fi scan results"
      internal: true   # keeps the full scan results in memory

api:
  actions:
    - action: wifi_scan
      supports_response: only
      then:
        - wifi.roam:      # triggers a fresh scan (skipped if the signal is above -49 dBm)
        - delay: 6s
        - api.respond:
            data: !lambda |-
              auto aps = root["aps"].to<JsonArray>();
              for (auto &r : wifi::global_wifi_component->get_scan_result()) {
                auto o = aps.add<JsonObject>();
                o["ssid"] = r.get_ssid().c_str();
                const auto &m = r.get_bssid();
                char b[18];
                snprintf(b, sizeof(b), "%02X:%02X:%02X:%02X:%02X:%02X", m[0], m[1], m[2], m[3], m[4], m[5]);
                o["bssid"] = b;
                o["channel"] = r.get_channel();
                o["rssi"] = r.get_rssi();
              }
```

### OpenWrt

If an OpenWrt integration (luci, openwrt, openwrt_ubus) is already configured its credentials are used, otherwise add the router from the options. root works out of the box; for another user create `/usr/share/rpcd/acl.d/wifi-analyzer.json`, add `list read 'wifi-analyzer'` and `list write 'wifi-analyzer'` to its `config login` in `/etc/config/rpcd` and restart rpcd:

```json
{
  "wifi-analyzer": {
    "description": "Wi-Fi Analyzer",
    "read": { "ubus": { "iwinfo": ["devices", "info", "survey", "scan", "assoclist"] } },
    "write": { "ubus": { "iwinfo": ["scan"] } }
  }
}
```

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
- Shelly, ESPHome, Tasmota and WLED only see 2.4 GHz. 5 GHz comes from routers and from the server Wi-Fi card, if dual band.
- The integration does not change the channel on your router: every brand is different. It tells you what to set.

## Installation

HACS → Integrations → ⋮ → Custom repositories → `https://github.com/marco-cavallo/ha-wifi-analyzer` (category: Integration). Install, restart Home Assistant, then Settings → Devices & services → Add integration → **Wi-Fi Analyzer**.

---

Apache License 2.0 · Copyright 2026 Marco Cavallo. See [NOTICE](NOTICE): attribution must not be removed from redistributions or derivative works.
