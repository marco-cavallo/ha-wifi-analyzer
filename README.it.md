# Wi-Fi Analyzer

[English](README.md) · **Italiano**

*Integrazione per Home Assistant che trova il canale Wi-Fi migliore per la tua casa, usando come sonde i dispositivi che hai già.*

*By Marco Cavallo*

---

## Cos'è

Un analizzatore Wi-Fi dentro Home Assistant. Invece di girare per casa con un'app sul telefono, chiede ai dispositivi già sparsi nelle stanze di guardare l'aria da dove si trovano, e mette insieme quello che vedono: quali canali sono affollati, quanto sono forti i vicini, qual è il canale migliore per tutta la casa e come stanno i tuoi dispositivi.

Nessun servizio cloud, nessun hardware aggiuntivo obbligatorio, nessuna dipendenza Python.

## Sonde

L'integrazione trova le sonde da sola fra le integrazioni già configurate, e usa le loro connessioni e credenziali.

| Sonda | Reti vicine | Occupazione | Provata | Sperimentale |
|---|---|---|---|---|
| Scheda Wi-Fi del server (Raspberry Pi, mini PC, chiavetta USB) | 2,4/5 GHz | — | ✓ |  |
| Router Cudy (integrazione cudy_m3000) | 2,4 + 5 GHz | — | ✓ |  |
| Shelly Gen2/Gen3/Gen4 | 2,4 GHz | — | ✓ |  |
| UniFi Network | 2,4 + 5 GHz | ✓ |  | ✓ |
| TP-Link Omada | 2,4 + 5 GHz | ✓ |  | ✓ |
| OpenWrt (ubus) | 2,4 + 5 GHz | ✓ |  | ✓ |
| MikroTik RouterOS | 2,4 + 5 GHz | — |  | ✓ |
| FRITZ!Box | solo occupazione | ✓ |  | ✓ |
| Freebox / Iliadbox | 2,4 + 5 GHz | ✓ |  | ✓ |
| ASUS (Asuswrt, Merlin, AsusRouter) | 2,4 + 5 GHz | ✓ (SSH) |  | ✓ |
| ESPHome (con il blocco YAML qui sotto) | 2,4 GHz | — |  | ✓ |
| Tasmota ≥ 12.1 | 2,4 GHz | — |  | ✓ |
| WLED ≥ 0.14 | 2,4 GHz | — |  | ✓ |

"Sperimentale" = scritta seguendo la documentazione e il codice sorgente, non ancora provata su un apparecchio vero: segnalazioni benvenute.

Le sonde che si staccano dal Wi-Fi per scansionare (Shelly, ESPHome, Tasmota, WLED) vengono usate una alla volta; i router no: leggono dati che raccolgono da soli. Le scansioni che fanno cadere il Wi-Fi (spectrum scan di UniFi, RF scan di Omada, frequency-scan di MikroTik) non vengono mai usate.

### ESPHome

Aggiungi questo blocco al YAML del dispositivo (ESPHome ≥ 2026.10): la sonda compare da sola.

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

Se c'è già un'integrazione OpenWrt (luci, openwrt, openwrt_ubus) si usano le sue credenziali, altrimenti si aggiunge il router dalle opzioni. Con root funziona subito; con un altro utente crea `/usr/share/rpcd/acl.d/wifi-analyzer.json`, aggiungi `list read 'wifi-analyzer'` e `list write 'wifi-analyzer'` al suo `config login` in `/etc/config/rpcd` e riavvia rpcd:

```json
{
  "wifi-analyzer": {
    "description": "Wi-Fi Analyzer",
    "read": { "ubus": { "iwinfo": ["devices", "info", "survey", "scan", "assoclist"] } },
    "write": { "ubus": { "iwinfo": ["scan"] } }
  }
}
```

## Cosa mostra

**Spettro dei canali**: ogni rete come una curva, la tua in evidenza, per tutta la casa o stanza per stanza.

**Qualità dei canali**: un punteggio da 0 a 100 per canale, medio tra le sonde, con la stanza peggiore nel dettaglio.

**Consiglio**: il canale e la larghezza migliori, spiegati in parole semplici. Propone un cambio solo quando il guadagno vale il ricollegamento di tutti i dispositivi, e avvisa di vicini che si sovrappongono in parte, di tuoi access point su canali sovrapposti e dei canali DFS.

**I tuoi dispositivi**: il segnale di ogni dispositivo Wi-Fi che Home Assistant conosce (Shelly letti direttamente, più i sensori di segnale in dBm e l'app sui telefoni), l'access point a cui è collegato, quelli deboli e quelli non raggiungibili.

## Entità

- `sensor.*`: canale attuale e consigliato, qualità del canale, reti vicine (per banda), dispositivi Wi-Fi, dispositivi deboli, non raggiungibili, ultima scansione, sonde
- `button.*`: avvia scansione
- servizio `wifi_analyzer.scan`, restituisce un riepilogo

## Limiti

- La scansione vede gli access point, non il traffico: un vicino inattivo pesa come uno che sta guardando un film. Il punteggio è una stima.
- Shelly, ESPHome, Tasmota e WLED vedono solo il 2,4 GHz. Il 5 GHz arriva dai router e dalla scheda Wi-Fi del server, se dual band.
- L'integrazione non cambia il canale sul router: ogni marca è diversa. Ti dice cosa impostare.

## Installazione

HACS → Integrazioni → ⋮ → Repository personalizzati → `https://github.com/marco-cavallo/ha-wifi-analyzer` (categoria: Integrazione). Installa, riavvia Home Assistant, poi Impostazioni → Dispositivi e servizi → Aggiungi integrazione → **Wi-Fi Analyzer**.

---

Apache License 2.0 · Copyright 2026 Marco Cavallo. Vedi [NOTICE](NOTICE): l'attribuzione non va rimossa da ridistribuzioni o lavori derivati.
