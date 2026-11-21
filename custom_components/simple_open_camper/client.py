"""WebSocket-Verbindung zum Simple-Open-Camper-Panel (ws://<panel>/api/ha).

Ablauf: hello (Zugangscode) -> ok; list -> Katalog der Panel-Werte; sub -> nur ausgewaehlte Werte kommen bei Aenderung;
cmd -> schalten/dimmen. Umgekehrt: ents/hst -> bereitgestellte HA-Entitaeten und ihre Zustaende; call <- Kachel am Panel.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import SIGNAL_AVAILABLE, SIGNAL_VALUE

_LOGGER = logging.getLogger(__name__)


class PanelError(Exception):
    """Panel nicht erreichbar oder Zugangscode falsch."""


def ws_url(host: str) -> str:
    host = host.strip().removeprefix("http://").removeprefix("ws://").rstrip("/")
    return f"ws://{host}/api/ha"


async def probe(hass: HomeAssistant, host: str, token: str) -> dict[str, Any]:
    """Einmal verbinden und anmelden (fuer die Einrichtung). Liefert {'name','ver'}."""
    session = async_get_clientsession(hass)
    try:
        async with session.ws_connect(ws_url(host), timeout=aiohttp.ClientWSTimeout(ws_close=10), heartbeat=20) as ws:
            await ws.send_str(json.dumps({"t": "hello", "tok": token, "name": hass.config.location_name}))
            msg = await asyncio.wait_for(ws.receive(), timeout=10)
            if msg.type != aiohttp.WSMsgType.TEXT:
                raise PanelError("cannot_connect")
            data = json.loads(msg.data)
            if data.get("t") != "ok":
                raise PanelError("invalid_auth")
            return data
    except PanelError:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
        raise PanelError("cannot_connect") from err


class PanelClient:
    """Dauerhafte Verbindung mit automatischem Neuaufbau."""

    def __init__(self, hass: HomeAssistant, entry_id: str, host: str, token: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.host = host
        self.token = token
        self.connected = False
        self.panel_name = ""
        self.catalog: dict[str, dict] = {}
        self.values: dict[str, dict] = {}
        self._subs: list[str] = []
        self._expose: list[str] = []
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._task: asyncio.Task | None = None
        self._catalog_event = asyncio.Event()
        self._unsub_state = None

    # ---- Steuerung
    def start(self) -> None:
        self._task = self.hass.async_create_background_task(self._run(), f"simple_open_camper_{self.entry_id}")

    async def stop(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._task:
            self._task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()

    def set_subscriptions(self, ids: list[str]) -> None:
        self._subs = list(ids)

    def set_expose(self, entity_ids: list[str]) -> None:
        self._expose = list(entity_ids)
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._expose:
            self._unsub_state = async_track_state_change_event(self.hass, self._expose, self._on_state_change)

    async def async_get_catalog(self, timeout: float = 10) -> dict[str, dict]:
        """Katalog frisch vom Panel holen (Optionen-Dialog)."""
        if not self.connected:
            return self.catalog
        self._catalog_event.clear()
        await self._send({"t": "list"})
        try:
            await asyncio.wait_for(self._catalog_event.wait(), timeout)
        except asyncio.TimeoutError:
            pass
        return self.catalog

    async def command(self, item_id: str, on: bool | None = None, bri: int | None = None) -> None:
        msg: dict[str, Any] = {"t": "cmd", "id": item_id}
        if on is not None:
            msg["on"] = on
        if bri is not None:
            msg["bri"] = max(0, min(100, int(bri)))
        await self._send(msg)

    # ---- intern
    async def _send(self, msg: dict) -> None:
        if self._ws and not self._ws.closed:
            await self._ws.send_str(json.dumps(msg, ensure_ascii=False))

    def _set_connected(self, on: bool) -> None:
        if self.connected != on:
            self.connected = on
            async_dispatcher_send(self.hass, SIGNAL_AVAILABLE.format(self.entry_id))

    async def _run(self) -> None:
        session = async_get_clientsession(self.hass)
        delay = 5
        while True:
            try:
                async with session.ws_connect(ws_url(self.host), heartbeat=30) as ws:
                    self._ws = ws
                    await ws.send_str(json.dumps({"t": "hello", "tok": self.token, "name": self.hass.config.location_name}))
                    first = await asyncio.wait_for(ws.receive(), timeout=15)
                    data = json.loads(first.data) if first.type == aiohttp.WSMsgType.TEXT else {}
                    if data.get("t") != "ok":
                        _LOGGER.warning("Panel %s lehnt die Anmeldung ab (Zugangscode?)", self.host)
                        await asyncio.sleep(60)
                        continue
                    self.panel_name = data.get("name", "")
                    self._set_connected(True)
                    delay = 5
                    await self._send({"t": "list"})
                    await self._send({"t": "sub", "ids": self._subs})
                    await self._send_exposed()
                    async for msg in ws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            break
                        await self._handle(json.loads(msg.data))
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 – jede Stoerung: neu verbinden
                _LOGGER.debug("Verbindung zum Panel %s: %s", self.host, err)
            self._ws = None
            self._set_connected(False)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    async def _handle(self, m: dict) -> None:
        t = m.get("t")
        if t == "list":
            self.catalog = {i["id"]: i for i in m.get("items", []) if "id" in i}
            self._catalog_event.set()
        elif t == "st":
            for item_id, val in m.get("v", {}).items():
                self.values[item_id] = val
                async_dispatcher_send(self.hass, SIGNAL_VALUE.format(self.entry_id, item_id))
        elif t == "call":
            entity_id = m.get("id", "")
            if entity_id in self._expose:   # nur Bereitgestelltes darf das Panel schalten
                service = "turn_on" if m.get("on") else "turn_off"
                await self.hass.services.async_call("homeassistant", service, {"entity_id": entity_id}, blocking=False)

    def _entity_info(self, entity_id: str) -> dict[str, Any]:
        st = self.hass.states.get(entity_id)
        ent_reg, dev_reg, area_reg = er.async_get(self.hass), dr.async_get(self.hass), ar.async_get(self.hass)
        entry = ent_reg.async_get(entity_id)
        area_id = entry.area_id if entry else None
        if not area_id and entry and entry.device_id:
            dev = dev_reg.async_get(entry.device_id)
            area_id = dev.area_id if dev else None
        area = area_reg.async_get_area(area_id).name if area_id and area_reg.async_get_area(area_id) else ""
        attrs = st.attributes if st else {}
        return {
            "id": entity_id,
            "n": attrs.get("friendly_name", entity_id),
            "dom": entity_id.split(".", 1)[0],
            "u": attrs.get("unit_of_measurement", "") or "",
            "c": attrs.get("device_class", "") or "",
            "area": area,
        }

    def _state_of(self, entity_id: str) -> dict[str, Any]:
        st = self.hass.states.get(entity_id)
        if st is None:
            return {"s": "unavailable", "av": False}
        out: dict[str, Any] = {"s": st.state}
        if st.state in ("unavailable", "unknown"):
            out["av"] = False
        bri = st.attributes.get("brightness")
        if bri is not None:
            out["bri"] = round(bri * 100 / 255)
        return out

    async def _send_exposed(self) -> None:
        await self._send({"t": "ents", "list": [self._entity_info(e) for e in self._expose]})
        if self._expose:
            await self._send({"t": "hst", "v": {e: self._state_of(e) for e in self._expose}})

    @callback
    def _on_state_change(self, event: Event) -> None:
        entity_id = event.data["entity_id"]
        self.hass.async_create_task(self._send({"t": "hst", "v": {entity_id: self._state_of(entity_id)}}))
