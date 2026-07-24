/**
 * IPTV Control Card — Home Assistant Lovelace custom card
 * 依赖 MQTT Discovery 实体（默认前缀 iptv_241，对应 client_id=iptv-241）
 *
 * 资源：/local/iptv-card/iptv-card.js  （或 HACS / www 路径）
 * 类型：custom:iptv-control-card
 */
(() => {
  const CARD_VERSION = "1.0.0";
  const CARD_TYPE = "iptv-control-card";

  const LitElement =
    window.LitElement ||
    Object.getPrototypeOf(customElements.get("ha-panel-lovelace"));
  const html =
    window.html ||
    (LitElement
      ? Object.getPrototypeOf(customElements.get("ha-panel-lovelace")).prototype
          .html
      : null);
  const css =
    window.css ||
    (LitElement
      ? Object.getPrototypeOf(customElements.get("ha-panel-lovelace")).prototype
          .css
      : null);

  // HA 通常自带 lit；若拿不到则延迟用 ha-element 的基类
  function getLit() {
    if (window.lit) return window.lit;
    const ha =
      customElements.get("home-assistant") ||
      customElements.get("hui-view") ||
      customElements.get("ha-card");
    if (!ha) return null;
    const proto = Object.getPrototypeOf(ha.prototype);
    return {
      LitElement: proto.constructor,
      html: proto.html || window.html,
      css: proto.css || window.css,
    };
  }

  class IptvControlCard extends (customElements.get("hui-entity-card")
    ? Object.getPrototypeOf(customElements.get("hui-entity-card"))
    : HTMLElement) {
    static getStubConfig() {
      return { prefix: "iptv_241", title: "IPTV" };
    }

    static getConfigElement() {
      return document.createElement("iptv-control-card-editor");
    }

    setConfig(config) {
      if (!config) throw new Error("Invalid config");
      this._config = {
        prefix: "iptv_241",
        title: "IPTV",
        show_urls: true,
        show_actions: true,
        ...config,
      };
      this._prefix = String(this._config.prefix || "iptv_241").replace(
        /-/g,
        "_"
      );
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
      return 5;
    }

    connectedCallback() {
      this._render();
    }

    _eid(domain, suffix) {
      return `${domain}.${this._prefix}_${suffix}`;
    }

    _state(entityId) {
      return this._hass?.states?.[entityId];
    }

    _stateStr(entityId, fallback = "—") {
      const st = this._state(entityId);
      if (!st) return fallback;
      return st.state ?? fallback;
    }

    _isOn(entityId) {
      const s = this._stateStr(entityId, "off").toLowerCase();
      return s === "on" || s === "online" || s === "home" || s === "true";
    }

    async _press(suffix) {
      const entity_id = this._eid("button", suffix);
      if (!this._hass?.callService) return;
      if (!this._state(entity_id)) {
        this._toast(`实体不存在: ${entity_id}`);
        return;
      }
      await this._hass.callService("button", "press", { entity_id });
    }

    _toast(msg) {
      const ev = new Event("hass-notification", {
        bubbles: true,
        composed: true,
      });
      ev.detail = { message: msg };
      this.dispatchEvent(ev);
    }

    _copy(text) {
      if (!text || text === "—") return;
      navigator.clipboard?.writeText(text).then(
        () => this._toast("已复制"),
        () => this._toast(text)
      );
    }

    _render() {
      if (!this._config) return;
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });

      const p = this._prefix;
      const healthOk = this._isOn(this._eid("binary_sensor", "health"));
      const udpxyOk = this._isOn(this._eid("binary_sensor", "udpxy_running"));
      const jobOk = this._isOn(this._eid("binary_sensor", "last_job_ok"));
      const connections = this._stateStr(
        this._eid("sensor", "udpxy_connections"),
        "0"
      );
      const m3uTime = this._stateStr(this._eid("sensor", "m3u_mtime"));
      const epgTime = this._stateStr(this._eid("sensor", "epg_mtime"));
      const m3uUrl = this._stateStr(this._eid("sensor", "m3u_url"));
      const aptvUrl = this._stateStr(this._eid("sensor", "m3u_aptv_url"));
      const epgUrl = this._stateStr(this._eid("sensor", "epg_url"));

      const title = this._config.title || "IPTV";

      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          ha-card {
            padding: 12px 14px 14px;
            --iptv-ok: var(--success-color, #4caf50);
            --iptv-bad: var(--error-color, #f44336);
            --iptv-muted: var(--secondary-text-color, #888);
          }
          .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 10px;
          }
          .title {
            font-size: 1.15rem;
            font-weight: 600;
            margin: 0;
          }
          .pill {
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 999px;
            background: var(--secondary-background-color, #eee);
            color: var(--iptv-muted);
          }
          .pill.ok { background: color-mix(in srgb, var(--iptv-ok) 18%, transparent); color: var(--iptv-ok); }
          .pill.bad { background: color-mix(in srgb, var(--iptv-bad) 18%, transparent); color: var(--iptv-bad); }
          .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 12px;
          }
          .stat {
            background: var(--secondary-background-color, rgba(0,0,0,.04));
            border-radius: 10px;
            padding: 10px 12px;
          }
          .stat .label {
            font-size: 0.72rem;
            color: var(--iptv-muted);
            margin-bottom: 4px;
          }
          .stat .value {
            font-size: 0.95rem;
            font-weight: 600;
            word-break: break-all;
          }
          .dot {
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            margin-right: 6px;
            background: var(--iptv-muted);
          }
          .dot.on { background: var(--iptv-ok); }
          .dot.off { background: var(--iptv-bad); }
          .actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
          }
          button {
            appearance: none;
            border: none;
            border-radius: 8px;
            padding: 8px 12px;
            font: inherit;
            font-size: 0.85rem;
            cursor: pointer;
            background: var(--primary-color, #03a9f4);
            color: var(--text-primary-color, #fff);
          }
          button.secondary {
            background: var(--secondary-background-color, #e0e0e0);
            color: var(--primary-text-color, #111);
          }
          button:disabled { opacity: 0.5; cursor: not-allowed; }
          .urls { display: grid; gap: 6px; }
          .url-row {
            display: grid;
            grid-template-columns: 72px 1fr auto;
            gap: 8px;
            align-items: center;
            font-size: 0.8rem;
          }
          .url-row .tag { color: var(--iptv-muted); }
          .url-row a, .url-row .link {
            color: var(--primary-color, #03a9f4);
            text-decoration: none;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .url-row button.copy {
            padding: 4px 8px;
            font-size: 0.72rem;
            background: transparent;
            color: var(--primary-color, #03a9f4);
            border: 1px solid color-mix(in srgb, var(--primary-color, #03a9f4) 40%, transparent);
          }
          .hint {
            margin-top: 8px;
            font-size: 0.7rem;
            color: var(--iptv-muted);
          }
        </style>
        <ha-card>
          <div class="header">
            <h2 class="title">${escapeHtml(title)}</h2>
            <span class="pill ${healthOk ? "ok" : "bad"}">${healthOk ? "online" : "offline"}</span>
          </div>
          <div class="grid">
            <div class="stat">
              <div class="label">UDPXY</div>
              <div class="value"><span class="dot ${udpxyOk ? "on" : "off"}"></span>${udpxyOk ? "运行中" : "已停止"} · ${escapeHtml(connections)} 连接</div>
            </div>
            <div class="stat">
              <div class="label">上次任务</div>
              <div class="value"><span class="dot ${jobOk ? "on" : "off"}"></span>${jobOk ? "成功" : "失败/未知"}</div>
            </div>
            <div class="stat">
              <div class="label">M3U 更新</div>
              <div class="value">${escapeHtml(m3uTime)}</div>
            </div>
            <div class="stat">
              <div class="label">EPG 更新</div>
              <div class="value">${escapeHtml(epgTime)}</div>
            </div>
          </div>
          ${
            this._config.show_actions !== false
              ? `<div class="actions">
            <button data-act="generate">Create All</button>
            <button class="secondary" data-act="run_m3u">Create M3U</button>
            <button class="secondary" data-act="run_epg">Create EPG</button>
            <button class="secondary" data-act="run_logos">Create Logos</button>
            <button class="secondary" data-act="udpxy_restart">Restart UDPXY</button>
          </div>`
              : ""
          }
          ${
            this._config.show_urls !== false
              ? `<div class="urls">
            ${urlRow("TiviMate", m3uUrl)}
            ${urlRow("APTV", aptvUrl)}
            ${urlRow("EPG", epgUrl)}
          </div>`
              : ""
          }
          <div class="hint">实体前缀: ${escapeHtml(p)} · card ${CARD_VERSION}</div>
        </ha-card>
      `;

      this.shadowRoot.querySelectorAll("button[data-act]").forEach((btn) => {
        btn.addEventListener("click", () => this._press(btn.dataset.act));
      });
      this.shadowRoot.querySelectorAll("button.copy").forEach((btn) => {
        btn.addEventListener("click", () => this._copy(btn.dataset.url));
      });
    }
  }

  function urlRow(tag, url) {
    const safe = escapeHtml(url);
    const href =
      url && url !== "—" && /^https?:\/\//i.test(url)
        ? `<a href="${safe}" target="_blank" rel="noopener">${safe}</a>`
        : `<span class="link">${safe}</span>`;
    return `<div class="url-row">
      <span class="tag">${escapeHtml(tag)}</span>
      ${href}
      <button class="copy" type="button" data-url="${safe}">复制</button>
    </div>`;
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // 简易编辑器（可选）
  class IptvControlCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = config || {};
      this._render();
    }
    set hass(hass) {
      this._hass = hass;
    }
    _render() {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      const c = this._config || {};
      this.shadowRoot.innerHTML = `
        <div style="display:grid;gap:8px;padding:4px 0;">
          <label>标题 <input id="title" value="${escapeHtml(c.title || "IPTV")}" /></label>
          <label>实体前缀 <input id="prefix" value="${escapeHtml(c.prefix || "iptv_241")}" placeholder="iptv_241" /></label>
        </div>
      `;
      const fire = () => {
        const title = this.shadowRoot.getElementById("title").value;
        const prefix = this.shadowRoot.getElementById("prefix").value;
        const ev = new Event("config-changed", { bubbles: true, composed: true });
        ev.detail = { config: { ...c, type: `custom:${CARD_TYPE}`, title, prefix } };
        this.dispatchEvent(ev);
      };
      this.shadowRoot.querySelectorAll("input").forEach((el) => {
        el.addEventListener("change", fire);
        el.addEventListener("input", fire);
      });
    }
  }

  if (!customElements.get(CARD_TYPE)) {
    customElements.define(CARD_TYPE, IptvControlCard);
  }
  if (!customElements.get("iptv-control-card-editor")) {
    customElements.define("iptv-control-card-editor", IptvControlCardEditor);
  }

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: "IPTV Control Card",
    description: "IPTV 状态、一键生成与播放列表链接",
    preview: true,
  });

  console.info(
    `%c IPTV Control Card %c v${CARD_VERSION} `,
    "background:#03a9f4;color:#fff;border-radius:4px 0 0 4px;padding:2px 6px",
    "background:#333;color:#fff;border-radius:0 4px 4px 0;padding:2px 6px"
  );
})();
