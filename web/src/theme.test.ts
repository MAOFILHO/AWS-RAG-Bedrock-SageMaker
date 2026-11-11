import { expect, test } from "vitest";
import app from "./App.tsx?raw";
import css from "./theme.css?raw";

const blocks = (re: RegExp) => [...css.matchAll(re)].map((m) => m[1]);
const [lightBlock] = blocks(/^:root \{([^}]*)\}/gm);
const [darkBlock] = blocks(/prefers-color-scheme: dark\) \{\s*:root \{([^}]*)\}/g);
const tokens = (block: string) => Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6});/gi)].map((m) => [m[1], m[2]]));
const light = tokens(lightBlock);
const dark = { ...light, ...tokens(darkBlock) };

const luminance = (hex: string) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const contrast = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const TEXT_PAIRS: [string, string][] = [
  ["text", "bg"],
  ["text", "surface"],
  ["muted", "bg"],
  ["muted", "surface"],
  ["primary", "bg"],
  ["on-primary", "primary"],
  ["error", "bg"],
  ["accent", "bg"],
];

test.each([
  ["light", light],
  ["dark", dark],
])("text contrast is at least 4.5 in %s", (_name, theme) => {
  for (const [fg, bg] of TEXT_PAIRS) {
    expect(contrast(theme[fg], theme[bg]), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5);
  }
});

test("the dark theme redefines every color token", () => {
  expect(Object.keys(tokens(darkBlock)).sort()).toEqual(Object.keys(light).sort());
});

const COLOR_FUNCTIONS = /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\(|#[0-9a-f]{3,8}\b/i;
const COLOR_PROPERTY = /^(?:color|background|border|outline|box-shadow|text-shadow|text-decoration|text-emphasis|column-rule|scrollbar-color|fill|stroke|caret-color|accent-color)(?:-|$)/;
const NEUTRAL = new Set(["transparent", "inherit", "currentcolor", "initial", "unset", "none", "solid", "dashed", "dotted", "double", "wavy", "underline", "overline", "line-through", "auto", "!important"]);
const declarations = (source: string) => [...source.matchAll(/([\w-]+)\s*:\s*([^;{}]+)(?:;|(?=\}))/g)].map((m) => ({ property: m[1], value: m[2].trim() }));
const strayColors = (source: string) =>
  declarations(source)
    .filter(({ property }) => COLOR_PROPERTY.test(property) && !property.startsWith("--"))
    .flatMap(({ property, value }) =>
      value
        .replace(/var\(\s*--[\w-]+\s*,?/g, " ")
        .replace(/[\d.]+(?:px|rem|em|%)?/g, " ")
        .split(/[\s,()]+/)
        .filter((word) => word && !NEUTRAL.has(word.toLowerCase()))
        .map((word) => `${property}: ${word}`),
    );

test("the color check catches named and oklch() colors", () => {
  expect(strayColors("a { color: red; }")).toEqual(["color: red"]);
  expect(strayColors("a { color: red }")).toEqual(["color: red"]);
  expect(strayColors("a { background: oklch(0.5 0.1 200); }")).not.toEqual([]);
  expect(strayColors("a { color: var(--x, red); }")).toEqual(["color: red"]);
  expect(strayColors("a { color: var(--x, var(--y)); }")).toEqual([]);
  expect(strayColors("a { border: 1px solid var(--border); background: transparent; }")).toEqual([]);
  expect(strayColors("a { text-decoration-color: red; }")).toEqual(["text-decoration-color: red"]);
  expect(strayColors("a { text-decoration: underline wavy red; }")).toEqual(["text-decoration: red"]);
  expect(strayColors("a { color: var(--text) !important; }")).toEqual([]);
  expect(COLOR_FUNCTIONS.test("color: oklch(0.5 0.1 200)")).toBe(true);
});

test("no color is set outside the tokens", () => {
  const outside = css.replace(/:root \{[^}]*\}/g, "");
  expect(outside).not.toMatch(COLOR_FUNCTIONS);
  expect(strayColors(outside)).toEqual([]);
  expect(app).not.toMatch(/style=/);
  expect(app).not.toMatch(COLOR_FUNCTIONS);
});
