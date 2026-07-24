/**
 * IPTV Control Card — Home Assistant Lovelace custom card
 * 样式：B 极简单栏
 * 依赖 MQTT Discovery 实体（默认前缀 iptv_241）
 *
 * 类型：custom:iptv-control-card
 */
(() => {
  const CARD_VERSION = "1.1.1";
  const CARD_TYPE = "iptv-control-card";

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
      return this._moreOpen ? 5 : 3;
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
      const moreOpen = !!this._moreOpen;

      const statusLine = [
        healthOk ? "在线" : "离线",
        udpxyOk ? `UDPXY · ${connections} 连接` : "UDPXY 已停",
        jobOk ? "上次任务成功" : "上次任务未知",
      ].join("  ·  ");

      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          ha-card {
            padding: 16px 18px 14px;
            --muted: var(--secondary-text-color, #8a8a8a);
            --line: color-mix(in srgb, var(--divider-color, #888) 55%, transparent);
          }
          .row {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 12px;
          }
          .title {
            margin: 0;
            font-size: 1.2rem;
            font-weight: 650;
            letter-spacing: -0.01em;
            line-height: 1.2;
          }
          .online {
            flex-shrink: 0;
            font-size: 0.78rem;
            font-weight: 500;
            color: ${healthOk ? "var(--success-color, #4caf50)" : "var(--error-color, #f44336)"};
          }
          .status {
            margin: 10px 0 0;
            font-size: 0.88rem;
            line-height: 1.45;
            color: var(--primary-text-color, inherit);
          }
          .meta {
            margin: 4px 0 0;
            font-size: 0.78rem;
            color: var(--muted);
            line-height: 1.4;
          }
          .actions {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 14px;
          }
          button {
            appearance: none;
            border: none;
            background: none;
            font: inherit;
            cursor: pointer;
            padding: 0;
            color: inherit;
          }
          button.primary {
            padding: 8px 14px;
            border-radius: 6px;
            background: var(--primary-color, #03a9f4);
            color: var(--text-primary-color, #fff);
            font-size: 0.88rem;
            font-weight: 560;
          }
          button.primary:active { opacity: 0.88; }
          button.ghost {
            font-size: 0.84rem;
            color: var(--muted);
            padding: 6px 2px;
          }
          button.ghost[aria-expanded="true"] {
            color: var(--primary-text-color, inherit);
          }
          .more {
            display: ${moreOpen ? "grid" : "none"};
            gap: 2px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid var(--line);
          }
          .more button.item {
            display: flex;
            width: 100%;
            text-align: left;
            padding: 9px 2px;
            font-size: 0.88rem;
            color: var(--primary-text-color, inherit);
            border-radius: 4px;
          }
          .more button.item:hover {
            color: var(--primary-color, #03a9f4);
          }
          .urls {
            display: ${moreOpen && this._config.show_urls !== false ? "grid" : "none"};
            gap: 0;
            margin-top: 4px;
            padding-top: 6px;
            border-top: 1px solid var(--line);
          }
          .url-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 2px;
            font-size: 0.82rem;
            min-width: 0;
          }
          .url-row .tag {
            flex: 0 0 64px;
            color: var(--muted);
          }
          .url-row a, .url-row .link {
            flex: 1;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--primary-text-color, inherit);
            text-decoration: none;
            opacity: 0.85;
          }
          .url-row a:hover { color: var(--primary-color, #03a9f4); opacity: 1; }
          .url-row button.copy {
            flex-shrink: 0;
            font-size: 0.78rem;
            color: var(--muted);
            padding: 4px 0;
          }
          .url-row button.copy:hover {
            color: var(--primary-color, #03a9f4);
          }
        </style>
        <ha-card>
          <div class="row">
            <h2 class="title">${escapeHtml(title)}</h2>
            <span class="online">${healthOk ? "在线" : "离线"}</span>
          </div>
          <p class="status">${escapeHtml(statusLine)}</p>
          <p class="meta">M3U ${escapeHtml(m3uTime)}　·　EPG ${escapeHtml(epgTime)}</p>
          ${
            this._config.show_actions !== false
              ? `<div class="actions">
            <button class="primary" type="button" data-act="generate">一键生成</button>
            <button class="ghost" type="button" id="more-toggle" aria-expanded="${moreOpen}">
              ${moreOpen ? "收起" : "更多"}
            </button>
          </div>
          <div class="more">
            <button class="item" type="button" data-act="run_m3u">生成 M3U</button>
            <button class="item" type="button" data-act="run_epg">生成 EPG</button>
            <button class="item" type="button" data-act="run_logos">生成台标</button>
            <button class="item" type="button" data-act="udpxy_restart">重启 UDPXY</button>
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
        </ha-card>
      `;

      const toggle = this.shadowRoot.getElementById("more-toggle");
      if (toggle) {
        toggle.addEventListener("click", () => {
          this._moreOpen = !this._moreOpen;
          this._render();
        });
      }
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
  if (!window.customCards.some((c) => c.type === CARD_TYPE)) {
    window.customCards.push({
      type: CARD_TYPE,
      name: "IPTV Control Card",
      description: "IPTV 状态、一键生成与播放列表链接",
      preview: true,
    });
  }

  console.info(
    `%c IPTV Control Card %c v${CARD_VERSION} `,
    "background:#222;color:#fff;border-radius:4px 0 0 4px;padding:2px 6px",
    "background:#555;color:#fff;border-radius:0 4px 4px 0;padding:2px 6px"
  );
})();
