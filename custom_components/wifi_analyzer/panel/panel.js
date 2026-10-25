/*
 * Copyright 2026 Marco Cavallo
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/*
 * Wi-Fi Analyzer - pannello laterale
 * By Marco Cavallo
 *
 * Custom element vanilla: nessuna dipendenza esterna, nessuno step di build.
 * Parla con l'integrazione tramite i suoi comandi WebSocket.
 *
 * I nomi delle reti (SSID) arrivano dai vicini: sono dati non fidati e passano
 * sempre da esc() prima di finire nell'HTML.
 */

const DOMAIN = "wifi_analyzer";

// ---------------------------------------------------------------- traduzioni
const I18N = {
  en: {
    title: "Wi-Fi Analyzer", openMenu: "Open the sidebar",
    scan: "Start scan", scanning: "Scanning", scanOf: "{done} of {total}",
    lastScan: "Last scan", never: "No scan yet", probesN: "{n} probes", networksN: "{n} networks",
    wholeHome: "Whole home", band24: "2.4 GHz", band5: "5 GHz",
    current: "Current channel", recommended: "Recommended", neighbors: "Neighbor networks",
    devices: "Wi-Fi devices", weakN: "{n} weak", offlineN: "{n} unreachable", allGood: "all reachable",
    strongest: "strongest {v} dBm", none: "none",
    pts: "{v} pts", gain: "+{v} points", alreadyBest: "already the best", width: "Width {v} MHz",
    spectrum: "Channel spectrum", spectrumSub: "Every network is a curve: the higher, the stronger it reaches you.",
    yours: "Your network", others: "Neighbors", recommendedShort: "recommended", currentShort: "current",
    scores: "Channel quality", scoresSub: "100 = free channel. Average across probes; the tooltip also shows the worst room.",
    channel: "Channel", score: "Quality", worst: "Worst room", networksOn: "Networks on the channel",
    signal: "Signal", seenBy: "Seen by", bssid: "BSSID", ssid: "Network", hidden: "(hidden)",
    neighborList: "Neighbor networks", ownAps: "Your access points", apDevices: "devices",
    devicesTitle: "Your devices", devicesSub: "Signal as seen by each device, from the data Home Assistant already has.",
    all: "All", weak: "Weak", offline: "Unreachable", search: "Search…",
    q_excellent: "Excellent", q_good: "Good", q_fair: "Fair", q_weak: "Weak", q_unknown: "No signal data",
    node: "Access point", area: "Area", source: "Source",
    probes: "Probes", probeOk: "{n} networks · {s} s", probeOff: "not selected", probeHost: "Server Wi-Fi card",
    probeShelly: "Shelly", noBand: "No probe sees this band. A Wi-Fi card on the server (USB dongle or Raspberry Pi) adds 5 GHz.",
    empty: "Start the first scan: each probe looks at the air from its room.",
    a_keep: "Your channel is already the best choice", a_keep_close: "Stay where you are",
    a_change: "Move to channel {ch}", a_set_channel: "Use channel {ch}", a_no_data: "No data yet",
    d_keep: "Channel {ch} has the least interference across the house.",
    d_keep_close: "Channel {best} would be slightly better (+{gain} points), not enough to justify reconnecting every device.",
    d_change: "Channel {ch} scores {to} against {from} of channel {cur}: it is worth changing it on the router.",
    d_set_channel: "No device of yours was found on this band: if you use it, channel {ch} is the freest.",
    w_own_overlap: "Your access points use overlapping channels ({a} and {b}): put them all on the same channel.",
    w_own_mixed: "Your access points are on different channels ({list}).",
    w_off_plan: "Channel {ch} overlaps two non-overlapping channels: prefer the recommended set.",
    w_adjacent_strong: "“{ssid}” on channel {ch} ({rssi} dBm) partially overlaps yours: overlap is worse than sharing.",
    w_dfs: "Channel {ch} is DFS: the router may leave it for a minute if it detects radar.",
    widthHint24: "On 2.4 GHz use 20 MHz: 40 MHz takes two thirds of the band.",
    error: "Error", retry: "Retry", loading: "Loading…",
    tableView: "Table", chartView: "Chart", by: "By",
    stop: "Stop", stopping: "Stopping…", stopHint: "Stops after the probe being scanned",
    scanRunning: "Scan in progress", scanDone: "Scan complete", scanStopped: "Scan stopped", scanFailed: "No probe answered",
    scanSub: "{done} of {total} probes · {elapsed} s", remaining: "about {s} s left",
    resultSub: "at {time} · {networks} networks · {ok} of {total} probes in {duration} s",
    resultStopped: "at {time} · {ok} of {total} probes · {networks} networks saved", notSaved: "nothing saved",
    failedN: "{n} probes did not answer",
    st_waiting: "Waiting", st_scanning: "Scanning…", st_done: "{n} networks · {s} s", st_error: "Error", st_skipped: "Skipped",
    close: "Close",
    probesSub: "Choose which devices scan. A Shelly leaves Wi-Fi for about 3 seconds during its own scan.",
    selAll: "All", selSuggested: "One per room", selNone: "None",
    selCount: "{n} of {total} selected · scan takes about {s} s", noProbesSelected: "No probe selected: choose at least one below.",
  },
  it: {
    title: "Analisi Wi-Fi", openMenu: "Apri il menu laterale",
    scan: "Avvia scansione", scanning: "Scansione in corso", scanOf: "{done} di {total}",
    lastScan: "Ultima scansione", never: "Nessuna scansione", probesN: "{n} sonde", networksN: "{n} reti",
    wholeHome: "Tutta la casa", band24: "2,4 GHz", band5: "5 GHz",
    current: "Canale attuale", recommended: "Consigliato", neighbors: "Reti vicine",
    devices: "Dispositivi Wi-Fi", weakN: "{n} deboli", offlineN: "{n} non raggiungibili", allGood: "tutti raggiungibili",
    strongest: "la più forte {v} dBm", none: "nessuna",
    pts: "{v} punti", gain: "+{v} punti", alreadyBest: "già il migliore", width: "Larghezza {v} MHz",
    spectrum: "Spettro dei canali", spectrumSub: "Ogni rete è una curva: più è alta, più forte arriva da te.",
    yours: "La tua rete", others: "Vicini", recommendedShort: "consigliato", currentShort: "attuale",
    scores: "Qualità dei canali", scoresSub: "100 = canale libero. Media tra le sonde; nel dettaglio anche la stanza peggiore.",
    channel: "Canale", score: "Qualità", worst: "Stanza peggiore", networksOn: "Reti sul canale",
    signal: "Segnale", seenBy: "Vista da", bssid: "BSSID", ssid: "Rete", hidden: "(nascosta)",
    neighborList: "Reti vicine", ownAps: "I tuoi access point", apDevices: "dispositivi",
    devicesTitle: "I tuoi dispositivi", devicesSub: "Il segnale come lo vede ogni dispositivo, dai dati che Home Assistant ha già.",
    all: "Tutti", weak: "Deboli", offline: "Non raggiungibili", search: "Cerca…",
    q_excellent: "Ottimo", q_good: "Buono", q_fair: "Discreto", q_weak: "Debole", q_unknown: "Senza dato",
    node: "Access point", area: "Stanza", source: "Origine",
    probes: "Sonde", probeOk: "{n} reti · {s} s", probeOff: "non selezionata", probeHost: "Scheda Wi-Fi del server",
    probeShelly: "Shelly", noBand: "Nessuna sonda vede questa banda. Una scheda Wi-Fi sul server (chiavetta USB o Raspberry Pi) aggiunge il 5 GHz.",
    empty: "Avvia la prima scansione: ogni sonda guarda l'aria dalla sua stanza.",
    a_keep: "Il tuo canale è già la scelta migliore", a_keep_close: "Resta dove sei",
    a_change: "Passa al canale {ch}", a_set_channel: "Usa il canale {ch}", a_no_data: "Ancora nessun dato",
    d_keep: "Il canale {ch} è quello con meno interferenze in tutta la casa.",
    d_keep_close: "Il canale {best} sarebbe appena migliore (+{gain} punti): non abbastanza da far ricollegare tutti i dispositivi.",
    d_change: "Il canale {ch} vale {to} contro {from} del canale {cur}: conviene cambiarlo sul router.",
    d_set_channel: "Non ho trovato tuoi dispositivi su questa banda: se la usi, il canale {ch} è il più libero.",
    w_own_overlap: "I tuoi access point usano canali sovrapposti ({a} e {b}): mettili tutti sullo stesso canale.",
    w_own_mixed: "I tuoi access point sono su canali diversi ({list}).",
    w_off_plan: "Il canale {ch} si sovrappone a due canali puliti: meglio uno del gruppo consigliato.",
    w_adjacent_strong: "«{ssid}» sul canale {ch} ({rssi} dBm) si sovrappone in parte al tuo: sovrapporsi è peggio che condividere.",
    w_dfs: "Il canale {ch} è DFS: il router può lasciarlo per un minuto se rileva un radar.",
    widthHint24: "Sul 2,4 GHz usa 20 MHz: i 40 MHz occupano due terzi della banda.",
    error: "Errore", retry: "Riprova", loading: "Caricamento…",
    tableView: "Tabella", chartView: "Grafico", by: "By",
    stop: "Interrompi", stopping: "Interruzione…", stopHint: "Si ferma dopo la sonda in corso",
    scanRunning: "Scansione in corso", scanDone: "Scansione completata", scanStopped: "Scansione interrotta", scanFailed: "Nessuna sonda ha risposto",
    scanSub: "{done} di {total} sonde · {elapsed} s", remaining: "circa {s} s alla fine",
    resultSub: "alle {time} · {networks} reti · {ok} di {total} sonde in {duration} s",
    resultStopped: "alle {time} · {ok} di {total} sonde · {networks} reti salvate", notSaved: "nessun dato salvato",
    failedN: "{n} sonde non hanno risposto",
    st_waiting: "In attesa", st_scanning: "Sta scansionando…", st_done: "{n} reti · {s} s", st_error: "Errore", st_skipped: "Saltata",
    close: "Chiudi",
    probesSub: "Scegli quali dispositivi fanno la scansione. Uno Shelly si stacca dal Wi-Fi per circa 3 secondi durante la sua.",
    selAll: "Tutte", selSuggested: "Una per stanza", selNone: "Nessuna",
    selCount: "{n} di {total} selezionate · scansione di circa {s} s", noProbesSelected: "Nessuna sonda selezionata: scegline almeno una qui sotto.",
  },
};

const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

// ---------------------------------------------------------------- icone (mdi)
const P = {
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  radar: "M19.07,4.93L17.66,6.34C19.1,7.79 20,9.79 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12C4,7.92 7.05,4.56 11,4.07V6.09C8.16,6.57 6,9.03 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12C18,10.34 17.33,8.84 16.24,7.76L14.83,9.17C15.55,9.9 16,10.9 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12C8,10.14 9.28,8.59 11,8.14V10.28C10.4,10.63 10,11.26 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12C14,11.26 13.6,10.62 13,10.28V2H12A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12C22,9.24 20.88,6.74 19.07,4.93Z",
  ap: "M4.93,4.93C3.12,6.74 2,9.24 2,12C2,14.76 3.12,17.26 4.93,19.07L6.34,17.66C4.89,16.22 4,14.22 4,12C4,9.79 4.89,7.78 6.34,6.34L4.93,4.93M19.07,4.93L17.66,6.34C19.11,7.78 20,9.79 20,12C20,14.22 19.11,16.22 17.66,17.66L19.07,19.07C20.88,17.26 22,14.76 22,12C22,9.24 20.88,6.74 19.07,4.93M7.76,7.76C6.67,8.85 6,10.35 6,12C6,13.65 6.67,15.15 7.76,16.24L9.17,14.83C8.45,14.11 8,13.11 8,12C8,10.89 8.45,9.89 9.17,9.17L7.76,7.76M16.24,7.76L14.83,9.17C15.55,9.89 16,10.89 16,12C16,13.11 15.55,14.11 14.83,14.83L16.24,16.24C17.33,15.15 18,13.65 18,12C18,10.35 17.33,8.85 16.24,7.76M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10Z",
  star: "M12,17.27L18.18,21L16.54,13.64L22,8.64L14.81,8.03L12,1.5L9.19,8.03L2,8.64L7.45,13.64L5.82,21L12,17.27Z",
  wifi: "M12,21L15.6,16.2C14.6,15.45 13.35,15 12,15C10.65,15 9.4,15.45 8.4,16.2L12,21M12,3C7.95,3 4.21,4.34 1.2,6.6L3,9C5.5,7.12 8.62,6 12,6C15.38,6 18.5,7.12 21,9L22.8,6.6C19.79,4.34 16.05,3 12,3M12,9C9.3,9 6.81,9.89 4.8,11.4L6.6,13.8C8.1,12.67 9.97,12 12,12C14.03,12 15.9,12.67 17.4,13.8L19.2,11.4C17.19,9.89 14.7,9 12,9Z",
  devices: "M3,6H21V4H3C1.9,4 1,4.9 1,6V18A2,2 0 0,0 3,20H7V18H3V6M13,12H9V13.78C8.39,14.33 8,15.11 8,16C8,16.89 8.39,17.67 9,18.22V20H13V18.22C13.61,17.67 14,16.88 14,16C14,15.12 13.61,14.33 13,13.78V12M11,17.5A1.5,1.5 0 0,1 9.5,16A1.5,1.5 0 0,1 11,14.5A1.5,1.5 0 0,1 12.5,16A1.5,1.5 0 0,1 11,17.5M22,8H16A1,1 0 0,0 15,9V19A1,1 0 0,0 16,20H22A1,1 0 0,0 23,19V9A1,1 0 0,0 22,8M21,18H17V10H21V18Z",
  check: "M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z",
  swap: "M21,9L17,5V8H10V10H17V13M7,11L3,15L7,19V16H14V14H7V11Z",
  alert: "M13,14H11V9H13M13,18H11V16H13M1,21H23L12,2L1,21Z",
  info: "M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
  off: "M2.28,3L1,4.27L2.47,5.74C2.04,6 1.61,6.29 1.2,6.6L3,9C3.53,8.6 4.08,8.25 4.66,7.93L6.89,10.16C6.15,10.5 5.44,10.91 4.8,11.4L6.6,13.8C7.38,13.22 8.26,12.77 9.2,12.47L11.75,15C10.5,15.07 9.34,15.5 8.4,16.2L12,21L14.46,17.73L17.74,21L19,19.72M12,3C9.85,3 7.8,3.38 5.9,4.07L8.29,6.47C9.5,6.16 10.72,6 12,6C15.38,6 18.5,7.11 21,9L22.8,6.6C19.79,4.34 16.06,3 12,3M12,9C11.62,9 11.25,9 10.88,9.05L14.07,12.25C15.29,12.53 16.43,13.07 17.4,13.8L19.2,11.4C17.2,9.89 14.7,9 12,9Z",
  server: "M4,1H20A1,1 0 0,1 21,2V6A1,1 0 0,1 20,7H4A1,1 0 0,1 3,6V2A1,1 0 0,1 4,1M4,9H20A1,1 0 0,1 21,10V14A1,1 0 0,1 20,15H4A1,1 0 0,1 3,14V10A1,1 0 0,1 4,9M4,17H20A1,1 0 0,1 21,18V22A1,1 0 0,1 20,23H4A1,1 0 0,1 3,22V18A1,1 0 0,1 4,17M9,5H10V3H9V5M9,13H10V11H9V13M9,21H10V19H9V21M5,3V5H7V3H5M5,11V13H7V11H5M5,19V21H7V19H5Z",
  chip: "M6,4H18V5H21V7H18V9H21V11H18V13H21V15H18V17H21V19H18V20H6V19H3V17H6V15H3V13H6V11H3V9H6V7H3V5H6V4M11,15V18H12V15H11M13,15V18H14V15H13M15,15V18H16V15H15Z",
  table: "M5,4H19A2,2 0 0,1 21,6V18A2,2 0 0,1 19,20H5A2,2 0 0,1 3,18V6A2,2 0 0,1 5,4M5,8V12H11V8H5M13,8V12H19V8H13M5,14V18H11V14H5M13,14V18H19V14H13Z",
  chart: "M3,14L3.5,14.07L8.07,9.5C7.89,8.85 8.06,8.11 8.59,7.59C9.37,6.8 10.63,6.8 11.41,7.59C11.94,8.11 12.11,8.85 11.93,9.5L14.5,12.07L15,12C15.18,12 15.35,12 15.5,12.07L19.07,8.5C19,8.35 19,8.18 19,8A2,2 0 0,1 21,6A2,2 0 0,1 23,8A2,2 0 0,1 21,10C20.82,10 20.65,10 20.5,9.93L16.93,13.5C17,13.65 17,13.82 17,14A2,2 0 0,1 15,16A2,2 0 0,1 13,14L13.07,13.5L10.5,10.93C10.18,11 9.82,11 9.5,10.93L4.93,15.5L5,16A2,2 0 0,1 3,18A2,2 0 0,1 1,16A2,2 0 0,1 3,14Z",
};
Object.assign(P, {
  stop: "M18,18H6V6H18V18Z",
  close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  clock: "M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z",
  skip: "M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M7,11V13H17V11H7Z",
  error: "M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
});
const icon = (name, cls = "") => `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${P[name]}"/></svg>`;

const QUALITY_ICON = { excellent: "check", good: "check", fair: "info", weak: "alert", unknown: "info" };

// ---------------------------------------------------------------- stile
const STYLE = `
:host {
  --wa-font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --wa-page: #f4f5f2; --wa-card: #fcfcfb; --wa-ink: #0b0b0b; --wa-ink2: #52514e; --wa-muted: #898781;
  --wa-grid: #e1e0d9; --wa-axis: #c3c2b7; --wa-ring: rgba(11,11,11,.08);
  --wa-own: #2a78d6; --wa-other: #eb6834; --wa-neutral: #cfcec6; --wa-neutral-strong: #a9a89f;
  --wa-good: #0ca30c; --wa-warn: #fab219; --wa-serious: #ec835a; --wa-crit: #d03b3b; --wa-good-ink: #006300;
  --wa-wash: rgba(42,120,214,.08); --wa-shadow: 0 1px 2px rgba(11,11,11,.04), 0 8px 24px rgba(11,11,11,.06);
  --wa-hero: linear-gradient(135deg, #1c5cab 0%, #2a78d6 55%, #3f8fe6 100%);
  --wa-radius: 18px;
  display: block; min-height: 100vh; background: var(--wa-page); color: var(--wa-ink);
  font-family: var(--wa-font); -webkit-font-smoothing: antialiased;
}
:host([dark]) {
  --wa-page: #0d0d0d; --wa-card: #1a1a19; --wa-ink: #f0efec; --wa-ink2: #c3c2b7; --wa-muted: #898781;
  --wa-grid: #2c2c2a; --wa-axis: #383835; --wa-ring: rgba(255,255,255,.08);
  --wa-own: #3987e5; --wa-other: #d95926; --wa-neutral: #3a3a37; --wa-neutral-strong: #55554f; --wa-good-ink: #0ca30c;
  --wa-wash: rgba(57,135,229,.14); --wa-shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.35);
  --wa-hero: linear-gradient(135deg, #0d366b 0%, #184f95 55%, #256abf 100%);
}
* { box-sizing: border-box; }
.ic { width: 20px; height: 20px; fill: currentColor; flex: none; }
button { font: inherit; color: inherit; }

.hero { background: var(--wa-hero); color: #fff; padding: 14px 24px 64px; position: relative; overflow: hidden; }
.hero::after { content: ""; position: absolute; right: -80px; top: -120px; width: 380px; height: 380px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,.16), rgba(255,255,255,0) 70%); pointer-events: none; }
.bar { display: flex; align-items: center; gap: 12px; min-height: 48px; }
.icon-btn { background: none; border: 0; padding: 8px; border-radius: 50%; cursor: pointer; display: inline-flex; color: inherit; }
.icon-btn:hover { background: rgba(255,255,255,.14); }
.hero h1 { font-size: 22px; font-weight: 650; margin: 0; letter-spacing: -.2px; }
.hero .sub { opacity: .85; font-size: 13.5px; margin-top: 2px; }
.spacer { flex: 1; }
.scan-btn { display: inline-flex; align-items: center; gap: 8px; border: 0; cursor: pointer; border-radius: 999px;
  padding: 10px 18px 10px 14px; background: #fff; color: #184f95; font-weight: 600; font-size: 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,.18); transition: transform .15s ease, box-shadow .15s ease; }
.scan-btn:hover { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(0,0,0,.22); }
.scan-btn[disabled] { cursor: default; opacity: .92; transform: none; }
.scan-btn .ic { width: 18px; height: 18px; }
.scan-btn.running .ic { animation: spin 1.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.progress { margin-top: 14px; height: 6px; background: rgba(255,255,255,.22); border-radius: 99px; overflow: hidden; max-width: 520px; }
.progress > i { display: block; height: 100%; background: #fff; border-radius: 99px; transition: width .4s ease; }
.progress-label { font-size: 12.5px; opacity: .9; margin-top: 6px; }

.wrap { max-width: 1240px; margin: -44px auto 0; padding: 0 20px 40px; position: relative; display: grid; gap: 18px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.seg { display: inline-flex; background: var(--wa-card); border-radius: 999px; padding: 4px; box-shadow: var(--wa-shadow); border: 1px solid var(--wa-ring); }
.seg button { border: 0; background: none; padding: 7px 16px; border-radius: 999px; cursor: pointer; font-size: 13.5px; font-weight: 550; color: var(--wa-ink2); }
.seg button[aria-pressed="true"] { background: var(--wa-own); color: #fff; }
.seg button[disabled] { opacity: .45; cursor: default; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { border: 1px solid var(--wa-ring); background: var(--wa-card); color: var(--wa-ink2); border-radius: 999px; padding: 6px 12px; font-size: 12.5px; cursor: pointer; white-space: nowrap; }
.chip:hover { background: var(--wa-wash); }
.chip[aria-pressed="true"] { border-color: var(--wa-own); color: #fff; background: var(--wa-own); font-weight: 600; }

.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.card { background: var(--wa-card); border-radius: var(--wa-radius); box-shadow: var(--wa-shadow); border: 1px solid var(--wa-ring); }
.tile { padding: 16px 18px; display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.tile .lbl { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--wa-ink2); font-weight: 550; }
.tile .lbl .ic { width: 18px; height: 18px; color: var(--wa-muted); }
.tile .val { font-size: 34px; font-weight: 680; letter-spacing: -.8px; line-height: 1.1; display: flex; align-items: baseline; gap: 8px; }
.tile .val small { font-size: 14px; font-weight: 550; color: var(--wa-ink2); letter-spacing: 0; }
.tile .foot { font-size: 12.5px; color: var(--wa-ink2); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.tile.accent { background: linear-gradient(180deg, var(--wa-wash), transparent 70%), var(--wa-card); }
.tile.accent .lbl .ic { color: var(--wa-own); }

.status { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; padding: 2px 8px 2px 5px; border-radius: 999px; color: var(--wa-ink); }
.status .ic { width: 14px; height: 14px; }
.status.excellent .ic, .status.good .ic { color: var(--wa-good); }
.status.fair .ic { color: var(--wa-warn); }
.status.weak .ic { color: var(--wa-crit); }
.status.unknown .ic { color: var(--wa-muted); }
.status.excellent, .status.good { background: color-mix(in srgb, var(--wa-good) 12%, transparent); }
.status.fair { background: color-mix(in srgb, var(--wa-warn) 16%, transparent); }
.status.weak { background: color-mix(in srgb, var(--wa-crit) 12%, transparent); }
.status.unknown { background: color-mix(in srgb, var(--wa-muted) 14%, transparent); }

.advice { padding: 18px 20px; display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; align-items: start; }
.advice .badge { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center; background: var(--wa-wash); color: var(--wa-own); grid-row: span 2; }
.advice .badge.change { background: color-mix(in srgb, var(--wa-warn) 18%, transparent); color: #9a6a00; }
:host([dark]) .advice .badge.change { color: var(--wa-warn); }
.advice h2 { margin: 0; font-size: 17px; font-weight: 650; }
.advice p { margin: 0; color: var(--wa-ink2); font-size: 14px; line-height: 1.45; }
.advice ul { grid-column: 2; margin: 8px 0 0; padding: 0; list-style: none; display: grid; gap: 6px; }
.advice li { display: flex; gap: 8px; font-size: 13.5px; color: var(--wa-ink); line-height: 1.4; }
.advice li .ic { width: 18px; height: 18px; color: var(--wa-warn); margin-top: 1px; }
.pill { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 3px 10px; border-radius: 999px; background: var(--wa-wash); color: var(--wa-own); font-weight: 600; }

.section { padding: 18px 20px 16px; min-width: 0; }
.section-head { flex-wrap: wrap; }
.section-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px; }
.section-head h3 { margin: 0; font-size: 15.5px; font-weight: 650; }
.section-head p { margin: 3px 0 0; font-size: 12.5px; color: var(--wa-ink2); }
.legend { display: flex; gap: 14px; font-size: 12.5px; color: var(--wa-ink2); align-items: center; flex-wrap: wrap; }
.legend i { display: inline-block; width: 16px; height: 3px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }
.view-btn { border: 1px solid var(--wa-ring); background: none; border-radius: 10px; padding: 6px; cursor: pointer; display: inline-flex; color: var(--wa-ink2); }
.view-btn:hover { background: var(--wa-wash); }
.view-btn .ic { width: 18px; height: 18px; }

.chart { position: relative; width: 100%; }
.chart svg { display: block; width: 100%; height: auto; overflow: visible; }
.chart text { font-family: var(--wa-font); }
.tick { fill: var(--wa-muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.tick.on { fill: var(--wa-ink); font-weight: 650; }
.gridline { stroke: var(--wa-grid); stroke-width: 1; }
.baseline { stroke: var(--wa-axis); stroke-width: 1; }
.net { transition: opacity .15s ease; }
.net path.fill { stroke-width: 2; stroke-linejoin: round; }
.net.own path.fill { fill: var(--wa-own); fill-opacity: .14; stroke: var(--wa-own); }
.net.other path.fill { fill: var(--wa-other); fill-opacity: .07; stroke: var(--wa-other); stroke-opacity: .75; }
.chart.hovering .net { opacity: .28; }
.chart.hovering .net.hot { opacity: 1; }
.net.hot path.fill { stroke-width: 2.5; fill-opacity: .24; }
.net-label { font-size: 11.5px; font-weight: 600; fill: var(--wa-ink); paint-order: stroke; stroke: var(--wa-card); stroke-width: 4px; stroke-linejoin: round; }
.net-label.own { fill: var(--wa-own); }
.mark-rec { fill: var(--wa-wash); }
.mark-rec-label { font-size: 11px; font-weight: 700; fill: var(--wa-own); letter-spacing: .3px; text-transform: uppercase; }
.mark-cur { stroke: var(--wa-ink2); stroke-width: 1.5; stroke-dasharray: 4 4; }
.mark-cur-label { font-size: 11px; font-weight: 600; fill: var(--wa-ink2); letter-spacing: .3px; text-transform: uppercase; }
.bar-n { fill: var(--wa-neutral); transition: fill .15s ease; }
.bar-n.pref { fill: var(--wa-neutral-strong); }
.bar-n.rec { fill: var(--wa-own); }
.bar-n.hot { filter: brightness(1.08); }
.bar-ring { fill: none; stroke: var(--wa-ink); stroke-width: 1.5; }
.bar-val { font-size: 11.5px; font-weight: 650; fill: var(--wa-ink); font-variant-numeric: tabular-nums; }
.hit { fill: transparent; cursor: crosshair; }

.tip { position: absolute; pointer-events: none; z-index: 5; min-width: 180px; max-width: 280px; background: var(--wa-card); color: var(--wa-ink);
  border: 1px solid var(--wa-ring); border-radius: 12px; box-shadow: 0 12px 32px rgba(0,0,0,.18); padding: 10px 12px; font-size: 12.5px;
  opacity: 0; transform: translateY(4px); transition: opacity .12s ease, transform .12s ease; }
.tip.show { opacity: 1; transform: none; }
.tip .t-val { font-size: 18px; font-weight: 700; letter-spacing: -.3px; }
.tip .t-name { display: flex; align-items: center; gap: 6px; color: var(--wa-ink2); margin-top: 1px; word-break: break-all; }
.tip .t-name i { width: 12px; height: 3px; border-radius: 2px; flex: none; }
.tip dl { display: grid; grid-template-columns: auto 1fr; gap: 3px 10px; margin: 8px 0 0; }
.tip dt { color: var(--wa-muted); }
.tip dd { margin: 0; font-variant-numeric: tabular-nums; }

.two { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; font-weight: 600; color: var(--wa-muted); font-size: 11.5px; text-transform: uppercase; letter-spacing: .4px; padding: 6px 8px; border-bottom: 1px solid var(--wa-grid); }
td { padding: 9px 8px; border-bottom: 1px solid var(--wa-grid); vertical-align: middle; }
tr:last-child td { border-bottom: 0; }
td.num { font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
th.num { text-align: right; }
.ssid { font-weight: 600; word-break: break-word; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11.5px; color: var(--wa-muted); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
.bars { display: inline-flex; align-items: flex-end; gap: 2px; height: 14px; vertical-align: middle; margin-right: 8px; }
.bars i { width: 4px; border-radius: 1.5px; background: var(--wa-grid); }
.bars i.on { background: var(--wa-ink2); }
.table-scroll { overflow-x: auto; }

.aps { display: grid; gap: 10px; }
.ap { display: grid; grid-template-columns: auto 1fr auto; gap: 4px 12px; align-items: center; padding: 12px 14px; border-radius: 14px; background: var(--wa-wash); }
.ap .ic { color: var(--wa-own); width: 22px; height: 22px; grid-row: span 2; }
.ap .name { font-weight: 650; font-size: 13.5px; }
.ap .meta { font-size: 12px; color: var(--wa-ink2); }
.ap .count { grid-row: span 2; text-align: right; font-size: 22px; font-weight: 700; letter-spacing: -.4px; }
.ap .count small { display: block; font-size: 11px; font-weight: 550; color: var(--wa-ink2); letter-spacing: 0; }

.qbar { display: flex; height: 12px; border-radius: 99px; overflow: hidden; gap: 2px; margin: 4px 0 8px; }
.qbar span { display: block; height: 100%; }
.qbar span:first-child { border-radius: 99px 0 0 99px; }
.qbar span:last-child { border-radius: 0 99px 99px 0; }
.qlegend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; color: var(--wa-ink2); margin-bottom: 12px; }
.qlegend b { color: var(--wa-ink); font-variant-numeric: tabular-nums; }
.qlegend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
.search { flex: 1; min-width: 160px; max-width: 280px; border: 1px solid var(--wa-ring); background: var(--wa-page); color: var(--wa-ink); border-radius: 999px; padding: 7px 14px; font: inherit; font-size: 13px; outline: none; }
.search:focus { border-color: var(--wa-own); }
.dev-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 8px; }
.dev { display: grid; grid-template-columns: 1fr auto; gap: 2px 10px; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--wa-grid); align-items: center; }
.dev .n { font-weight: 600; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dev .m { font-size: 12px; color: var(--wa-ink2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dev .r { text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 650; }
.meter { grid-column: 1 / -1; height: 4px; background: var(--wa-grid); border-radius: 99px; overflow: hidden; margin-top: 4px; }
.meter i { display: block; height: 100%; border-radius: 99px; background: var(--wa-ink2); }
.dev.off { border-style: dashed; }
.dev.off .n { color: var(--wa-ink2); }

.probe-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; }
.probe { display: flex; gap: 12px; padding: 12px; border-radius: 14px; border: 1px solid var(--wa-grid); align-items: center; }
.probe .pi { width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; background: var(--wa-wash); color: var(--wa-own); flex: none; }
.probe .pn { font-weight: 600; font-size: 13.5px; }
.probe .pm { font-size: 12px; color: var(--wa-ink2); }
.probe .err { color: var(--wa-crit); }

.empty { padding: 48px 20px; text-align: center; color: var(--wa-ink2); }
.empty .big { width: 64px; height: 64px; margin: 0 auto 12px; border-radius: 20px; display: grid; place-items: center; background: var(--wa-wash); color: var(--wa-own); }
.empty .big .ic { width: 34px; height: 34px; }
.empty h3 { color: var(--wa-ink); margin: 0 0 6px; font-size: 17px; }
.footer { text-align: center; font-size: 12px; color: var(--wa-muted); padding-top: 4px; }
.footer a { color: inherit; }
.err-box { padding: 20px; color: var(--wa-crit); }
.muted { color: var(--wa-ink2); font-size: 13px; margin: 4px 0; }

.probes-btn { display: inline-flex; align-items: center; gap: 6px; border: 1px solid rgba(255,255,255,.45); background: rgba(255,255,255,.12); color: #fff;
  border-radius: 999px; padding: 9px 14px; cursor: pointer; font-size: 13.5px; font-weight: 600; margin-right: 8px; }
.probes-btn:hover { background: rgba(255,255,255,.22); }
.probes-btn .ic { width: 18px; height: 18px; }
@media (max-width: 560px) { .probes-btn span { display: none; } .probes-btn { padding: 9px; } }
.scan-btn.stop { background: #fff; color: var(--wa-crit); }
.scan-btn.stop .ic { animation: none; }

.scan-card { padding: 16px 20px; display: grid; gap: 12px; border-left: 4px solid var(--wa-own); }
.scan-card.done { border-left-color: var(--wa-good); }
.scan-card.stopped { border-left-color: var(--wa-warn); }
.scan-card.failed { border-left-color: var(--wa-crit); }
.sc-head { display: flex; align-items: center; gap: 14px; }
.sc-badge { width: 42px; height: 42px; border-radius: 14px; display: grid; place-items: center; flex: none; background: var(--wa-wash); color: var(--wa-own); }
.sc-badge.run .ic { animation: spin 1.6s linear infinite; }
.done .sc-badge { background: color-mix(in srgb, var(--wa-good) 14%, transparent); color: var(--wa-good); }
.stopped .sc-badge { background: color-mix(in srgb, var(--wa-warn) 18%, transparent); color: #9a6a00; }
:host([dark]) .stopped .sc-badge { color: var(--wa-warn); }
.failed .sc-badge { background: color-mix(in srgb, var(--wa-crit) 14%, transparent); color: var(--wa-crit); }
.sc-title { font-size: 16px; font-weight: 650; }
.sc-sub { font-size: 13px; color: var(--wa-ink2); margin-top: 2px; }
.btn-outline { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--wa-ring); background: var(--wa-card); color: var(--wa-ink); border-radius: 999px; padding: 7px 14px; cursor: pointer; font-size: 13px; font-weight: 600; white-space: nowrap; }
.btn-outline:hover { background: var(--wa-wash); }
.btn-outline.danger { color: var(--wa-crit); border-color: color-mix(in srgb, var(--wa-crit) 40%, transparent); }
.btn-outline.danger:hover { background: color-mix(in srgb, var(--wa-crit) 8%, transparent); }
.btn-outline[disabled] { opacity: .55; cursor: default; }
.btn-outline .ic { width: 16px; height: 16px; }
.sc-bar { height: 8px; background: var(--wa-grid); border-radius: 99px; overflow: hidden; }
.sc-bar > i { display: block; height: 100%; border-radius: 99px; background: var(--wa-own); transition: width .5s ease; }
.sc-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 6px 14px; }
.sc-item { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; min-width: 0; }
.sc-item .ic { width: 18px; height: 18px; flex: none; }
.sc-item .nm { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sc-item .st { color: var(--wa-ink2); font-size: 12px; }
.sc-item.waiting { opacity: .6; } .sc-item.waiting .ic { color: var(--wa-muted); }
.sc-item.scanning .ic { color: var(--wa-own); animation: spin 1.6s linear infinite; }
.sc-item.scanning .st { color: var(--wa-own); font-weight: 600; }
.sc-item.done .ic { color: var(--wa-good); }
.sc-item.error .ic { color: var(--wa-crit); } .sc-item.error .st { color: var(--wa-crit); }
.sc-item.skipped { opacity: .6; } .sc-item.skipped .ic { color: var(--wa-muted); }

.probe-actions { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
.probe-actions .count { font-size: 12.5px; color: var(--wa-ink2); margin-left: 6px; }
.probe { cursor: pointer; background: none; text-align: left; width: 100%; font: inherit; color: inherit; transition: border-color .15s ease, background .15s ease; }
.probe:hover { background: var(--wa-wash); }
.probe.on { border-color: color-mix(in srgb, var(--wa-own) 55%, transparent); }
.probe[disabled] { cursor: default; }
.probe .grow { flex: 1; min-width: 0; }
.switch { width: 36px; height: 20px; border-radius: 99px; background: var(--wa-grid); position: relative; flex: none; transition: background .15s ease; }
.switch::after { content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.3); transition: transform .15s ease; }
.probe.on .switch { background: var(--wa-own); }
.probe.on .switch::after { transform: translateX(16px); }
.warn-line { display: flex; gap: 8px; align-items: center; font-size: 13px; color: var(--wa-ink); background: color-mix(in srgb, var(--wa-warn) 14%, transparent); padding: 8px 12px; border-radius: 10px; margin-bottom: 10px; }
.warn-line .ic { color: var(--wa-warn); width: 18px; height: 18px; }

@media (max-width: 1000px) { .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } .two { grid-template-columns: 1fr; } }
@media (max-width: 560px) {
  .hero { padding: 10px 16px 60px; } .wrap { padding: 0 12px 32px; }
  .tile .val { font-size: 28px; } .scan-btn span { display: none; } .scan-btn { padding: 10px; }
  .dev-list { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
`;

// ---------------------------------------------------------------- utilità
function fmt(str, vars = {}) {
  return str.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ""));
}

function relTime(iso, lang) {
  if (!iso) return "";
  // Orologi di browser e server non sono mai identici: niente "tra 3 secondi".
  const diff = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
  if (diff < 60) return rtf.format(-Math.round(diff), "second");
  if (diff < 3600) return rtf.format(-Math.round(diff / 60), "minute");
  if (diff < 86400) return rtf.format(-Math.round(diff / 3600), "hour");
  return rtf.format(-Math.round(diff / 86400), "day");
}

function signalBars(rssi) {
  const n = rssi == null ? 0 : rssi >= -55 ? 4 : rssi >= -67 ? 3 : rssi >= -75 ? 2 : 1;
  return `<span class="bars" aria-hidden="true">${[5, 8, 11, 14].map((h, i) =>
    `<i class="${i < n ? "on" : ""}" style="height:${h}px"></i>`).join("")}</span>`;
}

function qualityColor(q) {
  return { excellent: "var(--wa-good)", good: "var(--wa-good)", fair: "var(--wa-warn)", weak: "var(--wa-crit)" }[q] || "var(--wa-muted)";
}

// ---------------------------------------------------------------- pannello
class WifiAnalyzerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._data = null;
    this._error = null;
    this._band = "2.4";
    this._probe = "all";
    this._devFilter = "all";
    this._devSearch = "";
    this._tableView = false;
    this._progress = null;
    this._result = null;
    this._savingProbes = false;
  }

  get _running() { return !!this._progress?.running; }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const dark = !!hass.themes?.darkMode;
    if (dark !== this.hasAttribute("dark")) this.toggleAttribute("dark", dark);
    if (first) this._load();
  }

  set narrow(v) { this._narrow = v; }

  get _lang() {
    const l = (this._hass?.locale?.language || this._hass?.language || "en").split("-")[0];
    return I18N[l] ? l : "en";
  }

  t(key, vars) { return fmt(I18N[this._lang][key] ?? I18N.en[key] ?? key, vars); }

  _ws(type, extra = {}) { return this._hass.callWS({ type: `${DOMAIN}/${type}`, ...extra }); }

  async _load() {
    try {
      this._data = await this._ws("data");
      this._error = null;
      if (this._data.progress?.running) {
        this._progress = this._data.progress;
        this._watchProgress();
      }
      // Se c'è solo il 5 GHz, parti da lì.
      if (!this._data.bands["2.4"]?.probes?.length && this._data.bands["5"]?.probes?.length) this._band = "5";
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._render();
  }

  async _scan() {
    if (this._running) return;
    this._result = null;
    try {
      await this._ws("scan");
    } catch (err) {
      if (err.code !== "scan_running") {
        this._error = err.message || String(err);
        this._render();
        return;
      }
    }
    const selected = (this._data?.probes || []).filter((p) => p.selected);
    this._progress = {
      running: true, total: selected.length, done: 0, elapsed: 0,
      probes: selected.map((p) => ({ id: p.id, name: p.name, area: p.area, state: "waiting" })),
    };
    this._render();
    this._watchProgress();
  }

  async _cancel() {
    if (!this._running) return;
    this._progress.cancelling = true;
    this._renderScanState();
    try { await this._ws("cancel"); } catch (_) { /* il polling mostrerà lo stato vero */ }
  }

  /** Segue la scansione in corso; quando finisce ricarica i dati e mostra l'esito. */
  _watchProgress() {
    if (this._pollTimer) return;
    this._pollTimer = setInterval(async () => {
      try {
        const p = await this._ws("progress");
        if (!p.running) {
          clearInterval(this._pollTimer);
          this._pollTimer = null;
          this._progress = null;
          await this._load();
          this._result = this._data?.last_result || null;
          this._render();
          return;
        }
        this._progress = p;
        this._renderScanState();
      } catch (_) {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
      }
    }, 800);
  }

  /** Controllo leggero ogni 10 s: una scansione partita dal pulsante o da un'automazione compare anche qui. */
  _startIdleWatch() {
    clearInterval(this._idleTimer);
    this._idleTimer = setInterval(async () => {
      if (this._running || !this._hass || document.hidden) return;
      try {
        const p = await this._ws("progress");
        if (p.running) {
          this._result = null;
          this._progress = p;
          this._render();
          this._watchProgress();
        }
      } catch (_) { /* integrazione ricaricata: riprova al giro dopo */ }
    }, 10000);
  }

  // -------------------------------------------------------------- dati derivati

  _bandData() { return this._data?.bands?.[this._band] || {}; }

  /** Reti della banda per la vista scelta: tutta la casa (segnale migliore) o una sonda. */
  _networks() {
    const band = this._bandData();
    if (this._probe === "all") {
      return [...(band.own || []).map((n) => ({ ...n, own: true })), ...(band.neighbors || [])];
    }
    const ownSet = new Set((band.own || []).map((n) => n.bssid));
    return (this._data.networks || [])
      .filter((n) => n.probe === this._probe && n.band === this._band)
      .map((n) => ({ ...n, own: n.own || ownSet.has(n.bssid), seen_by: { [n.probe]: n.rssi } }))
      .sort((a, b) => b.rssi - a.rssi);
  }

  _probeName(id) {
    return this._data?.probes?.find((p) => p.id === id)?.name
      || this._data?.last_scan?.probes?.find((p) => p.id === id)?.name || id;
  }

  // -------------------------------------------------------------- render

  /** Larghezza vera dei grafici: l'SVG si disegna a 1:1, così il testo resta leggibile anche sul telefono. */
  _measure() {
    const host = this.clientWidth || 1000;
    const pad = host <= 560 ? 12 * 2 + 20 * 2 : 20 * 2 + 20 * 2;
    this._chartW = Math.max(280, Math.min(1200 - 40 - 40, host - pad));
    this._compact = this._chartW < 600;
  }

  connectedCallback() {
    this._ro = new ResizeObserver(() => {
      const before = this._chartW;
      this._measure();
      if (this._data && Math.abs(before - this._chartW) > 8) {
        clearTimeout(this._roTimer);
        this._roTimer = setTimeout(() => this._render(), 120);
      }
    });
    this._ro.observe(this);
    this._startIdleWatch();
  }

  disconnectedCallback() {
    this._ro?.disconnect();
    clearInterval(this._idleTimer);
    clearInterval(this._pollTimer);
    this._pollTimer = null;
  }

  _render() {
    this._measure();
    const root = this.shadowRoot;
    if (!this._data && !this._error) {
      root.innerHTML = `<style>${STYLE}</style>${this._heroHtml()}<div class="wrap"><div class="card empty">${this.t("loading")}</div></div>`;
      this._bindHero();
      return;
    }
    if (this._error && !this._data) {
      root.innerHTML = `<style>${STYLE}</style>${this._heroHtml()}<div class="wrap"><div class="card err-box">${esc(this.t("error"))}: ${esc(this._error)}
        <p><button class="chip" id="retry">${this.t("retry")}</button></p></div></div>`;
      this._bindHero();
      root.getElementById("retry")?.addEventListener("click", () => this._load());
      return;
    }

    const d = this._data;
    const band = this._bandData();
    const hasScan = !!d.last_scan;
    const bandReady = (band.probes || []).length > 0;

    root.innerHTML = `<style>${STYLE}</style>
      ${this._heroHtml()}
      <div class="wrap">
        <div id="scan-slot">${this._scanCardHtml()}</div>
        ${this._toolbarHtml()}
        ${hasScan && bandReady ? `
          ${this._tilesHtml()}
          ${this._adviceHtml()}
          <div class="card section">${this._spectrumHtml()}</div>
          <div class="card section">${this._scoresHtml()}</div>
          <div class="two">
            <div class="card section">${this._neighborsHtml()}</div>
            <div class="card section">${this._ownApsHtml()}</div>
          </div>` : `
          <div class="card empty">
            <div class="big">${icon(hasScan ? "info" : "radar")}</div>
            <h3>${hasScan ? this.t("a_no_data") : this.t("never")}</h3>
            <p>${hasScan ? this.t("noBand") : this.t("empty")}</p>
          </div>`}
        <div class="card section">${this._devicesHtml()}</div>
        <div class="card section" id="probes-section">${this._probesHtml()}</div>
        <div class="footer">${esc(d.integration.name)} ${esc(d.integration.version)} · ${this.t("by")} ${esc(d.integration.author)}</div>
      </div>`;

    this._bindHero();
    this._bindToolbar();
    if (hasScan && bandReady) {
      this._bindSpectrum();
      this._bindScores();
    }
    this._bindDevices();
    this._bindScanCard();
    this._bindProbes();
  }

  _heroHtml() {
    const d = this._data;
    const last = d?.last_scan;
    const sub = last
      ? `${this.t("lastScan")} ${esc(relTime(last.time, this._lang))} · ${this.t("probesN", { n: last.probes.filter((p) => p.ok).length })} · ${this.t("networksN", { n: last.networks })}`
      : this.t("never");
    return `<div class="hero">
      <div class="bar">
        ${this._narrow ? `<button class="icon-btn" id="menu" title="${this.t("openMenu")}" aria-label="${this.t("openMenu")}">${icon("menu")}</button>` : ""}
        <div><h1>${this.t("title")}</h1><div class="sub" id="hero-sub">${sub}</div></div>
        <div class="spacer"></div>
        ${d ? `<button class="probes-btn" id="goto-probes">${icon("chip")}<span>${this.t("probes")} ${d.probes.filter((p) => p.selected).length}/${d.probes.length}</span></button>` : ""}
        <span id="hero-btn">${this._heroBtnHtml()}</span>
      </div>
    </div>`;
  }

  _heroBtnHtml() {
    const d = this._data;
    if (this._running) {
      const c = this._progress.cancelling;
      return `<button class="scan-btn stop" id="stop" ${c ? "disabled" : ""} title="${this.t("stopHint")}">${icon("stop")}<span>${c ? this.t("stopping") : this.t("stop")}</span></button>`;
    }
    const none = d && !d.probes.some((p) => p.selected);
    return `<button class="scan-btn" id="scan" ${!d || none ? "disabled" : ""}>${icon("radar")}<span>${this.t("scan")}</span></button>`;
  }

  _bindHero() {
    const root = this.shadowRoot;
    root.getElementById("scan")?.addEventListener("click", () => this._scan());
    root.getElementById("stop")?.addEventListener("click", () => this._cancel());
    root.getElementById("goto-probes")?.addEventListener("click", () => {
      root.getElementById("probes-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    root.getElementById("menu")?.addEventListener("click", () => {
      this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
    });
  }

  // ------------------------------------------------------------ scansione

  _scanCardHtml() {
    if (this._running) {
      const p = this._progress;
      const total = p.total || (p.probes || []).length;
      const pct = total ? Math.round((p.done / total) * 100) : 0;
      const left = Math.max(0, (total - p.done) * 5 - 2);
      const sub = [this.t("scanSub", { done: p.done, total, elapsed: Math.round(p.elapsed || 0) })];
      if (!p.cancelling && left) sub.push(this.t("remaining", { s: left }));
      if (p.cancelling) sub.push(this.t("stopHint"));
      return `<div class="card scan-card" role="status" aria-live="polite">
        <div class="sc-head">
          <div class="sc-badge run">${icon("radar")}</div>
          <div class="grow" style="flex:1"><div class="sc-title">${p.cancelling ? this.t("stopping") : this.t("scanRunning")}</div>
            <div class="sc-sub">${esc(sub.join(" · "))}</div></div>
          <button class="btn-outline danger" id="stop2" ${p.cancelling ? "disabled" : ""}>${icon("stop")}${this.t("stop")}</button>
        </div>
        <div class="sc-bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${Math.max(pct, 3)}%"></i></div>
        <div class="sc-list">${(p.probes || []).map((it) => this._scanItemHtml(it)).join("")}</div>
      </div>`;
    }
    const r = this._result;
    if (!r) return "";
    const time = new Date(r.time).toLocaleTimeString(this._lang, { hour: "2-digit", minute: "2-digit" });
    let cls = "done", title = this.t("scanDone"), badge = "check";
    let sub = this.t("resultSub", { time, networks: r.networks, ok: r.ok, total: r.total, duration: Math.round(r.duration) });
    if (r.cancelled) {
      cls = "stopped"; title = this.t("scanStopped"); badge = "stop";
      sub = r.saved ? this.t("resultStopped", { time, ok: r.ok, total: r.total, networks: r.networks }) : `${time} · ${this.t("notSaved")}`;
    } else if (!r.ok) {
      cls = "failed"; title = this.t("scanFailed"); badge = "error";
      sub = `${time} · ${this.t("notSaved")}`;
    }
    if (r.failed && r.ok) sub += ` · ${this.t("failedN", { n: r.failed })}`;
    return `<div class="card scan-card ${cls}" role="status">
      <div class="sc-head">
        <div class="sc-badge">${icon(badge)}</div>
        <div style="flex:1"><div class="sc-title">${title}</div><div class="sc-sub">${esc(sub)}</div></div>
        <button class="icon-btn" id="result-close" title="${this.t("close")}" aria-label="${this.t("close")}" style="color:var(--wa-ink2)">${icon("close")}</button>
      </div>
    </div>`;
  }

  _scanItemHtml(it) {
    const ic = { waiting: "clock", scanning: "radar", done: "check", error: "error", skipped: "skip" }[it.state] || "clock";
    const st = it.state === "done" ? this.t("st_done", { n: it.networks, s: it.duration })
      : it.state === "error" ? `${this.t("st_error")}: ${it.error || ""}` : this.t(`st_${it.state}`);
    return `<div class="sc-item ${it.state}">${icon(ic)}
      <div style="min-width:0"><div class="nm">${esc(it.name)}${it.area ? ` <span class="st">· ${esc(it.area)}</span>` : ""}</div>
      <div class="st">${esc(st)}</div></div></div>`;
  }

  /** Aggiorna solo la scheda di avanzamento e il pulsante: i grafici restano fermi. */
  _renderScanState() {
    const root = this.shadowRoot;
    const slot = root.getElementById("scan-slot");
    const btn = root.getElementById("hero-btn");
    if (!slot || !btn) { this._render(); return; }
    slot.innerHTML = this._scanCardHtml();
    btn.innerHTML = this._heroBtnHtml();
    this._bindHero();
    this._bindScanCard();
    root.querySelectorAll(".probe").forEach((b) => { b.disabled = this._running; });
  }

  _bindScanCard() {
    const root = this.shadowRoot;
    root.getElementById("stop2")?.addEventListener("click", () => this._cancel());
    root.getElementById("result-close")?.addEventListener("click", () => {
      this._result = null;
      root.getElementById("scan-slot").innerHTML = "";
    });
  }

  _toolbarHtml() {
    const d = this._data;
    const has = (b) => (d.bands[b]?.probes || []).length > 0;
    const probes = (d.bands[this._band]?.probes || []);
    return `<div class="toolbar">
      <div class="seg" role="group">
        ${["2.4", "5"].map((b) => `<button data-band="${b}" aria-pressed="${this._band === b}" ${!has(b) && d.last_scan ? "disabled" : ""}>${this.t(b === "2.4" ? "band24" : "band5")}</button>`).join("")}
      </div>
      ${probes.length > 1 ? `<div class="chips">
        <button class="chip" data-probe="all" aria-pressed="${this._probe === "all"}">${this.t("wholeHome")}</button>
        ${probes.map((id) => {
          const p = d.probes.find((x) => x.id === id);
          const label = p?.area || this._probeName(id);
          return `<button class="chip" data-probe="${esc(id)}" aria-pressed="${this._probe === id}" title="${esc(this._probeName(id))}">${esc(label)}</button>`;
        }).join("")}
      </div>` : ""}
    </div>`;
  }

  _bindToolbar() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-band]").forEach((b) => b.addEventListener("click", () => {
      if (b.disabled) return;
      this._band = b.dataset.band;
      this._probe = "all";
      this._render();
    }));
    root.querySelectorAll("[data-probe]").forEach((b) => b.addEventListener("click", () => {
      this._probe = b.dataset.probe;
      this._render();
    }));
  }

  _scoreQuality(score) {
    if (score == null) return "unknown";
    return score >= 80 ? "excellent" : score >= 65 ? "good" : score >= 45 ? "fair" : "weak";
  }

  _statusHtml(q, label) {
    return `<span class="status ${q}">${icon(QUALITY_ICON[q] || "info")}${esc(label ?? this.t(`q_${q}`))}</span>`;
  }

  _tilesHtml() {
    const b = this._bandData();
    const d = this._data;
    const neighbors = b.neighbors || [];
    const strongest = neighbors[0];
    const weak = d.devices.filter((x) => x.quality === "weak").length;
    const off = d.devices.filter((x) => !x.available).length;
    const curQ = this._scoreQuality(b.current_score);
    const changed = b.recommended != null && b.recommended !== b.current;
    return `<div class="tiles">
      <div class="card tile">
        <div class="lbl">${icon("ap")}${this.t("current")}</div>
        <div class="val">${b.current ?? "—"}${b.current_score != null ? `<small>${this.t("pts", { v: b.current_score })}</small>` : ""}</div>
        <div class="foot">${b.current_score != null ? this._statusHtml(curQ) : ""}</div>
      </div>
      <div class="card tile accent">
        <div class="lbl">${icon("star")}${this.t("recommended")}</div>
        <div class="val">${b.recommended ?? "—"}${b.recommended_score != null ? `<small>${this.t("pts", { v: b.recommended_score })}</small>` : ""}</div>
        <div class="foot">${changed && b.gain != null ? `<span class="pill">${icon("swap")}${this.t("gain", { v: b.gain })}</span>` : `<span class="pill">${icon("check")}${this.t(b.advice === "keep_close" ? "a_keep_close" : "alreadyBest")}</span>`}
          ${b.width ? `<span>${this.t("width", { v: b.width })}</span>` : ""}</div>
      </div>
      <div class="card tile">
        <div class="lbl">${icon("wifi")}${this.t("neighbors")}</div>
        <div class="val">${neighbors.length}</div>
        <div class="foot">${strongest ? this.t("strongest", { v: strongest.rssi }) : this.t("none")}</div>
      </div>
      <div class="card tile">
        <div class="lbl">${icon("devices")}${this.t("devices")}</div>
        <div class="val">${d.devices.length}</div>
        <div class="foot">${weak ? this._statusHtml("weak", this.t("weakN", { n: weak })) : ""}
          ${off ? this._statusHtml("unknown", this.t("offlineN", { n: off })) : ""}
          ${!weak && !off ? this._statusHtml("good", this.t("allGood")) : ""}</div>
      </div>
    </div>`;
  }

  _adviceHtml() {
    const b = this._bandData();
    const advice = b.advice || "no_data";
    const best = (b.channels || []).filter((c) => c.preferred).sort((x, y) => y.score - x.score)[0];
    const vars = {
      ch: b.recommended, cur: b.current, to: b.recommended_score, from: b.current_score,
      best: best?.channel, gain: best && b.current_score != null ? best.score - b.current_score : "",
    };
    const warnings = (b.warnings || []).map((w) => {
      const key = `w_${w.code}`;
      return this.t(key, {
        a: w.channels?.[0], b: w.channels?.[1], list: (w.channels || []).join(", "),
        ch: w.channel, ssid: w.ssid || this.t("hidden"), rssi: w.rssi,
      });
    });
    if (this._band === "2.4" && b.width === "20") warnings.push(this.t("widthHint24"));
    const isChange = advice === "change";
    return `<div class="card advice">
      <div class="badge ${isChange ? "change" : ""}">${icon(isChange ? "swap" : "check")}</div>
      <h2>${esc(this.t(`a_${advice}`, vars))}</h2>
      <p>${esc(this.t(`d_${advice}`, vars))}</p>
      ${warnings.length ? `<ul>${warnings.map((w) => `<li>${icon("alert")}<span>${esc(w)}</span></li>`).join("")}</ul>` : ""}
    </div>`;
  }

  // ------------------------------------------------------------ spettro

  _axis() {
    const is24 = this._band === "2.4";
    const channels = (this._bandData().channels || []).map((c) => c.channel);
    // 2,4 GHz: asse continuo in canali; 5 GHz: un posto per canale.
    const pos = is24 ? (ch) => ch : (ch) => Math.max(0, channels.indexOf(ch));
    const min = is24 ? -1 : -1;
    const max = is24 ? 15 : channels.length;
    const half = is24 ? 2 : 0.5;
    return { is24, channels, pos, min, max, half };
  }

  _spectrumHtml() {
    const ax = this._axis();
    const b = this._bandData();
    const nets = this._networks();
    const W = this._chartW, H = this._compact ? 250 : 330, L = 40, R = 10, T = 28, B = 34;
    const x = (v) => L + ((v - ax.min) / (ax.max - ax.min)) * (W - L - R);
    const yMin = -100, yMax = -25;
    const y = (r) => T + ((yMax - Math.max(yMin, Math.min(yMax, r))) / (yMax - yMin)) * (H - T - B);
    this._geo = { W, H, L, R, T, B, x, y, ax, nets, yMin, yMax };

    const grid = [-30, -40, -50, -60, -70, -80, -90].map((r) =>
      `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(r)}" y2="${y(r)}"/><text class="tick" x="${L - 8}" y="${y(r) + 4}" text-anchor="end">${r}</text>`).join("");

    const xt = ax.channels.map((ch) => {
      const on = ch === b.current || ch === b.recommended;
      return `<text class="tick ${on ? "on" : ""}" x="${x(ax.pos(ch))}" y="${H - B + 18}" text-anchor="middle">${ch}</text>`;
    }).join("");

    const rec = b.recommended != null ? (() => {
      const cx = x(ax.pos(b.recommended));
      const w = x(ax.pos(b.recommended) + ax.half) - x(ax.pos(b.recommended) - ax.half);
      return `<rect class="mark-rec" x="${cx - w / 2}" y="${T}" width="${w}" height="${H - T - B}" rx="10"/>
        <text class="mark-rec-label" x="${cx}" y="${T - 10}" text-anchor="middle">★ ${this.t("recommendedShort")}</text>`;
    })() : "";
    const cur = b.current != null && b.current !== b.recommended ? (() => {
      const cx = x(ax.pos(b.current));
      return `<line class="mark-cur" x1="${cx}" x2="${cx}" y1="${T}" y2="${H - B}"/>
        <text class="mark-cur-label" x="${cx}" y="${T - 10}" text-anchor="middle">${this.t("currentShort")}</text>`;
    })() : "";

    const floor = y(yMin);
    // Le più deboli sotto, le più forti sopra.
    const order = [...nets].sort((a, z) => a.rssi - z.rssi);
    const curves = order.map((n) => {
      const c = ax.pos(n.channel);
      const x0 = x(c - ax.half), x1 = x(c + ax.half);
      const shoulder = (x1 - x0) * 0.2;
      const top = y(n.rssi);
      const d = `M${x0},${floor} C${x0 + shoulder * 0.6},${floor} ${x0 + shoulder * 0.4},${top} ${x0 + shoulder * 1.6},${top}
        L${x1 - shoulder * 1.6},${top} C${x1 - shoulder * 0.4},${top} ${x1 - shoulder * 0.6},${floor} ${x1},${floor}`;
      return `<g class="net ${n.own ? "own" : "other"}" data-bssid="${esc(n.bssid)}"><path class="fill" d="${d}"/></g>`;
    }).join("");

    // Etichette: le reti di casa e le 6 vicine più forti, senza sovrapporle.
    // I nodi di una mesh hanno lo stesso nome e canale: un'etichetta sola.
    const seen = new Set();
    const unique = nets.filter((n) => {
      const k = `${n.own}|${n.ssid}|${n.channel}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
    const maxOther = this._compact ? 3 : 6;
    const labelled = [...unique.filter((n) => n.own).slice(0, 2), ...unique.filter((n) => !n.own).slice(0, maxOther)];
    const placed = [];
    const labels = labelled.map((n) => {
      const cx = x(ax.pos(n.channel));
      let ly = y(n.rssi) - 7;
      const text = n.ssid || this.t("hidden");
      const w = Math.min(text.length, 22) * 6.6 + 8;
      for (let i = 0; i < 6; i++) {
        const hit = placed.some((p) => Math.abs(p.x - cx) < (p.w + w) / 2 && Math.abs(p.y - ly) < 14);
        if (!hit) break;
        ly -= 15;
      }
      ly = Math.max(T + 4, ly);
      placed.push({ x: cx, y: ly, w });
      const short = text.length > 22 ? `${text.slice(0, 21)}…` : text;
      return `<text class="net-label ${n.own ? "own" : ""}" x="${cx}" y="${ly}" text-anchor="middle">${esc(short)}</text>`;
    }).join("");

    const legend = `<div class="legend"><span><i style="background:var(--wa-own)"></i>${this.t("yours")}</span><span><i style="background:var(--wa-other)"></i>${this.t("others")}</span></div>`;

    const table = `<div class="table-scroll"><table>
      <thead><tr><th>${this.t("ssid")}</th><th class="num">${this.t("channel")}</th><th class="num">${this.t("signal")}</th><th>${this.t("bssid")}</th></tr></thead>
      <tbody>${nets.map((n) => `<tr><td class="ssid"><span class="dot" style="background:${n.own ? "var(--wa-own)" : "var(--wa-other)"}"></span>${esc(n.ssid || this.t("hidden"))}</td>
        <td class="num">${n.channel}</td><td class="num">${n.rssi} dBm</td><td class="mono">${esc(n.bssid)}</td></tr>`).join("")}</tbody></table></div>`;

    return `<div class="section-head">
        <div><h3>${this.t("spectrum")}</h3><p>${this.t("spectrumSub")}</p></div>
        <div class="spacer"></div>${legend}
        <button class="view-btn" id="spec-view" title="${this._tableView ? this.t("chartView") : this.t("tableView")}" aria-label="${this._tableView ? this.t("chartView") : this.t("tableView")}">${icon(this._tableView ? "chart" : "table")}</button>
      </div>
      ${this._tableView ? table : `<div class="chart" id="spectrum">
        <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${this.t("spectrum")}">
          ${grid}${rec}
          <line class="baseline" x1="${L}" x2="${W - R}" y1="${floor}" y2="${floor}"/>
          ${curves}${cur}${labels}${xt}
          <text class="tick" x="${L - 8}" y="${T - 10}" text-anchor="end">dBm</text>
          <rect class="hit" id="spec-hit" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}"/>
        </svg>
        <div class="tip" id="spec-tip"></div>
      </div>`}`;
  }

  _bindSpectrum() {
    const root = this.shadowRoot;
    root.getElementById("spec-view")?.addEventListener("click", () => { this._tableView = !this._tableView; this._render(); });
    const chart = root.getElementById("spectrum");
    const hit = root.getElementById("spec-hit");
    const tip = root.getElementById("spec-tip");
    if (!chart || !hit) return;
    const svg = chart.querySelector("svg");
    const g = this._geo;

    const leave = () => {
      chart.classList.remove("hovering");
      chart.querySelectorAll(".net.hot").forEach((n) => n.classList.remove("hot"));
      tip.classList.remove("show");
    };
    hit.addEventListener("pointerleave", leave);
    hit.addEventListener("pointermove", (ev) => {
      const pt = svg.createSVGPoint();
      pt.x = ev.clientX; pt.y = ev.clientY;
      const p = pt.matrixTransform(svg.getScreenCTM().inverse());
      const chPos = g.ax.min + ((p.x - g.L) / (g.W - g.L - g.R)) * (g.ax.max - g.ax.min);
      const rssi = g.yMax - ((p.y - g.T) / (g.H - g.T - g.B)) * (g.yMax - g.yMin);
      // La curva "sopra" il puntatore più vicina: quella che lo contiene con il
      // picco più basso. Se nessuna lo contiene, la più vicina in orizzontale.
      const covering = g.nets.filter((n) => Math.abs(g.ax.pos(n.channel) - chPos) <= g.ax.half * 0.85 && n.rssi >= rssi);
      let net = covering.sort((a, z) => a.rssi - z.rssi)[0];
      if (!net) {
        net = [...g.nets].sort((a, z) => Math.abs(g.ax.pos(a.channel) - chPos) - Math.abs(g.ax.pos(z.channel) - chPos)
          || z.rssi - a.rssi)[0];
        if (!net || Math.abs(g.ax.pos(net.channel) - chPos) > g.ax.half) { leave(); return; }
      }
      chart.classList.add("hovering");
      chart.querySelectorAll(".net").forEach((el) => el.classList.toggle("hot", el.dataset.bssid === net.bssid));
      this._showTip(tip, chart, ev, `
        <div class="t-val">${net.rssi} dBm</div>
        <div class="t-name"><i style="background:${net.own ? "var(--wa-own)" : "var(--wa-other)"}"></i>${esc(net.ssid || this.t("hidden"))}</div>
        <dl>
          <dt>${this.t("channel")}</dt><dd>${net.channel}</dd>
          <dt>${this.t("bssid")}</dt><dd class="mono">${esc(net.bssid)}</dd>
          <dt>${this.t("seenBy")}</dt><dd>${esc(Object.keys(net.seen_by || {}).map((id) => this._probeName(id)).join(", "))}</dd>
        </dl>`);
    });
  }

  _showTip(tip, container, ev, html) {
    tip.innerHTML = html;
    tip.classList.add("show");
    const box = container.getBoundingClientRect();
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = ev.clientX - box.left + 14;
    let top = ev.clientY - box.top - th - 12;
    if (left + tw > box.width) left = ev.clientX - box.left - tw - 14;
    if (top < 0) top = ev.clientY - box.top + 16;
    tip.style.left = `${Math.max(0, left)}px`;
    tip.style.top = `${top}px`;
  }

  // ------------------------------------------------------------ punteggi

  _scoresHtml() {
    const b = this._bandData();
    const ax = this._axis();
    const chans = b.channels || [];
    const W = this._chartW, H = this._compact ? 170 : 200, L = 40, R = 10, T = 22, B = 30;
    const x = (v) => L + ((v - ax.min) / (ax.max - ax.min)) * (W - L - R);
    const y = (s) => T + (1 - s / 100) * (H - T - B);
    const step = x(ax.pos(chans[1]?.channel ?? 2)) - x(ax.pos(chans[0]?.channel ?? 1));
    const bw = Math.max(8, Math.min(46, step * 0.62));
    this._scoreGeo = { chans };

    const grid = [0, 50, 100].map((s) =>
      `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y(s)}" y2="${y(s)}"/><text class="tick" x="${L - 8}" y="${y(s) + 4}" text-anchor="end">${s}</text>`).join("");
    const bars = chans.map((c, i) => {
      const cx = x(ax.pos(c.channel));
      const top = y(c.score), base = y(0);
      const h = Math.max(2, base - top);
      const r = Math.min(4, h / 2);
      // Barra con gli angoli arrotondati solo in alto, appoggiata alla base.
      const d = `M${cx - bw / 2},${base} V${top + r} Q${cx - bw / 2},${top} ${cx - bw / 2 + r},${top} H${cx + bw / 2 - r} Q${cx + bw / 2},${top} ${cx + bw / 2},${top + r} V${base} Z`;
      const cls = c.channel === b.recommended ? "rec" : c.preferred ? "pref" : "";
      const showVal = c.preferred || c.channel === b.current || c.channel === b.recommended;
      const ring = c.channel === b.current && c.channel !== b.recommended
        ? `<rect class="bar-ring" x="${cx - bw / 2 - 3}" y="${top - 3}" width="${bw + 6}" height="${base - top + 3}" rx="6"/>` : "";
      return `<g><path class="bar-n ${cls}" data-i="${i}" d="${d}"/>${ring}
        ${showVal ? `<text class="bar-val" x="${cx}" y="${top - 7}" text-anchor="middle">${c.score}</text>` : ""}
        <text class="tick ${c.channel === b.current || c.channel === b.recommended ? "on" : ""}" x="${cx}" y="${H - B + 18}" text-anchor="middle">${c.channel}</text>
        <rect class="hit" data-i="${i}" x="${cx - step / 2}" y="${T}" width="${step}" height="${H - T - B}"/></g>`;
    }).join("");

    return `<div class="section-head"><div><h3>${this.t("scores")}</h3><p>${this.t("scoresSub")}</p></div>
        <div class="spacer"></div>
        <div class="legend"><span><i style="background:var(--wa-own);height:10px;width:10px;border-radius:3px"></i>${this.t("recommendedShort")}</span>
        <span><i style="background:var(--wa-neutral-strong);height:10px;width:10px;border-radius:3px"></i>${esc((chans.filter((c) => c.preferred).map((c) => c.channel)).slice(0, 6).join(" · "))}${chans.filter((c) => c.preferred).length > 6 ? " …" : ""}</span>
        <span><i style="border:1.5px solid var(--wa-ink);height:10px;width:10px;border-radius:3px;background:none"></i>${this.t("currentShort")}</span></div>
      </div>
      <div class="chart" id="scores">
        <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${this.t("scores")}">${grid}
          <line class="baseline" x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}"/>${bars}</svg>
        <div class="tip" id="score-tip"></div>
      </div>`;
  }

  _bindScores() {
    const root = this.shadowRoot;
    const chart = root.getElementById("scores");
    const tip = root.getElementById("score-tip");
    if (!chart) return;
    const chans = this._scoreGeo.chans;
    chart.querySelectorAll("rect.hit").forEach((r) => {
      r.addEventListener("pointermove", (ev) => {
        const c = chans[+r.dataset.i];
        chart.querySelectorAll(".bar-n").forEach((b) => b.classList.toggle("hot", b.dataset.i === r.dataset.i));
        this._showTip(tip, chart, ev, `
          <div class="t-val">${c.score}</div>
          <div class="t-name">${this.t("channel")} ${c.channel}${c.dfs ? " · DFS" : ""}</div>
          <dl>
            <dt>${this.t("worst")}</dt><dd>${c.worst_score}</dd>
            <dt>${this.t("networksOn")}</dt><dd>${c.networks}</dd>
          </dl>`);
      });
      r.addEventListener("pointerleave", () => {
        tip.classList.remove("show");
        chart.querySelectorAll(".bar-n.hot").forEach((b) => b.classList.remove("hot"));
      });
    });
  }

  // ------------------------------------------------------------ elenchi

  _neighborsHtml() {
    const nets = (this._bandData().neighbors || []);
    return `<div class="section-head"><div><h3>${this.t("neighborList")}</h3></div></div>
      ${nets.length ? `<div class="table-scroll"><table>
        <thead><tr><th>${this.t("ssid")}</th><th class="num">${this.t("channel")}</th><th class="num">${this.t("signal")}</th><th class="num">${this.t("seenBy")}</th></tr></thead>
        <tbody>${nets.slice(0, 40).map((n) => `<tr>
          <td><div class="ssid">${esc(n.ssid || this.t("hidden"))}</div><div class="mono">${esc(n.bssid)}</div></td>
          <td class="num">${n.channel}</td>
          <td class="num">${signalBars(n.rssi)}${n.rssi} dBm</td>
          <td class="num">${Object.keys(n.seen_by || {}).length}</td></tr>`).join("")}</tbody></table></div>`
        : `<p class="muted">${this.t("none")}</p>`}`;
  }

  _ownApsHtml() {
    const aps = (this._data.own_aps || []).filter((a) => !a.channel || (this._band === "2.4" ? a.channel <= 14 : a.channel > 14));
    return `<div class="section-head"><div><h3>${this.t("ownAps")}</h3><p>${esc((this._data.own_ssids || []).join(" · "))}</p></div></div>
      <div class="aps">${aps.length ? aps.map((a) => `<div class="ap">
        ${icon("ap")}
        <div class="name">${esc(a.ssid || this.t("hidden"))}${a.channel ? ` · ${this.t("channel")} ${a.channel}` : ""}</div>
        <div class="count">${a.devices}<small>${this.t("apDevices")}</small></div>
        <div class="meta"><span class="mono">${esc(a.bssid)}</span>${a.weak ? ` · ${this.t("weakN", { n: a.weak })}` : ""}</div>
      </div>`).join("") : `<p class="muted">${this.t("none")}</p>`}</div>`;
  }

  _devicesHtml() {
    const devs = this._data.devices || [];
    const order = ["excellent", "good", "fair", "weak", "unknown"];
    const counts = Object.fromEntries(order.map((q) => [q, devs.filter((d) => d.quality === q).length]));
    const total = devs.length || 1;
    const apName = new Map((this._data.own_aps || []).map((a, i) => [a.bssid, `AP ${i + 1}`]));
    return `<div class="section-head"><div><h3>${this.t("devicesTitle")}</h3><p>${this.t("devicesSub")}</p></div></div>
      <div class="qbar" role="img" aria-label="${order.map((q) => `${this.t(`q_${q}`)} ${counts[q]}`).join(", ")}">
        ${order.filter((q) => counts[q]).map((q) => `<span style="width:${(counts[q] / total) * 100}%;background:${qualityColor(q)}"></span>`).join("")}
      </div>
      <div class="qlegend">${order.filter((q) => counts[q]).map((q) => `<span><i style="background:${qualityColor(q)}"></i>${this.t(`q_${q}`)} <b>${counts[q]}</b></span>`).join("")}</div>
      <div class="filters">
        ${["all", "weak", "offline"].map((f) => `<button class="chip" data-dev="${f}" aria-pressed="${this._devFilter === f}">${this.t(f)}</button>`).join("")}
        <input class="search" id="dev-search" type="search" placeholder="${this.t("search")}" value="${esc(this._devSearch)}">
      </div>
      <div class="dev-list" id="dev-list">${this._devListHtml(apName)}</div>`;
  }

  _devListHtml(apName) {
    const q = this._devSearch.trim().toLowerCase();
    const devs = (this._data.devices || []).filter((d) => {
      if (this._devFilter === "weak" && d.quality !== "weak") return false;
      if (this._devFilter === "offline" && d.available) return false;
      return !q || `${d.name} ${d.area || ""}`.toLowerCase().includes(q);
    });
    if (!devs.length) return `<p class="muted">${this.t("none")}</p>`;
    return devs.map((d) => {
      const pct = d.rssi == null ? 0 : Math.max(4, Math.min(100, ((d.rssi + 95) / 55) * 100));
      const meta = [d.area, apName.get(d.bssid), d.band ? `${d.band} GHz` : null].filter(Boolean).join(" · ");
      return `<div class="dev ${d.available ? "" : "off"}">
        <div class="n" title="${esc(d.name)}">${esc(d.name)}</div>
        <div class="r">${d.available ? (d.rssi != null ? `${d.rssi} dBm` : "—") : icon("off")}</div>
        <div class="m">${esc(meta || d.source)}</div>
        <div>${d.available ? this._statusHtml(d.quality) : this._statusHtml("unknown", this.t("offline"))}</div>
        <div class="meter">${d.available ? `<i style="width:${pct}%;background:${qualityColor(d.quality)}"></i>` : ""}</div>
      </div>`;
    }).join("");
  }

  _bindDevices() {
    const root = this.shadowRoot;
    const apName = new Map((this._data.own_aps || []).map((a, i) => [a.bssid, `AP ${i + 1}`]));
    const refresh = () => { root.getElementById("dev-list").innerHTML = this._devListHtml(apName); };
    root.querySelectorAll("[data-dev]").forEach((b) => b.addEventListener("click", () => {
      this._devFilter = b.dataset.dev;
      root.querySelectorAll("[data-dev]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      refresh();
    }));
    root.getElementById("dev-search")?.addEventListener("input", (ev) => { this._devSearch = ev.target.value; refresh(); });
  }

  _probesHtml() {
    const d = this._data;
    const results = new Map((d.last_scan?.probes || []).map((p) => [p.id, p]));
    const n = d.probes.filter((p) => p.selected).length;
    const secs = n ? n * 3 + (n - 1) * 2 : 0;
    const dis = this._running || this._savingProbes ? "disabled" : "";
    return `<div class="section-head"><div><h3>${this.t("probes")}</h3><p>${this.t("probesSub")}</p></div></div>
      ${!n ? `<div class="warn-line">${icon("alert")}${this.t("noProbesSelected")}</div>` : ""}
      <div class="probe-actions">
        <button class="chip" data-sel="all" ${dis}>${this.t("selAll")}</button>
        <button class="chip" data-sel="suggested" ${dis}>${this.t("selSuggested")}</button>
        <button class="chip" data-sel="none" ${dis}>${this.t("selNone")}</button>
        <span class="count">${this.t("selCount", { n, total: d.probes.length, s: secs })}</span>
      </div>
      <div class="probe-grid">${d.probes.map((p) => {
        const r = results.get(p.id);
        const status = r ? (r.ok ? this.t("probeOk", { n: r.networks, s: r.duration }) : `<span class="err">${esc(r.error)}</span>`) : "";
        return `<button class="probe ${p.selected ? "on" : ""}" data-id="${esc(p.id)}" role="switch" aria-checked="${p.selected}" ${dis}>
          <div class="pi">${icon(p.kind === "host" ? "server" : "chip")}</div>
          <div class="grow"><div class="pn">${esc(p.name)}</div>
          <div class="pm">${esc([p.kind === "host" ? this.t("probeHost") : this.t("probeShelly"), p.area, p.rssi != null ? `${p.rssi} dBm` : null].filter(Boolean).join(" · "))}</div>
          ${status ? `<div class="pm">${status}</div>` : ""}</div>
          <span class="switch" aria-hidden="true"></span>
        </button>`;
      }).join("")}</div>`;
  }

  _bindProbes() {
    const root = this.shadowRoot;
    const save = async (ids) => {
      if (this._running || this._savingProbes) return;
      this._savingProbes = true;
      // Aggiornamento immediato a schermo, poi conferma dal server.
      const set = new Set(ids);
      this._data.probes.forEach((p) => { p.selected = set.has(p.id); });
      this._render();
      try {
        this._data = await this._ws("set_probes", { probes: ids });
      } catch (err) {
        this._error = err.message || String(err);
      }
      this._savingProbes = false;
      this._render();
    };
    root.querySelectorAll(".probe[data-id]").forEach((b) => b.addEventListener("click", () => {
      const ids = this._data.probes.filter((p) => p.selected).map((p) => p.id);
      const id = b.dataset.id;
      save(ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]);
    }));
    root.querySelectorAll("[data-sel]").forEach((b) => b.addEventListener("click", () => {
      const all = this._data.probes.map((p) => p.id);
      save({ all, none: [], suggested: this._data.suggested_probes || [] }[b.dataset.sel]);
    }));
  }
}

customElements.define("wifi-analyzer-panel", WifiAnalyzerPanel);
