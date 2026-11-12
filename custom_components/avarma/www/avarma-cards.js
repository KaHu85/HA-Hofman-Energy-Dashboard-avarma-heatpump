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
    const c = this._c;
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
