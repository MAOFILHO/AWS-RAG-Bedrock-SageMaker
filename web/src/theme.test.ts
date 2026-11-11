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
// CSS Color 4 named colors (148) and system colors (19).
const NAMED_COLORS = new Set(
  (
    "aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen " +
    "accentcolor accentcolortext activetext buttonborder buttonface buttontext canvas canvastext field fieldtext graytext highlight highlighttext linktext mark marktext selecteditem selecteditemtext visitedtext"
  ).split(" "),
);
const declarations = (source: string) => [...source.matchAll(/([\w-]+)\s*:\s*([^;{}]+)(?:;|(?=\}))/g)].map((m) => ({ property: m[1], value: m[2].trim() }));
const strayColors = (source: string) =>
  declarations(source)
    .filter(({ property }) => !property.startsWith("--"))
    .flatMap(({ property, value }) => {
      const bare = value.replace(/url\([^)]*\)|"[^"]*"|'[^']*'/g, " ");
      const named = bare.split(/[\s,()/]+/).filter((word) => NAMED_COLORS.has(word.toLowerCase()));
      const functions = bare.match(new RegExp(COLOR_FUNCTIONS, "gi")) ?? [];
      return [...named, ...functions].map((word) => `${property}: ${word}`);
    });

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
  expect(strayColors("a { border-collapse: collapse; }")).toEqual([]);
  expect(strayColors("a { background: url(x.png) no-repeat; }")).toEqual([]);
  expect(strayColors("a { background: url(x.png) no-repeat center / cover red; }")).toEqual(["background: red"]);
  expect(strayColors("a { border-radius: 4px; border-top-width: thin; border-spacing: 2px; background-size: cover; }")).toEqual([]);
  expect(strayColors("a { background-image: linear-gradient(red, var(--bg)); }")).toEqual(["background-image: red"]);
  expect(strayColors("a { border-image: linear-gradient(red, var(--bg)) 1; }")).toEqual(["border-image: red"]);
  expect(strayColors("a { -webkit-text-fill-color: red; }")).toEqual(["-webkit-text-fill-color: red"]);
  expect(strayColors("a { outline: 2px solid Canvas; }")).toEqual(["outline: Canvas"]);
  expect(strayColors("a { box-shadow: inset 0 0 0 1px var(--border); border: thin groove var(--border); }")).toEqual([]);
  expect(strayColors("a { color-scheme: light dark; background: linear-gradient(45deg, var(--bg), var(--surface)); }")).toEqual([]);
  expect(strayColors("a { font: 1rem system-ui, \"Red Hat\", sans-serif; }")).toEqual([]);
  expect(COLOR_FUNCTIONS.test("color: oklch(0.5 0.1 200)")).toBe(true);
});

test("no color is set outside the tokens", () => {
  const outside = css.replace(/:root \{[^}]*\}/g, "");
  expect(outside).not.toMatch(COLOR_FUNCTIONS);
  expect(strayColors(outside)).toEqual([]);
  expect(app).not.toMatch(/style=/);
  expect(app).not.toMatch(COLOR_FUNCTIONS);
});
