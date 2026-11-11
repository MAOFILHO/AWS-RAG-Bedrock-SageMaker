// QA for issue #77: layout, keyboard focus, accessible names, token-only colors, contrast, screenshots.
const { chromium } = require("/Users/marco/.claude/skills/gstack/node_modules/playwright-core");
const fs = require("fs");
const OUT = process.argv[2];
const URL = "http://localhost:4177/";
fs.mkdirSync(OUT, { recursive: true });

const SOURCES = [
  { id: "web", name: "Web", description: "Two IBM pages on cloud computing and data science." },
  { id: "pdf", name: "PDF", description: "The K21 course PDF." },
  { id: "sql", name: "SQL", description: "The Chinook music store database, read-only." },
];
const LONG = "Answer " + "x".repeat(300) + " https://example.com/" + "a".repeat(200);

const TOKENS = {
  light: ["#ffffff", "#f3f6fa", "#1b2430", "#4a5565", "#8593a6", "#0b5cad", "#a84a00", "#b42318"],
  dark: ["#0f1722", "#172231", "#e8edf3", "#b4bfcc", "#7b8a9d", "#6fb1f2", "#f5a65b", "#ff9b90"],
};

const results = [];
const check = (name, ok, detail) => { results.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"} ${name} ${detail ? JSON.stringify(detail) : ""}`); };

async function page(browser, { width, height, scheme, ask }) {
  const ctx = await browser.newContext({ viewport: { width, height }, colorScheme: scheme });
  const p = await ctx.newPage();
  const errors = [];
  p.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  p.on("pageerror", (e) => errors.push(String(e)));
  await p.route("**/api/sources", (r) => r.fulfill({ json: SOURCES }));
  await p.route("**/api/ask", (r) => ask === "error"
    ? r.fulfill({ status: 502, json: { error: "The answer service is not available. Try again." } })
    : r.fulfill({ json: { answer: ask === "long" ? LONG : "Cloud computing is on-demand compute." } }));
  await p.goto(URL);
  await p.getByRole("radio").first().waitFor();
  return { ctx, p, errors };
}

const noScroll = (p) => p.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));

(async () => {
  const browser = await chromium.launch();
  // AC2: no horizontal scroll at 390 (and the other viewports), light + dark, with answer and error states.
  for (const scheme of ["light", "dark"]) {
    for (const [w, h] of [[390, 844], [375, 667], [1024, 768], [1440, 900], [1920, 1080]]) {
      for (const ask of ["short", "long", "error"]) {
        const { ctx, p, errors } = await page(browser, { width: w, height: h, scheme, ask });
        await p.getByRole("textbox", { name: "Question" }).fill("What is cloud computing?");
        await p.getByRole("button", { name: "Ask" }).click();
        await (ask === "error" ? p.getByRole("alert") : p.locator(".answer")).waitFor();
        const m = await noScroll(p);
        check(`no-hscroll ${scheme} ${w} ${ask}`, m.scrollWidth <= m.innerWidth, m);
        check(`no-console-errors ${scheme} ${w} ${ask}`, errors.length === 0, errors);
        await ctx.close();
      }
    }
  }

  for (const scheme of ["light", "dark"]) {
    const { ctx, p } = await page(browser, { width: 390, height: 844, scheme, ask: "short" });
    // AC3: keyboard reach + visible focus + accessible names.
    const stops = [];
    for (let i = 0; i < 6; i++) {
      await p.keyboard.press("Tab");
      stops.push(await p.evaluate(() => {
        const el = document.activeElement;
        const cs = getComputedStyle(el);
        return { tag: el.tagName, type: el.type || "", value: el.value || "", focusVisible: el.matches(":focus-visible"), outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth, outlineColor: cs.outlineColor };
      }));
    }
    const kinds = new Set(stops.map((s) => `${s.tag}:${s.type}`));
    check(`keyboard reaches radio, textbox, button (${scheme})`, ["INPUT:radio", "INPUT:text", "BUTTON:submit"].every((k) => kinds.has(k)), stops);
    check(`focus ring visible on every stop (${scheme})`, stops.filter((s) => s.tag !== "BODY").every((s) => s.focusVisible && s.outlineStyle !== "none" && parseFloat(s.outlineWidth) >= 2), stops);
    // arrow keys move within the radio group
    await p.getByRole("radio", { name: /PDF/ }).focus();
    await p.keyboard.press("ArrowDown");
    check(`arrow key picks next Source (${scheme})`, await p.getByRole("radio", { name: /SQL/ }).isChecked());
    await p.keyboard.press("ArrowUp");
    // screenshot of the focus ring on the radio and on the button
    await p.keyboard.press("Tab");
    await p.screenshot({ path: `${OUT}/ac3-focus-textbox-${scheme}.png` });
    await p.keyboard.press("Tab");
    await p.screenshot({ path: `${OUT}/ac3-focus-button-${scheme}.png` });

    const names = await p.evaluate(() => [...document.querySelectorAll("input,button,select,textarea,a[href]")].map((e) => ({ tag: e.tagName, type: e.type, labelled: !!(e.getAttribute("aria-label") || (e.labels && [...e.labels].some((l) => l.textContent.trim())) || e.textContent.trim()) })));
    check(`every control has an accessible name (${scheme})`, names.every((n) => n.labelled), names);
    for (const [role, name] of [["radio", /Web/], ["radio", /PDF/], ["radio", /SQL/], ["textbox", "Question"], ["button", "Ask"]]) {
      check(`role ${role} named ${name} (${scheme})`, (await p.getByRole(role, { name }).count()) === 1);
    }

    // AC1: every computed color on the page is a token (or transparent / native control).
    await p.getByRole("textbox", { name: "Question" }).fill("q");
    await p.getByRole("button", { name: "Ask" }).click();
    await p.locator(".answer").waitFor();
    const colors = await p.evaluate(() => {
      const hex = (c) => { const m = c.match(/rgba?\((\d+), (\d+), (\d+)(?:, ([\d.]+))?\)/); if (!m) return c; if (m[4] !== undefined && +m[4] === 0) return "transparent"; return "#" + [m[1], m[2], m[3]].map((n) => (+n).toString(16).padStart(2, "0")).join(""); };
      const seen = new Set();
      for (const el of [document.documentElement, document.body, ...document.body.querySelectorAll("*")]) {
        const cs = getComputedStyle(el);
        const props = ["color", "backgroundColor"];
        for (const side of ["Top", "Right", "Bottom", "Left"]) if (parseFloat(cs[`border${side}Width`]) > 0) props.push(`border${side}Color`);
        if (cs.outlineStyle !== "none") props.push("outlineColor");
        for (const prop of props) seen.add(`${el.tagName.toLowerCase()}.${prop}=${hex(cs[prop])}`);
      }
      return [...seen];
    });
    const off = colors.filter((c) => { const v = c.split("=")[1]; return v !== "transparent" && !TOKENS[scheme].includes(v); });
    check(`only token colors in computed styles (${scheme})`, off.length === 0, off);

    // AC4: computed text contrast in the live page.
    const pairs = await p.evaluate(() => {
      const rgb = (c) => c.match(/\d+(\.\d+)?/g).slice(0, 4).map(Number);
      const lum = ([r, g, b]) => { const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
      const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor); if (c.length < 4 || c[3] > 0) return c; } return [255, 255, 255]; };
      const out = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const n = walker.currentNode; if (!n.textContent.trim()) continue;
        const el = n.parentElement; const fg = rgb(getComputedStyle(el).color); const bg = bgOf(el);
        const [hi, lo] = [lum(fg), lum(bg)].sort((a, b) => b - a);
        out.push({ text: n.textContent.trim().slice(0, 30), ratio: +((hi + 0.05) / (lo + 0.05)).toFixed(2) });
      }
      for (const el of document.querySelectorAll("input[type=text],button")) {
        const fg = rgb(getComputedStyle(el).color); const bg = bgOf(el); const [hi, lo] = [lum(fg), lum(bg)].sort((a, b) => b - a);
        out.push({ text: `<${el.tagName.toLowerCase()}>`, ratio: +((hi + 0.05) / (lo + 0.05)).toFixed(2) });
      }
      return out;
    });
    check(`live text contrast >= 4.5 (${scheme})`, pairs.every((x) => x.ratio >= 4.5), pairs);
    await ctx.close();
  }

  // Screenshots at standard viewports, light + dark, plus the AC 390 / 1440 widths.
  for (const scheme of ["light", "dark"]) {
    for (const [label, w, h] of [["desktop", 1920, 1080], ["tablet", 1024, 768], ["mobile", 375, 667], ["mobile-390", 390, 844], ["desktop-1440", 1440, 900]]) {
      const { ctx, p } = await page(browser, { width: w, height: h, scheme, ask: "short" });
      await p.getByRole("textbox", { name: "Question" }).fill("What is cloud computing?");
      await p.getByRole("button", { name: "Ask" }).click();
      await p.locator(".answer").waitFor();
      await p.screenshot({ path: `${OUT}/${label}-${scheme}.png` });
      await ctx.close();
    }
  }
  await browser.close();
  fs.writeFileSync(`${OUT}/browser-checks.json`, JSON.stringify(results, null, 1));
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
