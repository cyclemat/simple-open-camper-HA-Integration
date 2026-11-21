"""Einrichtung (Adresse + Zugangscode) und Optionen (was HA uebernimmt / was das Panel bekommt)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .client import PanelClient, PanelError, probe
from .const import CONF_EXPOSE, CONF_PANEL_ITEMS, CONF_TOKEN, DOMAIN, EXPOSE_DOMAINS


class SocConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                info = await probe(self.hass, host, user_input[CONF_TOKEN].strip())
            except PanelError as err:
                errors["base"] = str(err)
            else:
                await self.async_set_unique_id(host.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info.get("name") or "Simple Open Camper",
                                               data={CONF_HOST: host, CONF_TOKEN: user_input[CONF_TOKEN].strip()})
        schema = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SocOptionsFlow()


class SocOptionsFlow(config_entries.OptionsFlow):
    """Schritt 1: Werte vom Panel waehlen. Schritt 2: HA-Entitaeten fuer das Panel waehlen."""

    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._catalog: dict[str, dict] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        client: PanelClient | None = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        current: dict = self.config_entry.options.get(CONF_PANEL_ITEMS, {})
        if user_input is not None:
            chosen = user_input.get("items", [])
            self._items = {i: (self._catalog.get(i) or current.get(i)) for i in chosen if (self._catalog.get(i) or current.get(i))}
            return await self.async_step_expose()
        self._catalog = await client.async_get_catalog() if client else {}
        if not self._catalog and not current:
            return self.async_abort(reason="not_connected")
        names = {i: f"{v.get('g', '')} – {v.get('n', i)}" for i, v in {**current, **self._catalog}.items()}
        names = dict(sorted(names.items(), key=lambda kv: kv[1].lower()))
        schema = vol.Schema({vol.Optional("items", default=[i for i in current if i in names]): cv.multi_select(names)})
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_expose(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(data={CONF_PANEL_ITEMS: self._items, CONF_EXPOSE: user_input.get(CONF_EXPOSE, [])})
        # eigene Entitaeten (vom Panel uebernommen) nicht zurueck ans Panel geben – kein Kreislauf
        own = [e.entity_id for e in er.async_entries_for_config_entry(er.async_get(self.hass), self.config_entry.entry_id)]
        schema = vol.Schema({
            vol.Optional(CONF_EXPOSE, default=self.config_entry.options.get(CONF_EXPOSE, [])): EntitySelector(
                EntitySelectorConfig(domain=EXPOSE_DOMAINS, multiple=True, exclude_entities=own)),
        })
        return self.async_show_form(step_id="expose", data_schema=schema)
