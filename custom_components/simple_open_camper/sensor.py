"""Messwerte vom Panel (Akku, Victron, Gas, Temperaturen, Tanks …)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SocEntity, items_of_kind

# Klassen vom Panel -> HA (nur die, deren Einheiten HA sicher akzeptiert)
DEVICE_CLASS = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "voltage": SensorDeviceClass.VOLTAGE,
    "current": SensorDeviceClass.CURRENT,
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "pressure": SensorDeviceClass.PRESSURE,
    "carbon_dioxide": SensorDeviceClass.CO2,
}
UNITS_OK = {
    SensorDeviceClass.TEMPERATURE: {"°C", "°F"},
    SensorDeviceClass.HUMIDITY: {"%"},
    SensorDeviceClass.VOLTAGE: {"V", "mV"},
    SensorDeviceClass.CURRENT: {"A", "mA"},
    SensorDeviceClass.POWER: {"W", "kW"},
    SensorDeviceClass.ENERGY: {"Wh", "kWh"},
    SensorDeviceClass.PRESSURE: {"hPa", "Pa", "kPa", "bar", "mbar", "psi"},
    SensorDeviceClass.CO2: {"ppm"},
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add(SocSensor(hass, entry, i, v) for i, v in items_of_kind(entry, "sensor").items())


class SocSensor(SocEntity, SensorEntity):
    def __init__(self, hass, entry, item_id, item) -> None:
        super().__init__(hass, entry, item_id, item)
        unit = item.get("u") or None
        dc = DEVICE_CLASS.get(item.get("c", ""))
        if dc and unit not in UNITS_OK.get(dc, set()):
            dc = None
        self._attr_device_class = dc
        self._attr_native_unit_of_measurement = unit
        if unit:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        v = self.value.get("v")
        if self._attr_native_unit_of_measurement and not isinstance(v, (int, float)):
            return None   # Messwert mit Einheit: nur Zahlen
        return v
