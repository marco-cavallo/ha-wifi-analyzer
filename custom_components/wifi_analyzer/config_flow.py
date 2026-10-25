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
"""Configurazione guidata di Wi-Fi Analyzer.

Wi-Fi Analyzer - By Marco Cavallo.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .analysis import CHANNEL_PLANS_24, DEFAULT_PLAN_24
from .const import (
    CONF_CHANNEL_PLAN,
    CONF_OWN_SSIDS,
    CONF_PANEL,
    CONF_PROBES,
    CONF_SCAN_HOURS,
    DEFAULT_PANEL,
    DEFAULT_SCAN_HOURS,
    DEFAULT_SHELLY_PROBES,
    DOMAIN,
    INTEGRATION_NAME,
    PROBE_HOST,
)
from .probes import Probe, async_discover, default_probes


def _probe_label(probe: Probe) -> str:
    parts = [probe.name]
    if probe.area:
        parts.append(f"· {probe.area}")
    if probe.rssi is not None:
        parts.append(f"· {probe.rssi} dBm")
    if probe.kind == PROBE_HOST:
        parts.append("· 2,4 + 5 GHz")
    return " ".join(parts)


def _probe_selector(probes: list[Probe]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=p.probe_id, label=_probe_label(p))
                for p in probes
            ],
            multiple=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


class WifiAnalyzerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configurazione iniziale: una sola istanza per casa."""

    VERSION = 1

    def __init__(self) -> None:
        self._probes: list[Probe] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=INTEGRATION_NAME,
                data={},
                options={
                    CONF_PROBES: user_input.get(CONF_PROBES, []),
                    CONF_SCAN_HOURS: DEFAULT_SCAN_HOURS,
                    CONF_CHANNEL_PLAN: DEFAULT_PLAN_24,
                    CONF_OWN_SSIDS: [],
                    CONF_PANEL: DEFAULT_PANEL,
                },
            )

        self._probes = await async_discover(self.hass)
        if not self._probes:
            return self.async_abort(reason="no_probes")

        hosts = sum(1 for p in self._probes if p.kind == PROBE_HOST)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PROBES,
                        default=default_probes(self._probes, DEFAULT_SHELLY_PROBES),
                    ): _probe_selector(self._probes),
                }
            ),
            description_placeholders={
                "count": str(len(self._probes)),
                "shelly": str(len(self._probes) - hosts),
                "host": str(hosts),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> WifiAnalyzerOptionsFlow:
        return WifiAnalyzerOptionsFlow()


class WifiAnalyzerOptionsFlow(OptionsFlow):
    """Opzioni: sonde, reti di casa, scansioni automatiche."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_SCAN_HOURS] = int(user_input.get(CONF_SCAN_HOURS, 0))
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        probes = await async_discover(self.hass)
        known = {p.probe_id for p in probes}
        # Una sonda scelta ma spenta adesso resta nell'elenco, altrimenti
        # salvando le opzioni sparirebbe dalla selezione.
        selected = options.get(CONF_PROBES, [])
        probes.extend(
            Probe(probe_id=pid, kind=pid.split(":", 1)[0], name=pid)
            for pid in selected if pid not in known
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_PROBES, default=selected): _probe_selector(probes),
                vol.Optional(
                    CONF_OWN_SSIDS, default=options.get(CONF_OWN_SSIDS, [])
                ): selector.TextSelector(selector.TextSelectorConfig(multiple=True)),
                vol.Optional(
                    CONF_SCAN_HOURS,
                    default=options.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=168, step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="h",
                    )
                ),
                vol.Optional(
                    CONF_CHANNEL_PLAN,
                    default=options.get(CONF_CHANNEL_PLAN, DEFAULT_PLAN_24),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(CHANNEL_PLANS_24),
                        translation_key=CONF_CHANNEL_PLAN,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PANEL, default=options.get(CONF_PANEL, DEFAULT_PANEL)
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
