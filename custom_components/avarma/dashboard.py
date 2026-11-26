"""Stellt das Dashboard „Wärmepumpe“ bereit (YAML-Dashboard aus der Integration).

Das Dashboard wird mit jeder neuen Version der Integration automatisch aktualisiert.
Wer es selbst anpassen möchte, schaltet die Option aus und legt sich eine eigene Kopie an
(Inhalt: homeassistant/dashboards/waermepumpe.yaml im Repository).
"""

from __future__ import annotations

import inspect
import logging
import os

from homeassistant.components import frontend, persistent_notification
from homeassistant.components.lovelace import dashboard as ll_dashboard
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant, callback

_LOGGER = logging.getLogger(__name__)

URL_PATH = "waermepumpe"
TITLE = "Wärmepumpe"
ICON = "mdi:heat-pump"
FILE = os.path.join(os.path.dirname(__file__), "dashboard.yaml")
GEN_NAME = "avarma.dashboard.yaml"  # gefilterte Fassung (nur die gewählten Seiten) in <config>/.storage/


WETTER = "weather.avarma_wetter"  # Platzhalter im Dashboard für die Wetter-Entität aus den Optionen


def _wetter(node, ent: str | None):
    """Platzhalter durch die gewählte Wetter-Entität ersetzen; ohne Wetter-Entität die Karte weglassen."""
    if isinstance(node, list):
        return [x for x in (_wetter(n, ent) for n in node) if x is not None]
    if isinstance(node, dict):
        if "avarma_ohne_wetter" in node:
            if ent:
                return None
            node = {k: v for k, v in node.items() if k != "avarma_ohne_wetter"}
        if node.get("entity") == WETTER:
            if not ent:
                return None
            node = dict(node, entity=ent)
        return {k: _wetter(v, ent) for k, v in node.items()}
    return node


OHNE_NAMEN = ("markdown", "logbook", "weather-forecast", "heading", "map")  # Karten ohne Namen je Entität


def _namen(node, namen: dict[str, str]):
    """In den Karten den Namen ohne Gerät („WP“) davor eintragen, wo keiner angegeben ist.

    Seit Home Assistant 2026.10 setzt HA den Gerätenamen immer vor den Entitätsnamen.
    """
    if isinstance(node, list):
        return [_namen(n, namen) for n in node]
    if not isinstance(node, dict):
        return node
    node = dict(node)
    for k in ("views", "sections", "cards", "card"):
        if k in node:
            node[k] = _namen(node[k], namen)
    typ = node.get("type", "")
    if not typ or typ.startswith("custom:") or typ in OHNE_NAMEN:
        return node
    if node.get("entity") in namen and "name" not in node:
        node["name"] = namen[node["entity"]]
    if isinstance(node.get("entities"), list):
        ents = []
        for e in node["entities"]:
            if isinstance(e, str) and e in namen:
                e = {"entity": e, "name": namen[e]}
            elif isinstance(e, dict) and "type" not in e and "name" not in e and e.get("entity") in namen:
                e = dict(e, name=namen[e["entity"]])
            ents.append(e)
        node["entities"] = ents
    return node


@callback
def kurznamen(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Entity-ID → Name ohne Gerät davor (eigener Name aus HA hat Vorrang)."""
    from homeassistant.helpers import entity_registry as er

    return {e.entity_id: e.name or e.original_name
            for e in er.async_entries_for_config_entry(er.async_get(hass), entry_id) if e.name or e.original_name}


def write_filtered(hass: HomeAssistant, pages: list[str] | None, known: list[str] | None = None,
                   wetter: str | None = None, namen: dict[str, str] | None = None) -> str:
    """Mitgeliefertes Dashboard ohne abgewählte Seiten nach .storage schreiben (blockierend, im Executor aufrufen).

    Abgewählt ist nur, was es beim Speichern der Optionen schon gab (`known`); neue Seiten erscheinen zunächst.
    """
    import yaml

    from .const import PAGES, PAGES_V1

    with open(FILE, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    weg = set() if pages is None else (set(known or PAGES_V1) & set(PAGES)) - set(pages)
    cfg["views"] = _namen(_wetter([v for v in cfg.get("views", []) if v.get("path") not in weg], wetter), namen or {})
    path = hass.config.path(".storage", GEN_NAME)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Automatisch erzeugt von der Avarma-Integration (Optionen → Seiten im Dashboard). Nicht bearbeiten.\n")
        yaml.safe_dump(cfg, fh, allow_unicode=True, sort_keys=False, width=4000)
    return path


def _ours(hass: HomeAssistant, dash) -> bool:
    return getattr(dash, "path", None) in (FILE, hass.config.path(".storage", GEN_NAME))


@callback
def async_register_dashboard(hass: HomeAssistant, filename: str = FILE) -> bool:
    ll = hass.data.get(LOVELACE_DATA)
    if ll is None:
        _LOGGER.warning("Lovelace ist nicht geladen – Dashboard wird nicht angelegt")
        return False
    existing = ll.dashboards.get(URL_PATH)
    panels = hass.data.get(frontend.DATA_PANELS, {})
    ours = isinstance(existing, ll_dashboard.LovelaceYAML) and _ours(hass, existing)
    if (existing is not None or URL_PATH in panels) and not ours:
        persistent_notification.async_create(
            hass,
            f"Es gibt bereits ein Dashboard mit der Adresse /{URL_PATH}. Die Integration legt ihr Dashboard deshalb "
            "nicht an. Lösche das vorhandene Dashboard (Einstellungen → Dashboards) und lade die Integration neu – "
            "oder schalte in den Optionen der Integration „Dashboard bereitstellen“ aus.",
            "Avarma: Dashboard nicht angelegt", "avarma_dashboard")
        return False
    conf = {"mode": "yaml", "filename": filename, "title": TITLE, "icon": ICON,
            "show_in_sidebar": True, "require_admin": False}
    kwargs = {"frontend_url_path": URL_PATH, "require_admin": False, "show_in_sidebar": True,
              "sidebar_title": TITLE, "sidebar_icon": ICON, "config": {"mode": "yaml"}, "update": URL_PATH in panels}
    params = inspect.signature(frontend.async_register_built_in_panel).parameters
    kwargs = {k: v for k, v in kwargs.items() if k in params}  # ältere HA-Versionen kennen nicht alle Parameter
    ll.dashboards[URL_PATH] = ll_dashboard.LovelaceYAML(hass, URL_PATH, conf)
    try:
        frontend.async_register_built_in_panel(hass, "lovelace", **kwargs)
    except Exception:  # noqa: BLE001
        ll.dashboards.pop(URL_PATH, None)
        _LOGGER.exception("Dashboard konnte nicht registriert werden")
        return False
    persistent_notification.async_dismiss(hass, "avarma_dashboard")
    return True


@callback
def async_remove_dashboard(hass: HomeAssistant) -> None:
    ll = hass.data.get(LOVELACE_DATA)
    if ll is None:
        return
    existing = ll.dashboards.get(URL_PATH)
    if isinstance(existing, ll_dashboard.LovelaceYAML) and _ours(hass, existing):
        ll.dashboards.pop(URL_PATH, None)
        frontend.async_remove_panel(hass, URL_PATH)


async def async_ensure_resource(hass: HomeAssistant, version: str, static_url: str) -> bool:
    """Display-Karte als Lovelace-Ressource eintragen (lädt in allen Browsern zuverlässig).

    Ein frühes Laden über extra_module_url schlug in Firefox und Safari fehl. Ressourcen werden – wie bei
    HACS-Karten – erst nach dem Frontend geladen.
    """
    ll = hass.data.get(LOVELACE_DATA)
    res = getattr(ll, "resources", None)
    if res is None or not hasattr(res, "async_create_item"):
        return False  # YAML-Ressourcen: kann nicht automatisch eingetragen werden
    base = f"{static_url}/avarma-cards.js"
    url = f"{base}?v={version}"
    try:
        await res.async_get_info()  # stellt sicher, dass die Ressourcen geladen sind
        found = [i for i in res.async_items() if str(i.get("url", "")).split("?")[0] == base]
        for extra in found[1:]:
            await res.async_delete_item(extra["id"])
        if found:
            if found[0].get("url") != url:
                await res.async_update_item(found[0]["id"], {"res_type": "module", "url": url})
        else:
            await res.async_create_item({"res_type": "module", "url": url})
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Lovelace-Ressource für die Display-Karte konnte nicht eingetragen werden")
        return False
    return True
