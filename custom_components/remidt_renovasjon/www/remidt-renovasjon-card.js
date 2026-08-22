class RemidtRenovasjonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = undefined;
  }

  setConfig(config) {
    if (!config || !Array.isArray(config.entities) || config.entities.length === 0) {
      throw new Error("The ReMidt Renovasjon card requires an entities list.");
    }

    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return this._config.entities ? this._config.entities.length : 1;
  }

  _render() {
    if (!this.shadowRoot || !this._config.entities) {
      return;
    }

    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; }
      ha-card { padding: 12px; }
      .title {
        color: var(--primary-text-color);
        font-size: 1.1rem;
        font-weight: 500;
        margin: 0 4px 10px;
      }
      .tiles {
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      }
      .tile {
        align-items: center;
        background: var(--ha-card-background, var(--card-background-color));
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        display: flex;
        gap: 10px;
        min-height: 68px;
        padding: 10px;
        transition: background-color 180ms ease;
      }
      .tile.yellow {
        background: var(--warning-color, #f6c945);
        color: var(--primary-text-color);
      }
      .tile.red {
        background: var(--error-color, #db4437);
        color: var(--text-primary-color, #fff);
      }
      .icon {
        color: var(--primary-text-color);
        flex: 0 0 auto;
        height: 28px;
        width: 28px;
      }
      .red .icon { color: inherit; }
      .name { font-size: 0.9rem; line-height: 1.2; }
      .days {
        font-size: 1.25rem;
        font-weight: 600;
        line-height: 1.2;
        margin-top: 3px;
      }
      .unavailable { opacity: 0.65; }
    `;

    const card = document.createElement("ha-card");
    if (this._config.title) {
      const title = document.createElement("h2");
      title.className = "title";
      title.textContent = this._config.title;
      card.appendChild(title);
    }

    const tiles = document.createElement("div");
    tiles.className = "tiles";
    for (const entityId of this._config.entities) {
      tiles.appendChild(this._createTile(entityId));
    }
    card.appendChild(tiles);

    this.shadowRoot.replaceChildren(style, card);
  }

  _createTile(entityId) {
    const state = this._hass?.states?.[entityId];
    const tile = document.createElement("div");
    const days = Number(state?.state);
    const color = Number.isFinite(days) && days <= 1
      ? "red"
      : Number.isFinite(days) && days <= 3 ? "yellow" : "";
    tile.className = `tile ${color} ${state ? "" : "unavailable"}`;

    const icon = document.createElement("ha-icon");
    icon.className = "icon";
    icon.setAttribute("icon", state?.attributes?.icon || "mdi:trash-can-outline");

    const content = document.createElement("div");
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = state?.attributes?.friendly_name || entityId;
    const value = document.createElement("div");
    value.className = "days";
    value.textContent = Number.isFinite(days) ? `${days} days` : "Unavailable";

    content.append(name, value);
    tile.append(icon, content);
    tile.addEventListener("click", () => this._hass?.moreInfo(entityId));
    return tile;
  }
}

customElements.define("remidt-renovasjon-card", RemidtRenovasjonCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "remidt-renovasjon-card",
  name: "ReMidt Renovasjon days card",
  description: "Shows waste collection countdowns with warning colors.",
  preview: true,
});
