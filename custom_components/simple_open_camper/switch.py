"""Schalter vom Panel (Steckdosen, Relais der Satelliten, Shelly …)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SocEntity, items_of_kind


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add(SocSwitch(hass, entry, i, v) for i, v in items_of_kind(entry, "switch").items())


class SocSwitch(SocEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        on = self.value.get("on")
        return None if on is None else bool(on)

    async def async_turn_on(self, **kwargs) -> None:
        await self.client.command(self.item_id, on=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.client.command(self.item_id, on=False)
