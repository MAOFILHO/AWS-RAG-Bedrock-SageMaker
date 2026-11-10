import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const reply = (status: number, body: object) => Promise.resolve(new Response(JSON.stringify(body), { status }));

test("shows the answer after the user types a question and presses Enter", async () => {
  const fetchMock = vi.fn(() => reply(200, { answer: "SDKs wrap APIs." }));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), "What are SDKs?{Enter}");
  expect(await screen.findByText("SDKs wrap APIs.")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/ask",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ question: "What are SDKs?" }) }),
  );
});

test("shows the plain error the API returns", async () => {
  vi.stubGlobal("fetch", () => reply(400, { error: "Type a question first." }));
  render(<App />);
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), " {Enter}");
  expect((await screen.findByRole("alert")).textContent).toBe("Type a question first.");
});

test("shows one plain error when the API cannot be reached", async () => {
  vi.stubGlobal("fetch", () => Promise.reject(new TypeError("failed")));
  render(<App />);
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), "Hi?{Enter}");
  expect((await screen.findByRole("alert")).textContent).toBe("Could not reach the server. Try again.");
});
