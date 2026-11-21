# Simple Open Camper – Home Assistant Integration *(Beta)*

Connects [Simple Open Camper](https://github.com/cyclemat/simple-open-camper) panels with Home Assistant – in **both
directions**, and each side only gets what you select:

- **Panel → Home Assistant:** choose which panel values HA takes over – lights and switches (Zigbee, Shelly, WLED …),
  batteries, Victron, gas, satellite tanks and temperatures. They show up as sensors, binary sensors, switches and lights,
  grouped like on the panel.
- **Home Assistant → Panel:** choose HA entities (lights, switches, sensors, binary sensors …) that the panel should
  show. They appear on the panel like a satellite "Home Assistant" (one group per area) and can be placed as tiles,
  used in rules, the app and the live view.

One local WebSocket connection (`ws://<panel>/api/ha`), push-based, no MQTT broker and no cloud needed. Works over the
LAN or over **Tailscale** (e.g. with the Tailscale add-on in HA) when the panel is somewhere else.

**No loops:** values the panel receives from HA are never offered back to HA, and entities created by this integration
cannot be provided to the panel.

## Installation

**HACS (custom repository):** HACS → ⋮ → *Custom repositories* → `https://github.com/cyclemat/simple-open-camper-HA-Integration`,
type *Integration* → install → restart Home Assistant.

**Manually:** copy `custom_components/simple_open_camper` to `config/custom_components/` and restart Home Assistant.

## Setup

1. On the panel (browser editor): **Settings → Network → Home Assistant** – switch on *"Allow Home Assistant to connect"*
   and copy the **access code**.
2. In Home Assistant: **Settings → Devices & services → Add integration → Simple Open Camper**. Enter the panel's
   address (LAN IP, Tailscale IP or tailnet name) and the access code.
3. Open the integration's **Configure**:
   - step 1 – tick the panel values HA should take over,
   - step 2 – pick the HA entities the panel should show.

Requires panel firmware **0.2.7** or newer (P4, round panel, Waveshare).

---

## Deutsch (Kurzfassung)

Verbindet Simple-Open-Camper-Panels mit Home Assistant – in beide Richtungen, jede Seite bekommt nur das Ausgewählte.
Am Panel im Editor unter **Einstellungen → Netzwerk → Home Assistant** einschalten und den **Zugangscode** kopieren; in HA
die Integration **Simple Open Camper** hinzufügen (Adresse des Panels + Zugangscode). Unter **Konfigurieren** wählst du,
welche Panel-Werte HA übernimmt und welche HA-Entitäten das Panel zeigt. Lokal per WebSocket, auch über Tailscale.

## License

MIT – see [LICENSE](LICENSE). The panel firmware itself is a separate project with its own license.
