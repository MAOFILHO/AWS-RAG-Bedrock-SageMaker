import http from "node:http";

const send = (res, status, body) => {
  res.writeHead(status, { "content-type": "application/json" }).end(JSON.stringify(body));
};

const MAX_BODY = 64 * 1024;

class TooLong extends Error {}

const readJson = async (req) => {
  let text = "";
  for await (const chunk of req) {
    text += chunk;
    if (text.length > MAX_BODY) throw new TooLong();
  }
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
};

export function createApi(serviceUrl) {
  return http.createServer(async (req, res) => {
    try {
      await handle(req, res, serviceUrl);
    } catch (error) {
      // An aborted request or any other surprise ends this request, never the process.
      if (res.writableEnded || res.destroyed) return;
      if (error instanceof TooLong) return send(res, 413, { error: "That question is too long." });
      send(res, 500, { error: "Something went wrong. Try again." });
    }
  });
}

async function handle(req, res, serviceUrl) {
  if (req.method !== "POST" || req.url !== "/api/ask") return send(res, 404, { error: "Not found." });
  const { question } = (await readJson(req)) ?? {};
  if (typeof question !== "string" || !question.trim()) return send(res, 400, { error: "Type a question first." });
  try {
    const reply = await fetch(`${serviceUrl}/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!reply.ok) throw new Error(`service said ${reply.status}`);
    send(res, 200, { answer: (await reply.json()).answer });
  } catch {
    send(res, 502, { error: "The answer service is not available. Try again." });
  }
}
