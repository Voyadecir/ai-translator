/* =========================================================
   Voyadecir main.js
   - Language menu (global)
   - "More" dropdown (global)
   - Minimal i18n engine (data-i18n)
   - Emits: window.dispatchEvent(new CustomEvent("voyadecir:lang-changed", {detail:{lang}}))
   ========================================================= */

(function () {
  "use strict";

  const STORAGE_KEY = "voyadecir_lang";

  // Keep these aligned with your UI list
  const SUPPORTED_LANGS = [
    { code: "en", label: "English" },
    { code: "es", label: "Español" },
    { code: "pt", label: "Português" },
    { code: "fr", label: "Français" },
    { code: "zh", label: "中文" },
    { code: "hi", label: "हिन्दी" },
    { code: "ar", label: "العربية" },
    { code: "bn", label: "বাংলা" },
    { code: "ur", label: "اردو" },
    { code: "py", label: "Guaraní" }, // keeping your existing list entry
  ];

  // Minimal UI strings. Expand as we tag elements with data-i18n.
  // Fallback is English if a key is missing in selected language.
  const I18N = {
    en: {
      "nav.home": "Home",
      "nav.translate": "Translate",
      "nav.mailbills": "Mail & Bills",
      "nav.more": "More",
      "nav.about": "About",
      "nav.contact": "Contact",
      "nav.privacy": "Privacy",
      "nav.terms": "Terms",

      "translate.title": "Translate",
      "translate.subtitle":
        "Paste text to translate. Voyadecir is designed to translate with context, and can provide multiple meanings when needed.",
      "translate.btn.translate": "Translate",
      "translate.btn.clear": "Clear",

      "translate.from": "From",
      "translate.to": "To",
      "translate.from.auto": "Auto",

      "translate.placeholder.input": "Type or paste text here…",
      "translate.placeholder.output": "Translation will appear here…",

      "clara.title": "Clara, your Assistant",
      "clara.placeholder": "Ask me about Voyadecir…",
      "clara.send": "Send",
    },
    es: {
      "nav.home": "Inicio",
      "nav.translate": "Traducir",
      "nav.mailbills": "Correo y Facturas",
      "nav.more": "Más",
      "nav.about": "Acerca de",
      "nav.contact": "Contacto",
      "nav.privacy": "Privacidad",
      "nav.terms": "Términos",

      "translate.title": "Traducir",
      "translate.subtitle":
        "Pega texto para traducir. Voyadecir está diseñado para traducir con contexto y puede dar varios significados cuando sea necesario.",
      "translate.btn.translate": "Traducir",
      "translate.btn.clear": "Borrar",

      "translate.from": "De",
      "translate.to": "A",
      "translate.from.auto": "Auto",

      "translate.placeholder.input": "Escribe o pega texto aquí…",
      "translate.placeholder.output": "La traducción aparecerá aquí…",

      "clara.title": "Clara, tu Asistente",
      "clara.placeholder": "Pregúntame sobre Voyadecir…",
      "clara.send": "Enviar",
    },
    pt: {
      "nav.home": "Início",
      "nav.translate": "Traduzir",
      "nav.mailbills": "Correio e Contas",
      "nav.more": "Mais",
      "nav.about": "Sobre",
      "nav.contact": "Contato",
      "nav.privacy": "Privacidade",
      "nav.terms": "Termos",

      "translate.title": "Traduzir",
      "translate.subtitle":
        "Cole texto para traduzir. O Voyadecir foi feito para traduzir com contexto e pode oferecer vários significados quando necessário.",
      "translate.btn.translate": "Traduzir",
      "translate.btn.clear": "Limpar",

      "translate.from": "De",
      "translate.to": "Para",
      "translate.from.auto": "Auto",

      "translate.placeholder.input": "Digite ou cole o texto aqui…",
      "translate.placeholder.output": "A tradução aparecerá aqui…",

      "clara.title": "Clara, sua Assistente",
      "clara.placeholder": "Pergunte sobre o Voyadecir…",
      "clara.send": "Enviar",
    },
  };

  function detectBrowserLang() {
    const raw = (navigator.language || "en").toLowerCase();
    const code = raw.split("-")[0];
    return SUPPORTED_LANGS.some((l) => l.code === code) ? code : "en";
  }

  function getLang() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LANGS.some((l) => l.code === stored)) return stored;
    return detectBrowserLang();
  }

  function setLang(code) {
    const finalCode = SUPPORTED_LANGS.some((l) => l.code === code) ? code : "en";
    localStorage.setItem(STORAGE_KEY, finalCode);
    document.documentElement.setAttribute("lang", finalCode);

    applyI18n(finalCode);
    updateLangButtonLabel(finalCode);

    window.dispatchEvent(
      new CustomEvent("voyadecir:lang-changed", { detail: { lang: finalCode } })
    );
  }

  function t(lang, key) {
    const pack = I18N[lang] || I18N.en;
    return (pack && pack[key]) || (I18N.en && I18N.en[key]) || key;
  }

  function applyI18n(lang) {
    // Text nodes
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (!key) return;
      el.textContent = t(lang, key);
    });

    // Placeholders
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (!key) return;
      el.setAttribute("placeholder", t(lang, key));
    });

    // Button values (input type=button/submit)
    document.querySelectorAll("[data-i18n-value]").forEach((el) => {
      const key = el.getAttribute("data-i18n-value");
      if (!key) return;
      el.setAttribute("value", t(lang, key));
    });

    // Optional: document title
    const titleKey = document.body.getAttribute("data-i18n-title");
    if (titleKey) document.title = t(lang, titleKey);
  }

  function updateLangButtonLabel(lang) {
    const btn = document.querySelector(".lang-menu__button");
    if (!btn) return;

    const codeBadge = btn.querySelector("[data-lang-badge]");
    if (codeBadge) codeBadge.textContent = (lang || "en").toUpperCase();
  }

  // ---------------------------
  // Language menu behavior
  // ---------------------------
  function initLanguageMenu() {
    const menu = document.querySelector(".lang-menu");
    const btn = document.querySelector(".lang-menu__button");
    const list = document.querySelector(".lang-menu__list");

    if (!menu || !btn || !list) return;

    // Ensure list has buttons hooked
    list.querySelectorAll("[data-lang]").forEach((item) => {
      item.addEventListener("click", () => {
        const code = item.getAttribute("data-lang");
        setLang(code);

        // close after select
        btn.setAttribute("aria-expanded", "false");
        menu.classList.remove("is-open");
      });
    });

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();

      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      menu.classList.toggle("is-open", !expanded);
    });

    // click outside closes
    document.addEventListener("click", () => {
      btn.setAttribute("aria-expanded", "false");
      menu.classList.remove("is-open");
    });

    // prevent inside clicks from closing
    menu.addEventListener("click", (e) => e.stopPropagation());
  }

  // ---------------------------
  // "More" dropdown behavior
  // ---------------------------
  function initMoreMenu() {
    const btn = document.querySelector(".nav-more__button");
    const list = document.querySelector(".nav-more__list");
    if (!btn || !list) return;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
    });

    // click outside closes
    document.addEventListener("click", () => {
      btn.setAttribute("aria-expanded", "false");
    });

    // prevent clicks inside
    list.addEventListener("click", (e) => e.stopPropagation());
  }

  // ---------------------------
  // Glass SVG filter injection (safe)
  // ---------------------------
  function ensureGlassFilter() {
    if (document.getElementById("lg-dist")) return;

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("style", "display:none");

    svg.innerHTML = `
      <filter id="lg-dist" x="0%" y="0%" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.008 0.008" numOctaves="2" seed="92" result="noise" />
        <feGaussianBlur in="noise" stdDeviation="2" result="blurred" />
        <feDisplacementMap in="SourceGraphic" in2="blurred" scale="70" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    `;

    document.body.appendChild(svg);
  }

  // ---------------------------
  // Boot
  // ---------------------------
  function boot() {
    ensureGlassFilter();
    initLanguageMenu();
    initMoreMenu();

    const lang = getLang();
    setLang(lang);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // Public access (for other scripts)
  window.Voyadecir = window.Voyadecir || {};
  window.Voyadecir.getLang = getLang;
  window.Voyadecir.setLang = setLang;
})();
