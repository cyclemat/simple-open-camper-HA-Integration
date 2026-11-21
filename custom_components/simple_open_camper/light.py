"""Lampen vom Panel (Zigbee, WLED …): ein/aus und – wenn dimmbar – Helligkeit."""
from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SocEntity, items_of_kind


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add(SocLight(hass, entry, i, v) for i, v in items_of_kind(entry, "light").items())


class SocLight(SocEntity, LightEntity):
    def __init__(self, hass, entry, item_id, item) -> None:
        super().__init__(hass, entry, item_id, item)
        mode = ColorMode.BRIGHTNESS if item.get("b") else ColorMode.ONOFF
        self._attr_supported_color_modes = {mode}
        self._attr_color_mode = mode

    @property
    def is_on(self) -> bool | None:
        on = self.value.get("on")
        return None if on is None else bool(on)

    @property
    def brightness(self) -> int | None:
        bri = self.value.get("bri")
        return None if bri is None else round(bri * 255 / 100)

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_BRIGHTNESS in kwargs and self.item.get("b"):
            await self.client.command(self.item_id, bri=round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))
        else:
            await self.client.command(self.item_id, on=True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.client.command(self.item_id, on=False)
