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

test("no color is set outside the tokens", () => {
  const outside = css.replace(/:root \{[^}]*\}/g, "");
  expect(outside).not.toMatch(/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i);
  expect(app).not.toMatch(/style=|#[0-9a-f]{6}\b/i);
});
