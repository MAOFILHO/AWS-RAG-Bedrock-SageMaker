import http from "node:http";
import express from "express";

export function createApi(serviceUrl) {
  const app = express();

  app.get("/api/sources", async (req, res) => {
    try {
      const reply = await fetch(`${serviceUrl}/sources`);
      if (!reply.ok) throw new Error(`service said ${reply.status}`);
      res.json(await reply.json());
    } catch {
      res.status(502).json({ error: "The answer service is not available. Try again." });
    }
  });

  app.post("/api/ask", express.json({ limit: "64kb" }), async (req, res) => {
    const question = req.body?.question;
    if (typeof question !== "string" || !question.trim()) {
      return res.status(400).json({ error: "Type a question first." });
    }
    const source = req.body.source;
    if (source !== undefined && typeof source !== "string") {
      return res.status(400).json({ error: "Pick a Source first." });
    }
    try {
      const reply = await fetch(`${serviceUrl}/ask`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question, source }),
      });
      if (!reply.ok) throw new Error(`service said ${reply.status}`);
      res.json({ answer: (await reply.json()).answer });
    } catch {
      res.status(502).json({ error: "The answer service is not available. Try again." });
    }
  });

  app.use((req, res) => res.status(404).json({ error: "Not found." }));

  // The body parser reports a too-large or unparsable body here; nothing else may end the process.
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    if (error.type === "entity.too.large") return res.status(413).json({ error: "That question is too long." });
    if (error.status === 400 || error.type === "entity.parse.failed") {
      return res.status(400).json({ error: "Type a question first." });
    }
    res.status(500).json({ error: "Something went wrong. Try again." });
  });

  return http.createServer(app);
}
