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

  const unavailable = (res) => res.status(502).json({ error: "The answer service is not available. Try again." });

  // The PDF Source answers from the active PDF: the default one, or the last one uploaded.
  const pdf = async (res, method, query = "", body) => {
    try {
      const reply = await fetch(`${serviceUrl}/pdf${query}`, { method, body, headers: body ? { "content-type": "application/pdf" } : {} });
      if (reply.status === 400) return res.status(400).json(await reply.json());
      if (!reply.ok) throw new Error(`service said ${reply.status}`);
      res.json(await reply.json());
    } catch {
      unavailable(res);
    }
  };
  app.get("/api/pdf", (req, res) => pdf(res, "GET"));
  app.delete("/api/pdf", (req, res) => pdf(res, "DELETE"));
  app.put("/api/pdf", express.raw({ type: () => true, limit: "10mb" }), (req, res) => {
    const name = req.query.name;
    if (typeof name !== "string" || !name.trim() || !Buffer.isBuffer(req.body) || !req.body.length) {
      return res.status(400).json({ error: "Pick a PDF file first." });
    }
    if (req.body.subarray(0, 5).toString("latin1") !== "%PDF-") {
      return res.status(400).json({ error: "That file is not a PDF." });
    }
    pdf(res, "PUT", `?name=${encodeURIComponent(name)}`, req.body);
  });

  app.use((req, res) => res.status(404).json({ error: "Not found." }));

  // The body parser reports a too-large or unparsable body here; nothing else may end the process.
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    if (error.type === "entity.too.large") {
      return res.status(413).json({ error: req.path === "/api/pdf" ? "That PDF is over the 10 MB limit." : "That question is too long." });
    }
    if (error.status === 400 || error.type === "entity.parse.failed") {
      return res.status(400).json({ error: "Type a question first." });
    }
    res.status(500).json({ error: "Something went wrong. Try again." });
  });

  return http.createServer(app);
}
