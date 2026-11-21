"""Simple Open Camper – Panel und Home Assistant tauschen ausgewaehlte Werte aus (WebSocket, lokal/Tailscale)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .client import PanelClient
from .const import CONF_EXPOSE, CONF_PANEL_ITEMS, CONF_TOKEN, DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = PanelClient(hass, entry.entry_id, entry.data[CONF_HOST], entry.data[CONF_TOKEN])
    items: dict = entry.options.get(CONF_PANEL_ITEMS, {})
    client.set_subscriptions(list(items))
    client.set_expose(entry.options.get(CONF_EXPOSE, []))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    client.start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    client: PanelClient | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if client:
        await client.stop()
    return ok
