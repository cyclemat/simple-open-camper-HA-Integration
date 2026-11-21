"""Eingaenge vom Panel (Tuerkontakte, Schwimmerschalter, Satelliten-Eingaenge …)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SocEntity, items_of_kind


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add(SocBinary(hass, entry, i, v) for i, v in items_of_kind(entry, "binary").items())


class SocBinary(SocEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        on = self.value.get("on")
        return None if on is None else bool(on)
