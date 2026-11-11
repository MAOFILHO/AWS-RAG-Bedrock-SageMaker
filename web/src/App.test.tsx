import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
const DEFAULT_PDF = { name: "k21.pdf", uploaded: false };
const serve = (ask: (body: string) => Promise<Response>) =>
  vi.fn((url: string, init?: RequestInit) => {
    if (url === "/api/sources") return reply(200, SOURCES);
    if (url === "/api/pdf") return reply(200, DEFAULT_PDF);
    return ask(String(init?.body));
  });

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

const ask = (text: string) => userEvent.type(screen.getByRole("textbox", { name: /question/i }), `${text}{Enter}`);

test("keeps three questions and answers in order, each with its Source name", async () => {
  let n = 0;
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: `Answer ${++n}` })));
  render(<App />);
  await screen.findByRole("radio", { name: /^PDF/ });
  await ask("One?");
  await screen.findByText("Answer 1");
  await userEvent.click(screen.getByRole("radio", { name: /^SQL/ }));
  await ask("Two?");
  await screen.findByText("Answer 2");
  await ask("Three?");
  await screen.findByText("Answer 3");
  const items = screen.getAllByRole("listitem").map((item) => item.textContent);
  expect(items).toEqual(["One?PDFAnswer 1", "Two?SQLAnswer 2", "Three?SQLAnswer 3"]);
});

test("shows a loading state and turns the send button off while a question runs", async () => {
  let finish: (value: Response) => void = () => {};
  vi.stubGlobal("fetch", serve(() => new Promise<Response>((resolve) => (finish = resolve))));
  render(<App />);
  await ask("Slow?");
  expect((await screen.findByRole("status")).textContent).toBe("Thinking...");
  expect((screen.getByRole("button", { name: "Send" }) as HTMLButtonElement).disabled).toBe(true);
  finish(new Response(JSON.stringify({ answer: "Done." }), { status: 200 }));
  await screen.findByText("Done.");
  expect(screen.queryByRole("status")).toBeNull();
  expect((screen.getByRole("button", { name: "Send" }) as HTMLButtonElement).disabled).toBe(false);
});

test("pressing Enter again while a question runs does not send it twice", async () => {
  let finish: (value: Response) => void = () => {};
  const fetchMock = serve(() => new Promise<Response>((resolve) => (finish = resolve)));
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await ask("Slow?");
  await screen.findByRole("status");
  await userEvent.type(screen.getByRole("textbox", { name: /question/i }), "{Enter}");
  finish(new Response(JSON.stringify({ answer: "Done." }), { status: 200 }));
  await screen.findByText("Done.");
  expect(fetchMock.mock.calls.filter(([url]) => url === "/api/ask")).toHaveLength(1);
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
});

test("a failed question keeps the thread, shows one line and allows a retry", async () => {
  let calls = 0;
  vi.stubGlobal(
    "fetch",
    serve(() => (++calls === 2 ? reply(502, { error: "The answer service is not available. Try again." }) : reply(200, { answer: `Answer ${calls}` }))),
  );
  render(<App />);
  await ask("One?");
  await screen.findByText("Answer 1");
  await ask("Two?");
  expect((await screen.findByRole("alert")).textContent).toBe("The answer service is not available. Try again.");
  expect(screen.getAllByRole("listitem")).toHaveLength(1);
  expect((screen.getByRole("textbox", { name: /question/i }) as HTMLInputElement).value).toBe("Two?");
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText("Answer 3");
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
});

test("shows a missing AWS access message in plain words", async () => {
  const message = "No AWS access found. Run `aws configure`, enable Bedrock model access, then try again.";
  vi.stubGlobal("fetch", serve(() => reply(502, { error: message })));
  render(<App />);
  await ask("Hi?");
  expect((await screen.findByRole("alert")).textContent).toBe(message);
});

test("the clear button empties the thread", async () => {
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: "An answer." })));
  render(<App />);
  await ask("Hi?");
  await screen.findByText("An answer.");
  await userEvent.click(screen.getByRole("button", { name: "Clear" }));
  expect(screen.queryByText("An answer.")).toBeNull();
  expect(screen.queryAllByRole("listitem")).toHaveLength(0);
});

const pdfFile = (name = "notes.pdf") => new File(["%PDF-1.4"], name, { type: "application/pdf" });

test("names the default PDF as active before any upload and offers no switch back", async () => {
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: "" })));
  render(<App />);
  expect(await screen.findByText("Active PDF: k21.pdf (default)")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Use the default PDF" })).toBeNull();
});

test("uploads a PDF, shows progress, then ready and the active name", async () => {
  let finish: (value: Response) => void = () => {};
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (url === "/api/sources") return reply(200, SOURCES);
    if (init?.method === "PUT") return new Promise<Response>((resolve) => (finish = resolve));
    return reply(200, DEFAULT_PDF);
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByText("Active PDF: k21.pdf (default)");
  const file = pdfFile();
  await userEvent.upload(screen.getByLabelText("Upload a PDF"), file);
  expect((await screen.findByRole("status")).textContent).toBe("Uploading notes.pdf...");
  expect(fetchMock).toHaveBeenCalledWith("/api/pdf?name=notes.pdf", expect.objectContaining({ method: "PUT", body: file }));
  finish(new Response(JSON.stringify({ name: "notes.pdf", uploaded: true }), { status: 200 }));
  expect((await screen.findByRole("status")).textContent).toBe("notes.pdf is ready");
  expect(screen.getByText("Active PDF: notes.pdf (uploaded)")).toBeTruthy();
});

test("asks the uploaded PDF, then switches back to the default and asks that", async () => {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (url === "/api/sources") return reply(200, SOURCES);
    if (init?.method === "PUT") return reply(200, { name: "notes.pdf", uploaded: true });
    if (init?.method === "DELETE") return reply(200, DEFAULT_PDF);
    if (url === "/api/pdf") return reply(200, DEFAULT_PDF);
    return reply(200, { answer: "An answer." });
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByText("Active PDF: k21.pdf (default)");
  await userEvent.upload(screen.getByLabelText("Upload a PDF"), pdfFile());
  await screen.findByText("Active PDF: notes.pdf (uploaded)");
  await ask("Kiwis?");
  await screen.findByText("An answer.");
  expect(fetchMock).toHaveBeenCalledWith("/api/ask", expect.objectContaining({ body: JSON.stringify({ question: "Kiwis?", source: "pdf" }) }));
  await userEvent.click(screen.getByRole("button", { name: "Use the default PDF" }));
  expect(await screen.findByText("Active PDF: k21.pdf (default)")).toBeTruthy();
  expect(fetchMock).toHaveBeenCalledWith("/api/pdf", expect.objectContaining({ method: "DELETE" }));
  expect(screen.queryByRole("button", { name: "Use the default PDF" })).toBeNull();
  await ask("Again?");
  await screen.findAllByText("An answer.");
  expect(fetchMock).toHaveBeenLastCalledWith("/api/ask", expect.objectContaining({ body: JSON.stringify({ question: "Again?", source: "pdf" }) }));
});

test("a PDF that cannot be read shows one line and keeps the active PDF", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) =>
      url === "/api/sources" ? reply(200, SOURCES) : init?.method === "PUT" ? reply(400, { error: "That file is not a readable PDF." }) : reply(200, DEFAULT_PDF),
    ),
  );
  render(<App />);
  await screen.findByText("Active PDF: k21.pdf (default)");
  await userEvent.upload(screen.getByLabelText("Upload a PDF"), pdfFile("bad.pdf"));
  expect((await screen.findByRole("alert")).textContent).toBe("That file is not a readable PDF.");
  expect(screen.getByText("Active PDF: k21.pdf (default)")).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
});

test("a PDF dropped on the panel uploads like a chosen one", async () => {
  const fetchMock = vi.fn((url: string, init?: RequestInit) =>
    url === "/api/sources" ? reply(200, SOURCES) : init?.method === "PUT" ? reply(200, { name: "dropped.pdf", uploaded: true }) : reply(200, DEFAULT_PDF),
  );
  vi.stubGlobal("fetch", fetchMock);
  render(<App />);
  await screen.findByText("Active PDF: k21.pdf (default)");
  fireEvent.drop(screen.getByText("or drop a PDF here"), { dataTransfer: { files: [pdfFile("dropped.pdf")] } });
  expect(await screen.findByText("Active PDF: dropped.pdf (uploaded)")).toBeTruthy();
});

test("the PDF panel shows only while the PDF Source is picked", async () => {
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: "" })));
  render(<App />);
  await screen.findByText("Active PDF: k21.pdf (default)");
  await userEvent.click(screen.getByRole("radio", { name: /^SQL/ }));
  expect(screen.queryByText(/^Active PDF/)).toBeNull();
});

const accessibleName = (control: Element) => {
  const labelledby = control.getAttribute("aria-labelledby")?.split(/\s+/).map((id) => document.getElementById(id)?.textContent ?? "").join(" ");
  const labels = "labels" in control ? [...(control as HTMLInputElement).labels!].map((label) => label.textContent) : [];
  return (control.getAttribute("aria-label") || labelledby || labels.join(" ") || (control.tagName === "BUTTON" ? control.textContent : "") || "").trim();
};

test("every control has an accessible name", async () => {
  vi.stubGlobal("fetch", serve(() => reply(200, { answer: "" })));
  const { container } = render(<App />);
  await screen.findAllByRole("radio");
  await screen.findByText("Active PDF: k21.pdf (default)");
  const controls = [...container.querySelectorAll("input, textarea, select, button")];
  expect(controls.some((control) => control.getAttribute("type") === "file")).toBe(true);
  for (const control of controls) {
    expect(accessibleName(control), control.outerHTML).not.toBe("");
  }
  expect(accessibleName(screen.getByLabelText("Upload a PDF"))).toBe("Upload a PDF");
  expect(screen.getByRole("button", { name: "Send" })).toBeTruthy();
});
