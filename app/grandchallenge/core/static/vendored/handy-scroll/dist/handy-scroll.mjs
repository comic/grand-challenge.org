/*!
handy-scroll v2.0.3
https://amphiluke.github.io/handy-scroll/
(c) 2024 Amphiluke
*/
const h = ':host{bottom:0;min-height:17px;overflow:auto;position:fixed}.strut{height:1px;overflow:hidden;pointer-events:none;&:before{content:" "}}:host,.strut{font-size:1px;line-height:0;margin:0;padding:0}:host(:state(latent)){bottom:110vh;.strut:before{content:"  "}}:host([viewport]:not([hidden])){display:block}:host([viewport]){position:sticky}:host([viewport]:state(latent)){position:fixed}';
let n = (s) => `Attribute ‘${s}’ must reference a valid container ‘id’`;
class o extends HTMLElement {
  static get observedAttributes() {
    return ["owner", "viewport", "hidden"];
  }
  #o = null;
  #t = null;
  #e = null;
  #s = null;
  #i = null;
  #n = null;
  #r = !0;
  #l = !0;
  get owner() {
    return this.getAttribute("owner");
  }
  set owner(t) {
    this.setAttribute("owner", t);
  }
  get viewport() {
    return this.getAttribute("viewport");
  }
  set viewport(t) {
    this.setAttribute("viewport", t);
  }
  get #h() {
    return this.#o.states.has("latent");
  }
  set #h(t) {
    this.#o.states[t ? "add" : "delete"]("latent");
  }
  constructor() {
    super();
    let t = this.attachShadow({ mode: "open" }), e = document.createElement("style");
    e.textContent = h, t.appendChild(e), this.#s = document.createElement("div"), this.#s.classList.add("strut"), t.appendChild(this.#s), this.#o = this.attachInternals();
  }
  connectedCallback() {
    this.#a(), this.#c(), this.#u(), this.#p(), this.update();
  }
  disconnectedCallback() {
    this.#w(), this.#f(), this.#e = this.#t = null;
  }
  attributeChangedCallback(t) {
    if (this.#i) {
      if (t === "hidden") {
        this.hasAttribute("hidden") || this.update();
        return;
      }
      t === "owner" ? this.#a() : t === "viewport" && this.#c(), this.#w(), this.#f(), this.#u(), this.#p(), this.update();
    }
  }
  #a() {
    let t = this.getAttribute("owner");
    if (this.#e = document.getElementById(t), !this.#e)
      throw new DOMException(n("owner"));
  }
  #c() {
    if (!this.hasAttribute("viewport")) {
      this.#t = window;
      return;
    }
    let t = this.getAttribute("viewport");
    if (this.#t = document.getElementById(t), !this.#t)
      throw new DOMException(n("viewport"));
  }
  #u() {
    this.#i = new AbortController();
    let t = { signal: this.#i.signal };
    this.#t.addEventListener("scroll", () => this.#v(), t), this.#t === window && this.#t.addEventListener("resize", () => this.update(), t), this.addEventListener("scroll", () => {
      this.#r && !this.#h && this.#b(), this.#r = !0;
    }, t), this.#e.addEventListener("scroll", () => {
      this.#l && this.#d(), this.#l = !0;
    }, t), this.#e.addEventListener("focusin", () => {
      setTimeout(() => {
        this.isConnected && this.#d();
      }, 0);
    }, t);
  }
  #w() {
    this.#i?.abort(), this.#i = null;
  }
  #p() {
    this.#t !== window && (this.#n = new ResizeObserver(([t]) => {
      t.contentBoxSize?.[0]?.inlineSize && this.update();
    }), this.#n.observe(this.#t));
  }
  #f() {
    this.#n?.disconnect(), this.#n = null;
  }
  #b() {
    let { scrollLeft: t } = this;
    this.#e.scrollLeft !== t && (this.#l = !1, this.#e.scrollLeft = t);
  }
  #d() {
    let { scrollLeft: t } = this.#e;
    this.scrollLeft !== t && (this.#r = !1, this.scrollLeft = t);
  }
  #v() {
    let t = this.scrollWidth <= this.offsetWidth;
    if (!t) {
      let e = this.#e.getBoundingClientRect(), i = this.#t === window ? window.innerHeight || document.documentElement.clientHeight : this.#t.getBoundingClientRect().bottom;
      t = e.bottom <= i || e.top > i;
    }
    this.#h !== t && (this.#h = t);
  }
  update() {
    let { clientWidth: t, scrollWidth: e } = this.#e, { style: i } = this;
    i.width = `${t}px`, this.#t === window && (i.left = `${this.#e.getBoundingClientRect().left}px`), this.#s.style.width = `${e}px`, e > t && (i.height = `${this.offsetHeight - this.clientHeight + 1}px`), this.#d(), this.#v();
  }
}
customElements.define("handy-scroll", o);
export {
  o as default
};
