"""Konstanten der Integration Simple Open Camper."""

DOMAIN = "simple_open_camper"

CONF_TOKEN = "token"
CONF_PANEL_ITEMS = "panel_items"   # {id: Katalog-Eintrag} – vom Panel uebernommene Werte
CONF_EXPOSE = "expose"             # [entity_id] – dem Panel bereitgestellte HA-Entitaeten

SIGNAL_VALUE = f"{DOMAIN}_value_{{}}_{{}}"       # .format(entry_id, item_id)
SIGNAL_AVAILABLE = f"{DOMAIN}_available_{{}}"    # .format(entry_id)

# HA-Bereiche, die das Panel als Kachel zeigen kann
EXPOSE_DOMAINS = ["light", "switch", "input_boolean", "fan", "sensor", "binary_sensor", "number", "input_number"]

PLATFORMS = ["sensor", "binary_sensor", "switch", "light"]
