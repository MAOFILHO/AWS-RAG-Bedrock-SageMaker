// @vitest-environment node
import http from "node:http";
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
  for (const body of [{ question: "   " }, {}, { question: 5 }]) {
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
