import http from "node:http";
import express from "express";

export function createApi(serviceUrl) {
  const app = express();

  app.post("/api/ask", express.json({ limit: "64kb" }), async (req, res) => {
    const question = req.body?.question;
    if (typeof question !== "string" || !question.trim()) {
      return res.status(400).json({ error: "Type a question first." });
    }
    try {
      const reply = await fetch(`${serviceUrl}/ask`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question }),
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
