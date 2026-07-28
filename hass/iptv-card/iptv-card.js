/**
 * IPTV Control Card — Home Assistant Lovelace custom card
 * 布局：状态行（灯/数字/时间）+ 一键更新 + 更多
 * 依赖 MQTT Discovery 实体（默认前缀 iptv_241）
 *
 * 类型：custom:iptv-control-card
 */
(() => {
  const CARD_VERSION = "1.3.4";
  const CARD_TYPE = "iptv-control-card";

  class IptvControlCard extends (customElements.get("hui-entity-card")
    ? Object.getPrototypeOf(customElements.get("hui-entity-card"))
    : HTMLElement) {
    static getStubConfig() {
      return { prefix: "iptv_241", title: "IPTV 电视直播系统" };
    }

    static getConfigElement() {
      return document.createElement("iptv-control-card-editor");
    }

    setConfig(config) {
      if (!config) throw new Error("Invalid config");
      this._config = {
        prefix: "iptv_241",
        title: "IPTV 电视直播系统",
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
      return this._moreOpen ? 6 : 4;
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

    /** 时间+日+月，如 15:02 28日7月 */
    _formatUpdateTime(raw) {
      if (!raw || raw === "—" || raw === "unknown" || raw === "unavailable") {
        return "—";
      }
      const s = String(raw).trim();

      // 已是目标样式
      if (/\d{1,2}:\d{2}\s+\d{1,2}日\d{1,2}月/.test(s)) return s;

      // HA 模板：28/07/2026 15:02
      let m = s.match(
        /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})(?::\d{2})?$/
      );
      if (m) {
        return `${pad(m[4])}:${m[5]} ${Number(m[1])}日${Number(m[2])}月`;
      }

      // 2026-07-28 15:02:00 / 2026-07-28T15:02:00
      m = s.match(
        /^(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})(?::\d{2})?/
      );
      if (m) {
        return `${pad(m[4])}:${m[5]} ${Number(m[3])}日${Number(m[2])}月`;
      }

      // unix 秒
      if (/^\d{10,13}$/.test(s)) {
        const n = Number(s);
        const ms = n > 1e12 ? n : n * 1000;
        const d = new Date(ms);
        if (!Number.isNaN(d.getTime())) {
          return `${pad(d.getHours())}:${pad(d.getMinutes())} ${d.getDate()}日${
            d.getMonth() + 1
          }月`;
        }
      }

      return s;
    }

    async _press(suffix) {
      const entity_id = this._eid("button", suffix);
      if (!this._hass?.callService) return;
      if (!this._state(entity_id)) {
        this._toast(`实体不存在: ${entity_id}`);
        return;
      }
      if (suffix === "network_diag") {
        await this._runNetworkDiag();
        return;
      }
      if (suffix === "generate") {
        await this._runGenerate();
        return;
      }
      await this._hass.callService("button", "press", { entity_id });
      this._toast("已触发");
    }

    async _runGenerate() {
      const entity_id = this._eid("button", "generate");
      const m3uId = this._eid("sensor", "m3u_mtime");
      const epgId = this._eid("sensor", "epg_mtime");
      const beforeM3u = this._stateStr(m3uId);
      const beforeEpg = this._stateStr(epgId);
      this._updating = true;
      this._toast("正在一键更新（M3U+EPG）…");
      this._render();
      await this._hass.callService("button", "press", { entity_id });
      // 等待传感器时间变化（最长约 3 分钟：含台标下载）
      for (let i = 0; i < 90; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const m3u = this._hass?.states?.[m3uId]?.state;
        const epg = this._hass?.states?.[epgId]?.state;
        const m3uChanged = m3u && m3u !== beforeM3u && m3u !== "unknown";
        const epgChanged = epg && epg !== beforeEpg && epg !== "unknown";
        if (m3uChanged || epgChanged) {
          this._updating = false;
          this._toast(
            `更新完成：M3U ${this._formatUpdateTime(m3u)} / EPG ${this._formatUpdateTime(epg)}`
          );
          this._render();
          return;
        }
      }
      this._updating = false;
      this._toast("已触发更新，请稍后看时间是否变化（任务可能仍在跑）");
      this._render();
    }

    async _runNetworkDiag() {
      const entity_id = this._eid("button", "network_diag");
      const summaryId = this._eid("sensor", "network_summary");
      const beforeAt = this._state(summaryId)?.attributes?.at;
      this._toast("正在检测网络…");
      this._moreOpen = true;
      await this._hass.callService("button", "press", { entity_id });
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 500));
        const st = this._hass?.states?.[summaryId];
        const at = st?.attributes?.at;
        if (st && at && at !== beforeAt) {
          const ok =
            st.attributes?.ok !== false &&
            String(st.state || "").startsWith("OK");
          const detail = st.attributes?.detail || st.state || "";
          this._toast(ok ? `网络正常：${st.state}` : `网络异常：${st.state}`);
          this._lastDiagDetail = detail;
          this._render();
          return;
        }
      }
      this._toast("检测已触发，请查看传感器 IPTV Network Summary");
      this._render();
    }

    _toast(msg) {
      const ev = new Event("hass-notification", {
        bubbles: true,
        composed: true,
      });
      ev.detail = { message: String(msg || "").slice(0, 180) };
      this.dispatchEvent(ev);
    }

    _copy(text) {
      if (!text || text === "—") return;
      navigator.clipboard?.writeText(text).then(
        () => this._toast("已复制"),
        () => this._toast(text)
      );
    }

    _dot(ok, sm = false) {
      return `<span class="dot${sm ? " sm" : ""} ${ok ? "on" : "off"}" title="${
        ok ? "正常" : "异常"
      }"></span>`;
    }

    _render() {
      if (!this._config) return;
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });

      const healthOk = this._isOn(this._eid("binary_sensor", "health"));
      const udpxyOk = this._isOn(this._eid("binary_sensor", "udpxy_running"));
      const connections = this._stateStr(
        this._eid("sensor", "udpxy_connections"),
        "0"
      );
      const m3uTime = this._formatUpdateTime(
        this._stateStr(this._eid("sensor", "m3u_mtime"))
      );
      const epgTime = this._formatUpdateTime(
        this._stateStr(this._eid("sensor", "epg_mtime"))
      );
      const m3uUrl = this._stateStr(this._eid("sensor", "m3u_url"));
      const aptvUrl = this._stateStr(this._eid("sensor", "m3u_aptv_url"));
      const epgUrl = this._stateStr(this._eid("sensor", "epg_url"));
      const netOk = this._isOn(this._eid("binary_sensor", "network_ok"));
      const netSummarySt = this._state(this._eid("sensor", "network_summary"));
      const netSummary = netSummarySt?.state || "";
      const netDetail =
        this._lastDiagDetail || netSummarySt?.attributes?.detail || "";
      const hasNet = !!netSummarySt;

      const title = this._config.title || "IPTV 电视直播系统";
      const moreOpen = !!this._moreOpen;
      const connNum =
        connections === "unavailable" || connections === "unknown"
          ? "—"
          : String(connections);

      const netBox =
        moreOpen && hasNet
          ? `<div class="net ${netOk ? "ok" : "bad"}">
            <div class="net-title">${
              netOk ? "网络检测：正常" : "网络检测：有问题"
            } · ${escapeHtml(netSummary)}</div>
            ${
              netDetail
                ? `<pre class="net-detail">${escapeHtml(netDetail)}</pre>`
                : `<div class="hint">点「网络检测」刷新明细</div>`
            }
          </div>`
          : "";

      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          ha-card {
            padding: 18px 20px 16px;
            --muted: var(--secondary-text-color, #888);
            --line: color-mix(in srgb, var(--divider-color, #888) 45%, transparent);
            --ok: #2ecc71;
            --bad: #e74c3c;
          }
          .head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
          }
          .title {
            margin: 0;
            font-size: 1.55rem;
            font-weight: 650;
            letter-spacing: -0.02em;
            line-height: 1.15;
            font-family: Georgia, "Times New Roman", "Songti SC", serif;
          }
          .online-label {
            flex-shrink: 0;
            font-size: 0.92rem;
            font-weight: 560;
            line-height: 1.2;
            padding-top: 6px;
          }
          .online-label.on { color: var(--ok); }
          .online-label.off { color: var(--bad); }
          .dot {
            display: inline-block;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: var(--bad);
            box-shadow: 0 0 0 2px color-mix(in srgb, var(--bad) 25%, transparent);
          }
          .dot.on {
            background: var(--ok);
            box-shadow: 0 0 0 2px color-mix(in srgb, var(--ok) 25%, transparent);
          }
          .dot.sm {
            width: 12px;
            height: 12px;
          }
          .rows {
            display: grid;
            gap: 11px;
          }
          .kv {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            min-height: 22px;
          }
          .kv .k {
            font-size: 0.95rem;
            color: var(--primary-text-color, inherit);
          }
          .kv .v {
            font-size: 0.95rem;
            color: var(--primary-text-color, inherit);
            font-variant-numeric: tabular-nums;
            text-align: right;
          }
          .actions {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-top: 18px;
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
            padding: 10px 18px;
            border-radius: 4px;
            background: #3b82f6;
            color: #fff;
            font-size: 0.92rem;
            font-weight: 560;
          }
          button.primary:disabled {
            opacity: 0.65;
            cursor: wait;
          }
          button.ghost {
            font-size: 0.9rem;
            color: var(--primary-text-color, inherit);
            padding: 6px 2px;
          }
          .more {
            display: ${moreOpen ? "grid" : "none"};
            gap: 2px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--line);
          }
          .more button.item {
            display: flex;
            width: 100%;
            text-align: left;
            padding: 9px 2px;
            font-size: 0.9rem;
            border-radius: 4px;
          }
          .more button.item:hover {
            color: var(--primary-color, #3b82f6);
          }
          .urls {
            display: ${
              moreOpen && this._config.show_urls !== false ? "grid" : "none"
            };
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
          .url-row a:hover { color: var(--primary-color, #3b82f6); opacity: 1; }
          .url-row button.copy {
            flex-shrink: 0;
            font-size: 0.78rem;
            color: var(--muted);
            padding: 4px 0;
          }
          .hint {
            font-size: 0.78rem;
            color: var(--muted);
          }
          .net {
            margin-top: 10px;
          }
          .net-title {
            font-size: 0.88rem;
            font-weight: 600;
            margin-bottom: 6px;
          }
          .net.ok .net-title { color: var(--ok); }
          .net.bad .net-title { color: var(--bad); }
          .net-detail {
            margin: 0;
            padding: 8px 10px;
            font-size: 0.72rem;
            line-height: 1.45;
            white-space: pre-wrap;
            word-break: break-word;
            color: var(--muted);
            background: var(--secondary-background-color, rgba(0,0,0,.04));
            border-radius: 6px;
            max-height: 180px;
            overflow: auto;
          }
        </style>
        <ha-card>
          <div class="head">
            <h2 class="title">${escapeHtml(title)}</h2>
            <span class="online-label ${healthOk ? "on" : "off"}">${
              healthOk ? "在线" : "离线"
            }</span>
          </div>

          <div class="rows">
            <div class="kv">
              <span class="k">UDPXY状态</span>
              <span class="v">${this._dot(udpxyOk, true)}</span>
            </div>
            <div class="kv">
              <span class="k">网络状态</span>
              <span class="v">${this._dot(hasNet ? netOk : false, true)}</span>
            </div>
            <div class="kv">
              <span class="k">udp连接数</span>
              <span class="v">${escapeHtml(connNum)}</span>
            </div>
            <div class="kv">
              <span class="k">m3u更新时间</span>
              <span class="v">${escapeHtml(m3uTime)}</span>
            </div>
            <div class="kv">
              <span class="k">epg更新时间</span>
              <span class="v">${escapeHtml(epgTime)}</span>
            </div>
          </div>

          ${
            this._config.show_actions !== false
              ? `<div class="actions">
            <button class="primary" type="button" data-act="generate" ${
              this._updating ? "disabled" : ""
            }>${this._updating ? "更新中…" : "一键更新"}</button>
            <button class="ghost" type="button" id="more-toggle" aria-expanded="${moreOpen}">
              ${moreOpen ? "收起" : "更多"}
            </button>
          </div>
          <div class="more">
            <button class="item" type="button" data-act="network_diag">网络检测</button>
            <button class="item" type="button" data-act="run_m3u">生成 M3U</button>
            <button class="item" type="button" data-act="run_epg">生成 EPG</button>
            <button class="item" type="button" data-act="run_logos">生成台标</button>
            <button class="item" type="button" data-act="udpxy_restart">重启 UDPXY</button>
          </div>`
              : ""
          }
          ${netBox}
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

  function pad(n) {
    return String(n).padStart(2, "0");
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
          <label>标题 <input id="title" value="${escapeHtml(
            c.title || "IPTV 电视直播系统"
          )}" /></label>
          <label>实体前缀 <input id="prefix" value="${escapeHtml(
            c.prefix || "iptv_241"
          )}" placeholder="iptv_241" /></label>
        </div>
      `;
      const fire = () => {
        const title = this.shadowRoot.getElementById("title").value;
        const prefix = this.shadowRoot.getElementById("prefix").value;
        const ev = new Event("config-changed", {
          bubbles: true,
          composed: true,
        });
        ev.detail = {
          config: { ...c, type: `custom:${CARD_TYPE}`, title, prefix },
        };
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
      description: "IPTV 状态、一键更新与更多操作",
      preview: true,
    });
  }

  console.info(
    `%c IPTV Control Card %c v${CARD_VERSION} `,
    "background:#222;color:#fff;border-radius:4px 0 0 4px;padding:2px 6px",
    "background:#555;color:#fff;border-radius:0 4px 4px 0;padding:2px 6px"
  );
})();
