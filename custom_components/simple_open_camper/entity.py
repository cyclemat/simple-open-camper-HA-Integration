"""Gemeinsame Basis: ein HA-Entity je ausgewaehltem Panel-Wert, Geraete nach Gruppe auf dem Panel."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .client import PanelClient
from .const import CONF_PANEL_ITEMS, DOMAIN, SIGNAL_AVAILABLE, SIGNAL_VALUE


def items_of_kind(entry: ConfigEntry, *kinds: str) -> dict[str, dict]:
    return {i: v for i, v in entry.options.get(CONF_PANEL_ITEMS, {}).items() if v.get("k") in kinds}


class SocEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, item_id: str, item: dict) -> None:
        self.client: PanelClient = hass.data[DOMAIN][entry.entry_id]
        self._entry = entry
        self.item_id = item_id
        self.item = item
        self._attr_unique_id = f"{entry.entry_id}_{item_id}"
        self._attr_name = item.get("n", item_id)
        group = item.get("g") or entry.title
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{group}")},
            name=group,
            manufacturer="Simple Open Camper",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def value(self) -> dict[str, Any]:
        return self.client.values.get(self.item_id, {})

    @property
    def available(self) -> bool:
        return self.client.connected and self.value.get("av", True) is not False

    async def async_added_to_hass(self) -> None:
        # Panel selbst als Geraet (Elternteil der Gruppen)
        from homeassistant.helpers import device_registry as dr
        dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self._entry.entry_id, identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title, manufacturer="Simple Open Camper", model="Panel")
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_VALUE.format(self._entry.entry_id, self.item_id), self._updated))
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_AVAILABLE.format(self._entry.entry_id), self._updated))

    @callback
    def _updated(self) -> None:
        self.async_write_ha_state()
