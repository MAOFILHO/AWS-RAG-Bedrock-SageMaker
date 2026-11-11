import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const reply = (status: number, body: object) => Promise.resolve(new Response(JSON.stringify(body), { status }));

const SOURCES = [
  { id: "web", name: "Web", description: "Two IBM pages." },
  { id: "pdf", name: "PDF", description: "The K21 PDF." },
  { id: "sql", name: "SQL", description: "The Chinook database." },
];
const serve = (ask: (body: string) => Promise<Response>) =>
  vi.fn((url: string, init?: RequestInit) => (url === "/api/sources" ? reply(200, SOURCES) : ask(String(init?.body))));

test("shows the answer after the user types a question and presses Enter", async () => {
  const fetchMock = serve(() => reply(200, { answer: "SDKs wrap APIs." }));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), "What are SDKs?{Enter}");
  expect(await screen.findByText("SDKs wrap APIs.")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/ask",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ question: "What are SDKs?", source: "pdf" }) }),
  );
});

test("shows the plain error the API returns", async () => {
  vi.stubGlobal("fetch", serve(() => reply(400, { error: "Type a question first." })));
  render(<App />);
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), " {Enter}");
  expect((await screen.findByRole("alert")).textContent).toBe("Type a question first.");
});

test("shows one plain error when the API cannot be reached", async () => {
  vi.stubGlobal("fetch", serve(() => Promise.reject(new TypeError("failed"))));
  render(<App />);
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), "Hi?{Enter}");
  expect((await screen.findByRole("alert")).textContent).toBe("Could not reach the server. Try again.");
});

test("lists web, PDF and SQL with a one-line description each", async () => {
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: "" })));
  render(<App />);
  for (const item of SOURCES) {
    expect(await screen.findByRole("radio", { name: `${item.name}: ${item.description}` })).toBeTruthy();
  }
});

test("sends the question to the chosen Source", async () => {
  const fetchMock = serve(() => reply(200, { answer: "59 customers." }));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await userEvent.click(await screen.findByRole("radio", { name: /^SQL/ }));
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), "How many customers?{Enter}");
  expect(await screen.findByText("59 customers.")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/ask",
    expect.objectContaining({ body: JSON.stringify({ question: "How many customers?", source: "sql" }) }),
  );
});

test("every control has an accessible name", async () => {
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: "" })));
  render(<App />);
  await screen.findAllByRole("radio");
  for (const control of [...screen.getAllByRole("radio"), screen.getByRole("textbox"), screen.getByRole("button")]) {
    expect(control.getAttribute("aria-label") || control.textContent || control.closest("label")?.textContent).toBeTruthy();
  }
  expect(screen.getByRole("button", { name: "Ask" })).toBeTruthy();
});
