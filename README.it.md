# Wi-Fi Analyzer

[English](README.md) · **Italiano**

*Integrazione per Home Assistant che trova il canale Wi-Fi migliore per la tua casa, usando come sonde i dispositivi che hai già.*

*By Marco Cavallo*

---

## Cos'è

Un analizzatore Wi-Fi dentro Home Assistant. Invece di girare per casa con un'app sul telefono, chiede ai dispositivi già sparsi nelle stanze di guardare l'aria da dove si trovano, e mette insieme quello che vedono: quali canali sono affollati, quanto sono forti i vicini, qual è il canale migliore per tutta la casa e come stanno i tuoi dispositivi.

Nessun servizio cloud, nessun hardware aggiuntivo obbligatorio, nessuna dipendenza Python.

## Sonde

L'integrazione trova le sonde da sola:

| Sonda | Bande | Requisiti |
|---|---|---|
| **Scheda Wi-Fi del server** (Raspberry Pi, mini PC, chiavetta USB) | 2,4 GHz e 5 GHz, se la scheda li supporta | Home Assistant OS o Supervised |
| **Shelly Gen2, Gen3, Gen4** | 2,4 GHz | Configurati con l'integrazione Shelly ufficiale, alimentati a rete |

Più sonde in stanze diverse danno un quadro migliore: il canale giusto è quello che va bene ovunque, non solo vicino al router. Durante la scansione uno Shelly si stacca dal Wi-Fi per circa 3 secondi, quindi l'integrazione usa una sonda alla volta e di default ne propone una per stanza.

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
- Le sonde Shelly vedono solo il 2,4 GHz. Per il 5 GHz serve una scheda Wi-Fi sul server Home Assistant.
- L'integrazione non cambia il canale sul router: ogni marca è diversa. Ti dice cosa impostare.

## Installazione

HACS → Integrazioni → ⋮ → Repository personalizzati → `https://github.com/marco-cavallo/ha-wifi-analyzer` (categoria: Integrazione). Installa, riavvia Home Assistant, poi Impostazioni → Dispositivi e servizi → Aggiungi integrazione → **Wi-Fi Analyzer**.

---

Apache License 2.0 · Copyright 2026 Marco Cavallo. Vedi [NOTICE](NOTICE): l'attribuzione non va rimossa da ridistribuzioni o lavori derivati.
