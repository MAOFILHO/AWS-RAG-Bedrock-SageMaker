// @vitest-environment node
import http from "node:http";
import net from "node:net";
import { afterEach, expect, test } from "vitest";
import { createApi } from "./api.js";

const open = [];
const listen = async (server) => {
  open.push(server);
  await new Promise((done) => server.listen(0, done));
  return `http://127.0.0.1:${server.address().port}`;
};
afterEach(() => Promise.all(open.splice(0).map((s) => new Promise((done) => s.close(done)))));

const post = (url, body) =>
  fetch(`${url}/api/ask`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

const fakeService = (handler) => listen(http.createServer(handler));

test("returns the answer the Python service gives", async () => {
  const asked = [];
  const service = await fakeService((req, res) => {
    req.on("data", (chunk) => asked.push(JSON.parse(chunk)));
    req.on("end", () => res.end(JSON.stringify({ answer: "SDKs wrap APIs." })));
  });
  const api = await listen(createApi(service));
  const reply = await post(api, { question: "What are SDKs?" });
  expect(reply.status).toBe(200);
  expect(await reply.json()).toEqual({ answer: "SDKs wrap APIs." });
  expect(asked).toEqual([{ question: "What are SDKs?" }]);
});

test("returns one plain error for an empty question and does not call the service", async () => {
  let called = false;
  const service = await fakeService(() => (called = true));
  const api = await listen(createApi(service));
  for (const body of [{ question: "   " }, {}, { question: 5 }, null]) {
    const reply = await post(api, body);
    expect(reply.status).toBe(400);
    expect(await reply.json()).toEqual({ error: "Type a question first." });
  }
  expect(called).toBe(false);
});

test("returns one plain error when the Python service is down or fails", async () => {
  const down = await listen(createApi("http://127.0.0.1:1"));
  const failing = await fakeService((req, res) => res.writeHead(500).end("boom"));
  const broken = await listen(createApi(failing));
  for (const api of [down, broken]) {
    const reply = await post(api, { question: "Hi?" });
    expect(reply.status).toBe(502);
    expect(await reply.json()).toEqual({ error: "The answer service is not available. Try again." });
  }
});

const raw = (url, text) =>
  fetch(`${url}/api/ask`, { method: "POST", headers: { "content-type": "application/json" }, body: text });

test("array, string, number and unparsable bodies get the plain 400", async () => {
  const api = await listen(createApi("http://127.0.0.1:1"));
  for (const text of ["[]", '["hi"]', '"hi"', "7", "not json", ""]) {
    const reply = await raw(api, text);
    expect(reply.status).toBe(400);
    expect(await reply.json()).toEqual({ error: "Type a question first." });
  }
});

test("an oversized body gets one plain error", async () => {
  const api = await listen(createApi("http://127.0.0.1:1"));
  const reply = await post(api, { question: "x".repeat(200_000) });
  expect(reply.status).toBe(413);
  expect(await reply.json()).toEqual({ error: "That question is too long." });
});

test("a client that disconnects mid-request does not stop the API", async () => {
  const api = await listen(createApi("http://127.0.0.1:1"));
  const { port } = new URL(api);
  await new Promise((done) => {
    const socket = net.connect(Number(port), "127.0.0.1", () => {
      socket.write("POST /api/ask HTTP/1.1\r\nhost: x\r\ncontent-type: application/json\r\ncontent-length: 500\r\n\r\n{\"question\":");
      setTimeout(() => socket.destroy(), 20);
    });
    socket.on("close", done);
    socket.on("error", () => {});
  });
  await new Promise((done) => setTimeout(done, 100));
  const reply = await post(api, { question: "Still up?" });
  expect(reply.status).toBe(502);
});

test("after a 413 the next request on the same connection is still answered", async () => {
  const service = await fakeService((req, res) => res.end(JSON.stringify({ answer: "ok" })));
  const api = await listen(createApi(service));
  const agent = new http.Agent({ keepAlive: true, maxSockets: 1 });
  const send = (body) =>
    new Promise((resolve, reject) => {
      const req = http.request(`${api}/api/ask`, { method: "POST", agent, timeout: 3000, headers: { "content-type": "application/json" } }, (res) => {
        res.resume();
        res.on("end", () => resolve(res.statusCode));
      });
      req.on("timeout", () => reject(new Error("request hung")));
      req.on("error", reject);
      req.end(body);
    });
  try {
    expect(await send(JSON.stringify({ question: "x".repeat(200_000) }))).toBe(413);
    expect(await send(JSON.stringify({ question: "Hi?" }))).toBe(200);
    expect(await send("null")).toBe(400);
  } finally {
    agent.destroy();
  }
});

test("a question split across chunks inside a multi-byte character arrives intact", async () => {
  const asked = [];
  const service = await fakeService((req, res) => {
    let text = "";
    req.on("data", (chunk) => (text += chunk));
    req.on("end", () => {
      asked.push(JSON.parse(text).question);
      res.end(JSON.stringify({ answer: "ok" }));
    });
  });
  const api = await listen(createApi(service));
  const { port } = new URL(api);
  const body = Buffer.from(JSON.stringify({ question: "Qué é um SDK? 日本語" }));
  const cut = body.indexOf(Buffer.from("é")) + 1; // inside the two bytes of "é"
  const status = await new Promise((done) => {
    const socket = net.connect(Number(port), "127.0.0.1", () => {
      socket.write(`POST /api/ask HTTP/1.1\r\nhost: x\r\ncontent-type: application/json\r\nconnection: close\r\ncontent-length: ${body.length}\r\n\r\n`);
      socket.write(body.subarray(0, cut));
      setTimeout(() => socket.write(body.subarray(cut)), 30);
    });
    let reply = "";
    socket.on("data", (chunk) => (reply += chunk));
    socket.on("close", () => done(reply.split(" ")[1]));
  });
  expect(status).toBe("200");
  expect(asked).toEqual(["Qué é um SDK? 日本語"]);
});

test("passes the list of Sources through", async () => {
  const sources = [{ id: "web", name: "Web", description: "Two pages." }];
  const service = await fakeService((req, res) => res.end(req.url === "/sources" ? JSON.stringify(sources) : "{}"));
  const api = await listen(createApi(service));
  const reply = await fetch(`${api}/api/sources`);
  expect(reply.status).toBe(200);
  expect(await reply.json()).toEqual(sources);
});

test("returns one plain error for the Sources when the Python service is down", async () => {
  const api = await listen(createApi("http://127.0.0.1:1"));
  const reply = await fetch(`${api}/api/sources`);
  expect(reply.status).toBe(502);
  expect(await reply.json()).toEqual({ error: "The answer service is not available. Try again." });
});

test("passes the chosen Source to the service and rejects a Source that is not text", async () => {
  const asked = [];
  const service = await fakeService((req, res) => {
    req.on("data", (chunk) => asked.push(JSON.parse(chunk)));
    req.on("end", () => res.end(JSON.stringify({ answer: "ok" })));
  });
  const api = await listen(createApi(service));
  expect((await post(api, { question: "Hi?", source: "sql" })).status).toBe(200);
  expect(asked).toEqual([{ question: "Hi?", source: "sql" }]);
  const bad = await post(api, { question: "Hi?", source: 5 });
  expect(bad.status).toBe(400);
  expect(await bad.json()).toEqual({ error: "Pick a Source first." });
});
