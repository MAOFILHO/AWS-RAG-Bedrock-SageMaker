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
