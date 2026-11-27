// Avarma-Wärmepumpe: Karte für den Display-Nachbau.
// Wrappt die Standard-Karte "picture-elements" und setzt die nötigen Styles selbst
// (dunkler Hintergrund, mitskalierende Schrift über container-type, Dreh-Animation),
// damit kein card-mod nötig ist.
class AvarmaSchemaCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.image) throw new Error("image fehlt");
    this._config = config;
    this._build();
  }

  async _build() {
    const helpers = await window.loadCardHelpers();
    const conf = { ...this._config, type: "picture-elements" };
    const card = await helpers.createCardElement(conf);
    if (this._hass) card.hass = this._hass;
    this._card = card;
    this.replaceChildren(card);
    this._applyStyle(0);
  }

  _applyStyle(tries) {
    const sr = this._card && this._card.shadowRoot;
    const haCard = sr && sr.querySelector("ha-card");
    if (!haCard) {
      if (tries < 100) setTimeout(() => this._applyStyle(tries + 1), 100);
      return;
    }
    Object.assign(haCard.style, {
      background: "#06090d", borderRadius: "16px", overflow: "hidden", containerType: "inline-size",
    });
    if (!sr.querySelector("style[data-avarma]")) {
      const st = document.createElement("style");
      st.dataset.avarma = "1";
      st.textContent = "@keyframes wpspin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}";
      sr.appendChild(st);
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) {
      this._card.hass = hass;
      this._applyStyle(100); // falls die Karte neu gezeichnet wurde: Styles erneut setzen (ohne Wiederholungen)
    }
  }

  getCardSize() {
    return this._card && this._card.getCardSize ? this._card.getCardSize() : 8;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

// Wert ohne Einheit für das Schema (Einheit steht wie am Display im Bild unter dem Strich).
// Wird von picture-elements als "custom:avarma-wert" eingebunden; Tippen öffnet die Detailansicht.
class AvarmaWert extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this._bound) {
      this._bound = true;
      this.style.cursor = "pointer";
      this.addEventListener("click", () => {
        this.dispatchEvent(new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId: this._config.entity } }));
      });
    }
  }

  set hass(hass) {
    const st = hass && this._config && hass.states[this._config.entity];
    let t = "–";
    if (st && st.state !== "unavailable" && st.state !== "unknown") {
      t = hass.formatEntityState ? hass.formatEntityState(st) : st.state;
      const u = st.attributes.unit_of_measurement;
      if (u && t.endsWith(u)) t = t.slice(0, -u.length).trim();
    }
    if (this.textContent !== t) this.textContent = t;
  }
}
if (!customElements.get("avarma-wert")) customElements.define("avarma-wert", AvarmaWert);

if (!customElements.get("avarma-schema-card")) {
  customElements.define("avarma-schema-card", AvarmaSchemaCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-schema-card", name: "Avarma Display-Nachbau", description: "Arbeitsstatus wie am Display der Wärmepumpe" });
}

// Balkendiagramm aus den Monats-/Jahrestabellen eines Sensors (Attribute "monate"/"jahre"),
// z. B. Heizkosten je Monat für WP, Heizöl, Gas … – ohne Zusatzkarten, Farben folgen dem Theme.
const AV_MON = ["Jän", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
class AvarmaBarCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity || !Array.isArray(config.series)) throw new Error("entity und series nötig");
    this._c = { field: "kosten", unit: "", period: "monate", months: 12, days: 30, decimals: 0, stacked: false, ...config };
    this._key = null;
    this.style.display = "block";  // eigene Elemente sind sonst "inline" und melden die Breite 0
  }

  set hass(hass) {
    const st = hass.states[this._c.entity];
    const data = st && st.attributes[this._c.period];
    const key = JSON.stringify(data || null);
    if (key === this._key) return;
    this._key = key;
    this._data = data || {};
    this._render(this._data);
  }

  connectedCallback() {
    // bei geänderter Breite neu zeichnen, damit die Balken die Karte ausfüllen
    if (!this._ro && window.ResizeObserver) {
      this._ro = new ResizeObserver(() => {
        const w = this._width();
        if (this._data && Math.abs(w - (this._w || 0)) > 8) this._render(this._data);
      });
      this._ro.observe(this);
    }
  }

  disconnectedCallback() {
    if (this._ro) this._ro.disconnect();
    this._ro = null;
  }

  _width() {
    return Math.round(this.getBoundingClientRect ? this.getBoundingClientRect().width : this.clientWidth || 0);
  }

  _fmt(v) {
    return v.toLocaleString("de-AT", { minimumFractionDigits: this._c.decimals, maximumFractionDigits: this._c.decimals });
  }

  _render(data) {
    let c = this._c;
    let keys = Object.keys(data).sort();
    if (c.period === "monate") keys = keys.slice(-c.months);
    if (c.period === "tage") keys = keys.slice(-c.days);
    const label = (k) => (c.period === "monate" ? `${AV_MON[+k.slice(5, 7) - 1]} ${k.slice(2, 4)}`
      : c.period === "tage" ? `${+k.slice(8, 10)}.${+k.slice(5, 7)}.` : k);
    const val = (k, s) => {
      const f = data[k] && (c.field ? data[k][c.field] : data[k]);
      const v = f && typeof f === "object" ? f[s.key] : null;
      return typeof v === "number" ? v : null;
    };
    // Reihen ohne einen einzigen Wert ausblenden (z. B. „WP ohne PV“, wenn keine PV eingerichtet ist)
    if (c.hide_empty) c = { ...c, series: c.series.filter((s) => keys.some((k) => val(k, s) !== null)) };
    const tot = (k) => c.series.reduce((a, s) => a + Math.max(val(k, s) || 0, 0), 0);
    const vals = c.stacked ? keys.map(tot) : keys.flatMap((k) => c.series.map((s) => val(k, s))).filter((v) => v !== null);
    const esc = (t) => String(t).replace(/[&<>"]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[m]);
    const legend = c.series.map((s) => `<span class="lg"><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("");
    let body;
    if (!vals.length) {
      body = `<div class="empty">Noch keine Daten${c.hint ? " – " + esc(c.hint) : ""}</div>`;
    } else {
      const max0 = Math.max(0, ...vals), min0 = Math.min(0, ...vals);
      const pad = (max0 - min0 || 1) * 0.12;  // Luft für die Werte über/unter den Balken
      const max = max0 + (max0 > 0 ? pad : 0), min = min0 - (min0 < 0 ? pad : 0);
      const H = 240, top = 10, bottom = 30, left = 46, n = c.stacked ? 1 : c.series.length, gap = 4;
      this._w = this._width();
      const avail = Math.max((this._w || 600) - 40, 280);  // Kartenbreite abzüglich Rand
      const slot = Math.max((avail - left - 10) / keys.length, c.stacked ? 9 : n * 16 + 24);  // Platz je Balkengruppe
      const inner = c.stacked ? Math.max(slot * 0.3, 2) : 24;  // Abstand zwischen den Gruppen
      const bw = Math.min(42, (slot - inner - (n - 1) * gap) / n), gw = n * bw + (n - 1) * gap, ggap = slot - gw;
      const W = Math.max(left + 10 + keys.length * slot, avail);
      const span = max - min || 1, ph = H - top - bottom;
      const y = (v) => top + ((max - v) / span) * ph;
      const step = Math.pow(10, Math.floor(Math.log10(span / 4))) * ([1, 2, 2.5, 5, 10].find((m) => span / 4 / Math.pow(10, Math.floor(Math.log10(span / 4))) <= m) || 10);
      let svg = "";
      for (let t = Math.ceil(min / step) * step; t <= max + 1e-9; t += step) {
        svg += `<line x1="${left}" x2="${W}" y1="${y(t)}" y2="${y(t)}" class="grid${Math.abs(t) < 1e-9 ? " zero" : ""}"/>`;
        svg += `<text x="${left - 6}" y="${y(t) + 4}" class="ax" text-anchor="end">${this._fmt(t)}</text>`;
      }
      const showVals = bw >= 14 && (!c.stacked || bw >= 26);
      keys.forEach((k, i) => {
        const x0 = left + 10 + i * slot + ggap / 2;
        if (c.stacked) {
          let acc = 0;
          const tip = c.series.map((s) => `${s.name}: ${this._fmt(val(k, s) || 0)} ${c.unit}`).join("\n");
          c.series.forEach((s) => {
            const v = Math.max(val(k, s) || 0, 0);
            if (!v) return;
            const yt = y(acc + v), h = Math.max(y(acc) - yt, 1);
            svg += `<rect x="${x0}" y="${yt}" width="${bw}" height="${h}" fill="${s.color}"><title>${esc(label(k))}\n${esc(tip)}</title></rect>`;
            acc += v;
          });
          if (showVals && acc) svg += `<text x="${x0 + bw / 2}" y="${y(acc) - 5}" class="v" text-anchor="middle">${this._fmt(acc)}</text>`;
          const every = Math.ceil(keys.length / Math.max(Math.floor(avail / 56), 1));
          const last = i === keys.length - 1;
          if (last || (i % every === 0 && keys.length - 1 - i >= Math.max(every * 0.75, 1)))
            svg += `<text x="${last ? x0 + gw : x0 + gw / 2}" y="${H - 8}" class="ax lbl" text-anchor="${last ? "end" : "middle"}">${esc(label(k))}</text>`;
          return;
        }
        c.series.forEach((s, j) => {
          const v = val(k, s);
          if (v === null) return;
          const x = x0 + j * (bw + gap), y0 = y(Math.max(v, 0)), h = Math.max(Math.abs(y(v) - y(0)), 1);
          svg += `<rect x="${x}" y="${y0}" width="${bw}" height="${h}" rx="3" fill="${s.color}"><title>${esc(s.name)} ${esc(label(k))}: ${this._fmt(v)} ${esc(c.unit)}</title></rect>`;
          if (showVals) svg += `<text x="${x + bw / 2}" y="${v >= 0 ? y0 - 5 : y0 + h + 13}" class="v" text-anchor="middle">${this._fmt(v)}</text>`;
        });
        svg += `<text x="${x0 + gw / 2}" y="${H - 8}" class="ax lbl" text-anchor="middle">${esc(label(k))}</text>`;
      });
      body = `<div class="scroll"><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${svg}</svg></div>`;
    }
    this.innerHTML = `<ha-card header="${esc(c.title || "")}"><div class="wrap">
      <div class="unit">${esc(c.unit)}${c.subtitle ? " · " + esc(c.subtitle) : ""}</div>
      <div class="legend">${legend}</div>${body}${c.note ? `<div class="note">${esc(c.note)}</div>` : ""}</div>
      <style>
        .wrap{padding:0 16px 16px}.unit{color:var(--secondary-text-color);font-size:14px;margin-bottom:6px}
        .legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin-bottom:8px;font-size:15px;color:var(--primary-text-color)}
        .lg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
        .scroll{overflow-x:auto}.grid{stroke:var(--divider-color);stroke-width:1}.zero{stroke:var(--secondary-text-color)}
        .ax{fill:var(--secondary-text-color);font-size:13px}.lbl{fill:var(--primary-text-color);font-size:14px}
        .v{fill:var(--primary-text-color);font-size:12px;font-weight:600}
        .note{color:var(--secondary-text-color);font-size:14px;margin-top:8px;line-height:1.4}
        .empty{color:var(--secondary-text-color);padding:24px 0;font-size:15px}
      </style></ha-card>`;
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

if (!customElements.get("avarma-bar-card")) {
  customElements.define("avarma-bar-card", AvarmaBarCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-bar-card", name: "Avarma Balkendiagramm", description: "Monats-/Jahreswerte (Kosten, Ersparnis, CO₂) als Balken" });
}

// Herkunft des WP-Stroms: „Jetzt“ (Leistung) und je Zeitraum ein 100-%-Balken PV · Akku · Netz.
const AV_SRC = [
  { key: "pv", name: "PV", icon: "mdi:solar-power", color: "#fbc02d" },
  { key: "akku", name: "Akku", icon: "mdi:home-battery", color: "#26a69a" },
  { key: "netz", name: "Netz", icon: "mdi:transmission-tower", color: "#ef5350" },
];
class AvarmaSourceCard extends HTMLElement {
  setConfig(config) {
    this._c = {
      power: "sensor.wp_leistung_elektrisch",
      periods: [["heute", "Heute"], ["woche", "Woche"], ["monat", "Monat"], ["jahr", "Jahr"]],
      ...config,
    };
    this._key = null;
  }

  set hass(hass) {
    const c = this._c, num = (e) => { const v = parseFloat(hass.states[e] && hass.states[e].state); return isNaN(v) ? null : v; };
    const p = hass.states[c.power], a = (p && p.attributes) || {};
    const now = { total: num(c.power), pv: a.jetzt_pv_w, akku: a.jetzt_akku_w, netz: a.jetzt_netz_w };
    const rows = c.periods.map(([per, name]) => {
      const r = { name };
      AV_SRC.forEach((s) => (r[s.key] = num(`sensor.wp_strom_aus_${s.key}_${per}`)));
      return r;
    });
    const key = JSON.stringify([now, rows]);
    if (key === this._key) return;
    this._key = key;
    this._render(now, rows);
  }

  _bar(r, unit, dec) {
    const parts = AV_SRC.filter((s) => r[s.key] !== null && r[s.key] !== undefined);
    const total = parts.reduce((t, s) => t + Math.max(r[s.key], 0), 0);
    const f = (v) => v.toLocaleString("de-AT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    if (!total) return `<div class="bar empty">–</div>`;
    const seg = parts.map((s) => {
      const pc = (100 * Math.max(r[s.key], 0)) / total;
      return pc > 0 ? `<div class="seg" style="width:${pc}%;background:${s.color}" title="${s.name}: ${f(r[s.key])} ${unit} (${Math.round(pc)} %)">${pc >= 9 ? Math.round(pc) + " %" : ""}</div>` : "";
    }).join("");
    const det = parts.map((s) => `<span><i style="background:${s.color}"></i>${s.name} <b>${f(r[s.key])}</b> ${unit}</span>`).join("");
    return `<div class="bar">${seg}</div><div class="det">${det}</div>`;
  }

  _render(now, rows) {
    const f0 = (v) => (v === null || v === undefined ? "–" : Math.round(v).toLocaleString("de-AT"));
    const nowHtml = `<div class="now"><div class="big"><ha-icon icon="mdi:heat-pump"></ha-icon>
        <div><div class="lbl">Wärmepumpe jetzt</div><div class="val">${f0(now.total)} <small>W</small></div></div></div>
        ${this._bar(now, "W", 0)}</div>`;
    const per = rows.map((r) => {
      const t = AV_SRC.reduce((s, x) => s + Math.max(r[x.key] || 0, 0), 0);
      return `<div class="row"><div class="rh"><span>${r.name}</span><span class="tot">${t.toLocaleString("de-AT", { maximumFractionDigits: 1 })} kWh</span></div>${this._bar(r, "kWh", 1)}</div>`;
    }).join("");
    const legend = AV_SRC.map((s) => `<span><ha-icon icon="${s.icon}" style="color:${s.color}"></ha-icon>${s.name}</span>`).join("");
    this.innerHTML = `<ha-card header="${this._c.title || "Woher kommt der Strom der Wärmepumpe?"}"><div class="wrap">
      <div class="legend">${legend}</div>${nowHtml}<div class="sep"></div>${per}
      <div class="note">Netz wird zuerst der WP zugerechnet, dann der Akku, der Rest ist PV.</div></div>
      <style>
        .wrap{padding:0 16px 16px}.legend{display:flex;gap:18px;margin-bottom:12px;font-size:15px;color:var(--primary-text-color)}
        .legend ha-icon{--mdc-icon-size:20px;margin-right:4px;vertical-align:-4px}
        .now .big{display:flex;align-items:center;gap:12px;margin-bottom:10px}.now ha-icon{--mdc-icon-size:36px;color:var(--state-icon-color)}
        .lbl{color:var(--secondary-text-color);font-size:14px}.val{font-size:30px;font-weight:600;line-height:1.1}.val small{font-size:16px;font-weight:400}
        .bar{display:flex;height:30px;border-radius:8px;overflow:hidden;background:var(--divider-color)}
        .bar.empty{align-items:center;justify-content:center;color:var(--secondary-text-color);font-size:13px}
        .seg{display:flex;align-items:center;justify-content:center;color:#111;font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden}
        .det{display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:6px;font-size:14px;color:var(--secondary-text-color)}
        .det b{color:var(--primary-text-color);font-weight:600}.det i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px}
        .sep{height:1px;background:var(--divider-color);margin:16px 0}.row{margin-bottom:16px}
        .rh{display:flex;justify-content:space-between;font-size:16px;margin-bottom:6px;color:var(--primary-text-color)}.tot{font-weight:600}
        .note{color:var(--secondary-text-color);font-size:13px}
      </style></ha-card>`;
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

if (!customElements.get("avarma-source-card")) {
  customElements.define("avarma-source-card", AvarmaSourceCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-source-card", name: "Avarma Stromherkunft", description: "WP-Strom nach PV, Akku und Netz" });
}

// Verlaufsgraph mit Entitäten, die erst zur Laufzeit feststehen (z. B. die in den Optionen gewählten Raumfühler):
// feste Entitäten + Listen aus Attributen eines Sensors → Standard-Karte "history-graph".
class AvarmaHistoryCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.source) throw new Error("source fehlt");
    this._c = { entities: [], attributes: ["fuehler"], hours_to_show: 48, ...config };
    this._list = null;
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._c.source], a = (st && st.attributes) || {};
    const list = [...this._c.entities];
    for (const k of this._c.attributes) for (const e of [].concat(a[k] || [])) if (e && !list.includes(e)) list.push(e);
    const usable = list.filter((e) => hass.states[e]).map((e) => ({ entity: e, name: this._name(hass, e) }));
    const key = JSON.stringify(usable);
    if (key !== this._list) {
      this._list = key;
      this._build(usable);
    } else if (this._card) {
      this._card.hass = hass;
    }
  }

  // Kurzer Name ohne Gerät davor: eigener Entitätsname (z. B. „Aussen“), sonst bei nur „Temperatur“ der Gerätename
  _name(hass, e) {
    const ent = hass.entities && hass.entities[e];
    const dev = ent && ent.device_id && hass.devices && hass.devices[ent.device_id];
    const dname = dev && (dev.name_by_user || dev.name);
    let n = (hass.states[e].attributes.friendly_name || e).trim();
    if (dname && n.startsWith(dname + " ")) n = n.slice(dname.length + 1).trim();
    if (dname && /^(temperatur|temperature|temp)$/i.test(n)) n = dname;
    return n;
  }

  async _build(entities) {
    const helpers = await window.loadCardHelpers();
    const card = await helpers.createCardElement({ type: "history-graph", title: this._c.title, hours_to_show: this._c.hours_to_show, entities });
    card.hass = this._hass;
    this._card = card;
    this.replaceChildren(card);
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

if (!customElements.get("avarma-history-card")) {
  customElements.define("avarma-history-card", AvarmaHistoryCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-history-card", name: "Avarma Verlauf (gewählte Fühler)", description: "Verlaufsgraph inkl. der in den Optionen gewählten Fühler" });
}

// Liste aus einem Attribut (z. B. Verlauf der Übergangszeit) als Tabelle mit fester Höhe und Scrollbalken.
class AvarmaListCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("entity fehlt");
    this._c = { attribute: "verlauf", rows: 10, max_height: 420, empty: "Noch keine Einträge.", ...config };
    this._key = null;
  }

  set hass(hass) {
    const st = hass.states[this._c.entity];
    const rows = [].concat((st && st.attributes[this._c.attribute]) || []);
    const key = JSON.stringify(rows);
    if (key === this._key) return;
    this._key = key;
    const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
    const body = rows.length
      ? `<table>${rows.map((r) => `<tr><td class="t">${esc(r.zeit)}</td><td>${esc(r.text)}</td></tr>`).join("")}</table>`
      : `<div class="leer">${esc(this._c.empty)}</div>`;
    this.innerHTML = `<ha-card header="${esc(this._c.title || "")}"><style>
        .wrap { max-height: ${Number(this._c.max_height) || 420}px; overflow-y: auto; padding: 0 16px 16px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        td { padding: 6px 8px; border-bottom: 1px solid var(--divider-color); vertical-align: top; }
        td.t { white-space: nowrap; color: var(--secondary-text-color); width: 1%; }
        .leer { color: var(--secondary-text-color); }
        .n { padding: 0 16px 12px; color: var(--secondary-text-color); font-size: 12px; }
      </style><div class="wrap">${body}</div>${rows.length ? `<div class="n">${rows.length} Einträge (neueste oben)</div>` : ""}</ha-card>`;
    this._fit();
  }

  // genau `rows` Zeilen sichtbar, Rest scrollen (Höhe aus der echten Zeilenhöhe, passt auf Handy und PC).
  // fill_row: so hoch wie die Nachbarn in derselben Reihe (z. B. Einstellungen rechts daneben); allein in der Reihe
  // (Handy, untereinander) gilt `rows`.
  _fit() {
    if (this._fitting) return;
    this._fitting = true;
    requestAnimationFrame(() => {
      this._fitting = false;
      const wrap = this.querySelector(".wrap"), trs = this.querySelectorAll("tr");
      if (!wrap) return;
      const n = Number(this._c.rows) || 10;
      let max = trs.length > n ? trs[n].offsetTop - trs[0].offsetTop : 0;
      const setzen = (v) => { const neu = v > 0 ? `${Math.round(v)}px` : "none"; if (wrap.style.maxHeight !== neu) wrap.style.maxHeight = neu; };
      if (!this._c.fill_row) return setzen(max);
      // erst klein machen, damit die Reihe von den Nachbarn bestimmt wird, dann messen
      const vorher = wrap.style.maxHeight;
      wrap.style.maxHeight = "120px";
      requestAnimationFrame(() => {
        const ziel = this._reihe();
        if (!ziel) { wrap.style.maxHeight = vorher; return setzen(max); }
        const card = this.querySelector("ha-card");
        const rand = (card ? card.getBoundingClientRect().height : 0) - wrap.getBoundingClientRect().height;
        setzen(Math.max(120, ziel.hoehe - rand - ziel.eigen_rand));
      });
    });
  }

  // Höhe der höchsten Nachbarn in derselben Reihe: nach oben laufen, bis ein Grid Geschwister auf gleicher Höhe hat
  _reihe() {
    let el = this;
    const card = this.querySelector("ha-card");
    for (let i = 0; i < 12 && el; i++) {
      const p = el.parentNode instanceof ShadowRoot ? el.parentNode.host : el.parentNode;
      if (!(p instanceof Element)) return null;
      if (getComputedStyle(p).display.includes("grid")) {
        const r = el.getBoundingClientRect();
        const nachbarn = [...p.children].filter((c) => c !== el && Math.abs(c.getBoundingClientRect().top - r.top) < 4);
        if (nachbarn.length) {
          if (!this._ro && window.ResizeObserver) {
            this._ro = new ResizeObserver((es) => {
              const k = es.map((e) => Math.round(e.contentRect.width)).join();
              if (k !== this._rok) { this._rok = k; this._fit(); }  // nur bei geänderter Breite (Fenster, Spalten)
            });
            nachbarn.forEach((c) => this._ro.observe(c));
          }
          const eigen_rand = r.height - (card ? card.getBoundingClientRect().height : r.height);
          return { hoehe: Math.max(...nachbarn.map((c) => c.getBoundingClientRect().height)), eigen_rand };
        }
      }
      el = p;
    }
    return null;
  }

  connectedCallback() {
    this._fit();
    setTimeout(() => this._fit(), 800);  // Nachbarn sind beim ersten Zeichnen oft noch nicht fertig
    if (this._c && this._c.fill_row && !this._wr) {
      this._wr = () => { if (this._ro) { this._ro.disconnect(); this._ro = null; } this._fit(); };
      window.addEventListener("resize", this._wr);
    }
  }

  disconnectedCallback() {
    if (this._ro) this._ro.disconnect();
    this._ro = null;
    if (this._wr) window.removeEventListener("resize", this._wr);
    this._wr = null;
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

if (!customElements.get("avarma-list-card")) {
  customElements.define("avarma-list-card", AvarmaListCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-list-card", name: "Avarma Liste", description: "Einträge aus einem Attribut als scrollbare Tabelle" });
}

// Temperaturkurve der Wetterprognose (stündlich) – ohne Zusatzkarten. Optional wird das Fenster schattiert,
// das die eigene Regelung als „Vorausschau“ nutzt (Attribut fein.vorschau des Regelungs-Sensors).
class AvarmaForecastCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("entity fehlt");
    this._c = { hours: 24, title: "Temperaturprognose", ...config };
    this.style.display = "block";
  }

  set hass(hass) {
    this._hass = hass;
    if (this._sub === undefined && hass.connection) {
      this._sub = null;
      hass.connection.subscribeMessage((msg) => { this._fc = msg.forecast || []; this._render(); },
        { type: "weather/subscribe_forecast", forecast_type: "hourly", entity_id: this._c.entity })
        .then((unsub) => { this._sub = unsub; })
        .catch(() => { this._fc = []; this._render(); });
    }
    const rg = this._c.regelung && hass.states[this._c.regelung];
    const vs = rg && rg.attributes.fein ? Number(rg.attributes.fein.vorschau) || 0 : 0;
    if (vs !== this._vs) { this._vs = vs; this._render(); }
  }

  connectedCallback() {
    if (!this._ro && window.ResizeObserver) {
      this._ro = new ResizeObserver(() => { if (Math.abs(this._width() - (this._w || 0)) > 8) this._render(); });
      this._ro.observe(this);
    }
  }

  disconnectedCallback() {
    if (this._ro) this._ro.disconnect();
    this._ro = null;
    if (this._sub) this._sub();
    this._sub = undefined;
  }

  _width() {
    return Math.round(this.getBoundingClientRect ? this.getBoundingClientRect().width : this.clientWidth || 0);
  }

  _render() {
    const c = this._c, esc = (s) => String(s ?? "").replace(/[&<>"]/g, (x) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[x]);
    const f1 = (v) => v.toLocaleString("de-AT", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const now = Date.now();
    const pts = (this._fc || []).map((f) => [Date.parse(f.datetime), Number(f.temperature)])
      .filter((p) => !isNaN(p[0]) && !isNaN(p[1]) && p[0] >= now - 3600e3).slice(0, Number(c.hours) + 1);
    let body;
    if (pts.length < 2) {
      body = `<div class="empty">${this._fc ? "Keine Stundenprognose verfügbar." : "Lade Prognose …"}</div>`;
    } else {
      const W = Math.max(this._w = this._width() - 32, 280), H = 220, L = 38, R = 8, T = 22, B = 26;
      const t0 = pts[0][0], t1 = pts[pts.length - 1][0];
      const vals = pts.map((p) => p[1]);
      let lo = Math.floor(Math.min(...vals) - 1), hi = Math.ceil(Math.max(...vals) + 1);
      const x = (t) => L + (t - t0) / (t1 - t0) * (W - L - R), y = (v) => T + (hi - v) / (hi - lo) * (H - T - B);
      let svg = "";
      const step = Math.max(1, Math.ceil((hi - lo) / 5));
      for (let v = Math.ceil(lo / step) * step; v <= hi; v += step)
        svg += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="grid${v === 0 ? " zero" : ""}"/><text x="${L - 6}" y="${y(v) + 4}" class="ax" text-anchor="end">${v}°</text>`;
      if (this._vs > 0) {
        const a = Math.max(now, t0), b = Math.min(now + this._vs * 3600e3, t1);
        if (b > a) svg += `<rect x="${x(a)}" y="${T}" width="${x(b) - x(a)}" height="${H - T - B}" class="vs"><title>Vorausschau der Regelung: ${this._vs} h</title></rect>`
          + `<text x="${x(a) + 4}" y="${T + 13}" class="vst">Vorausschau ${this._vs} h</text>`;
      }
      const hrs = (t1 - t0) / 3600e3, every = hrs > 30 ? 6 : 3;
      pts.forEach((p) => {
        const d = new Date(p[0]);
        if (d.getHours() % every === 0)
          svg += `<text x="${x(p[0])}" y="${H - 8}" class="ax" text-anchor="middle">${d.getHours() === 0 ? d.toLocaleDateString("de-AT", { weekday: "short" }) : d.getHours() + "h"}</text>`;
      });
      const line = pts.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
      svg += `<path d="${line}L${x(t1)},${H - B}L${x(t0)},${H - B}Z" class="area"/><path d="${line}" class="ln"/>`;
      if (now > t0 && now < t1) svg += `<line x1="${x(now)}" x2="${x(now)}" y1="${T}" y2="${H - B}" class="now"/>`;
      const iMin = vals.indexOf(Math.min(...vals)), iMax = vals.indexOf(Math.max(...vals));
      [[iMax, -8], [iMin, 16]].forEach(([i, dy]) => {
        svg += `<text x="${Math.min(Math.max(x(pts[i][0]), L + 14), W - R - 14)}" y="${y(pts[i][1]) + dy}" class="mm" text-anchor="middle">${f1(pts[i][1])}°</text>`;
      });
      pts.forEach((p) => {
        const d = new Date(p[0]);
        svg += `<circle cx="${x(p[0])}" cy="${y(p[1])}" r="6" class="hit"><title>${d.toLocaleString("de-AT", { weekday: "short", hour: "2-digit", minute: "2-digit" })}: ${f1(p[1])} °C</title></circle>`;
      });
      body = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${svg}</svg>`;
    }
    this.innerHTML = `<ha-card header="${esc(c.title)}"><div class="wrap">${body}</div><style>
        .wrap{padding:0 16px 16px}.grid{stroke:var(--divider-color);stroke-width:1}.zero{stroke:#42a5f5;stroke-dasharray:4 3}
        .ax{fill:var(--secondary-text-color);font-size:12px}.ln{fill:none;stroke:#ff7043;stroke-width:2.5;stroke-linejoin:round}
        .area{fill:#ff7043;opacity:.12}.now{stroke:var(--primary-text-color);stroke-width:1;stroke-dasharray:3 3;opacity:.6}
        .vs{fill:var(--primary-color);opacity:.10}.vst{fill:var(--secondary-text-color);font-size:11px}
        .mm{fill:var(--primary-text-color);font-size:12px;font-weight:600}.hit{fill:transparent}
        .empty{color:var(--secondary-text-color);padding:24px 0;font-size:15px}
      </style></ha-card>`;
  }

  getCardSize() {
    return 5;
  }

  getGridOptions() {
    return { columns: "full" };
  }
}

if (!customElements.get("avarma-forecast-card")) {
  customElements.define("avarma-forecast-card", AvarmaForecastCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-forecast-card", name: "Avarma Temperaturprognose", description: "Stündliche Temperaturprognose einer Wetter-Entität als Kurve" });
}

// Parameter-Karte: Standard-Zeilen (Eingabefeld) und dahinter je ein Feld mit der Werkseinstellung,
// Überschrift „Werk (9 kW)“ in der Titelzeile über dieser Spalte.
class AvarmaParamCard extends HTMLElement {
  setConfig(config) {
    if (!config || !Array.isArray(config.entities)) throw new Error("entities fehlt");
    this._c = config;
    this._rows = null;
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    (this._rows || []).forEach((r) => { r.hass = hass; });
    this._werk();
  }

  // Werkseinstellung und Modell kommen aus den Attributen der Entität (Modell in den Optionen der Integration wählbar)
  _werk() {
    if (!this._hass || !this._werkEl) return;
    let modell = null;
    this._c.entities.forEach((e, i) => {
      const a = (this._hass.states[e.entity] || {}).attributes || {};
      if (!("werkseinstellung" in a)) return;
      const w = a.werkseinstellung;
      const t = w === null ? "aus" : String(w).replace(".", ",");
      if (this._werkEl[i].textContent !== t) this._werkEl[i].textContent = t;
      modell = modell || a.modell;
    });
    if (modell && this._kopfEl) {
      const h = `Werk<br>(${modell.replace(/[&<>"]/g, "")})`;
      if (this._kopfEl.innerHTML !== h) this._kopfEl.innerHTML = h;
    }
  }

  getCardSize() { return 1 + (this._c ? this._c.entities.length : 0); }

  async _build() {
    const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
    const c = this._c;
    this.innerHTML = `<ha-card><div class="kopf"><div class="titel">${esc(c.title || "")}</div><div class="werkkopf">${esc(c.werk_title || "Werk (9 kW)").replace(" ", "<br>")}</div></div>
      <div class="liste"></div><style>
      .kopf { display: flex; align-items: flex-end; justify-content: space-between; gap: 8px; padding: 24px 16px 12px; }
      .titel { font-size: var(--ha-card-header-font-size, 24px); line-height: 1.3; color: var(--ha-card-header-color, var(--primary-text-color)); }
      .werkkopf { width: 64px; flex: none; text-align: center; font-size: 12px; line-height: 1.3; white-space: nowrap; color: var(--secondary-text-color); }
      .liste { padding: 0 16px 16px; }
      .zeile { display: flex; align-items: center; gap: 8px; }
      .zeile + .zeile { margin-top: 8px; }
      .ent { flex: 1; min-width: 0; }
      .werk { width: 64px; flex: none; box-sizing: border-box; height: 56px; display: flex; align-items: center; justify-content: flex-end;
        padding: 0 12px; border-radius: 4px 4px 0 0; background: var(--mdc-text-field-fill-color, rgba(127,127,127,.12));
        border-bottom: 1px dashed rgba(127,127,127,.35); color: var(--disabled-text-color, rgba(127,127,127,.6)); font-size: 16px; opacity: .75; }
      </style></ha-card>`;
    const helpers = await window.loadCardHelpers();
    const liste = this.querySelector(".liste");
    this._rows = [];
    this._werkEl = [];
    this._kopfEl = this.querySelector(".werkkopf");
    for (const e of c.entities) {
      const row = helpers.createRowElement({ entity: e.entity, name: e.name });
      if (this._hass) row.hass = this._hass;
      this._rows.push(row);
      const z = document.createElement("div");
      z.className = "zeile";
      const ent = document.createElement("div");
      ent.className = "ent";
      ent.appendChild(row);
      const w = document.createElement("div");
      w.className = "werk";
      w.textContent = e.werk ?? "–";
      this._werkEl.push(w);
      z.append(ent, w);
      liste.appendChild(z);
    }
    this._werk();
    this._ausrichten(0);
    if (!this._ro && window.ResizeObserver) {
      this._ro = new ResizeObserver(() => this._ausrichten(0));
      this._ro.observe(this);
    }
  }

  // Werk-Feld genau auf Höhe und Größe des Eingabefelds der Zeile legen (das liegt tief im Shadow-DOM)
  _ausrichten(versuch) {
    const suche = (el, d = 0) => {
      if (!el || d > 6) return null;
      const r = el.shadowRoot;
      if (r) {
        const f = r.querySelector("ha-input, ha-textfield, ha-select, ha-slider");
        if (f) return f;
        for (const k of r.querySelectorAll("*")) { const t = suche(k, d + 1); if (t) return t; }
      }
      return null;
    };
    let fehlt = false;
    this.querySelectorAll(".zeile").forEach((z, i) => {
      const feld = suche(this._rows[i]);
      const w = z.querySelector(".werk");
      const fr = feld && feld.getBoundingClientRect();
      if (!fr || !fr.height) { fehlt = true; return; }
      const zr = z.getBoundingClientRect();
      z.style.alignItems = "flex-start";
      w.style.marginTop = `${Math.round(fr.top - zr.top)}px`;
      w.style.height = `${Math.round(fr.height)}px`;
    });
    if (fehlt && versuch < 30) setTimeout(() => this._ausrichten(versuch + 1), 200);
  }
}
if (!customElements.get("avarma-param-card")) {
  customElements.define("avarma-param-card", AvarmaParamCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "avarma-param-card", name: "Avarma Parameter", description: "Parameter mit Werkseinstellung daneben" });
}
