import { DragEvent, FormEvent, useEffect, useState } from "react";

type Source = { id: string; name: string; description: string };
type ActivePdf = { name: string; uploaded: boolean };
type Turn = { question: string; source: string; answer: string };

export default function App() {
  const [sources, setSources] = useState<Source[]>([]);
  const [source, setSource] = useState("pdf");
  const [question, setQuestion] = useState("");
  const [thread, setThread] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activePdf, setActivePdf] = useState<ActivePdf | null>(null);
  const [pdfStatus, setPdfStatus] = useState("");

  useEffect(() => {
    fetch("/api/pdf")
      .then((reply) => (reply.ok ? reply.json() : Promise.reject()))
      .then((pdf: ActivePdf) => typeof pdf.name === "string" && setActivePdf(pdf))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch("/api/sources")
      .then((reply) => (reply.ok ? reply.json() : Promise.reject()))
      .then((list: Source[]) => {
        setSources(list);
        if (!list.some((item) => item.id === "pdf") && list[0]) setSource(list[0].id);
      })
      .catch(() => setError("Could not load the Sources. Try again."));
  }, []);

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const reply = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question, source }),
      });
      const body = await reply.json();
      if (reply.ok) {
        const name = sources.find((item) => item.id === source)?.name ?? source;
        setThread((turns) => [...turns, { question, source: name, answer: body.answer }]);
        setQuestion("");
      } else setError(body.error);
    } catch {
      setError("Could not reach the server. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function pdfCall(url: string, init: RequestInit, status: (pdf: ActivePdf) => string) {
    setError("");
    try {
      const reply = await fetch(url, init);
      const body = await reply.json();
      if (!reply.ok) {
        setPdfStatus("");
        return setError(body.error);
      }
      setActivePdf(body);
      setPdfStatus(status(body));
    } catch {
      setPdfStatus("");
      setError("Could not reach the server. Try again.");
    }
  }

  function upload(file?: File) {
    if (!file) return;
    setPdfStatus(`Uploading ${file.name}...`);
    return pdfCall(`/api/pdf?name=${encodeURIComponent(file.name)}`, { method: "PUT", body: file }, (pdf) => `${pdf.name} is ready`);
  }

  function drop(event: DragEvent) {
    event.preventDefault();
    upload(event.dataTransfer.files[0]);
  }

  return (
    <main>
      <h1>Ask a Source</h1>
      <fieldset>
        <legend>Source</legend>
        {sources.map((item) => (
          <label key={item.id}>
            <input type="radio" name="source" value={item.id} checked={source === item.id} onChange={() => setSource(item.id)} />
            {item.name}: {item.description}
          </label>
        ))}
      </fieldset>
      {source === "pdf" && (
        <section onDragOver={(event) => event.preventDefault()} onDrop={drop}>
          {activePdf && <p>Active PDF: {activePdf.name} ({activePdf.uploaded ? "uploaded" : "default"})</p>}
          <label>
            Upload a PDF
            <input type="file" accept="application/pdf" onChange={(event) => { upload(event.target.files?.[0]); event.target.value = ""; }} />
          </label>
          <span>or drop a PDF here</span>
          {activePdf?.uploaded && (
            <button type="button" onClick={() => pdfCall("/api/pdf", { method: "DELETE" }, () => "")}>Use the default PDF</button>
          )}
          {pdfStatus && <p role="status">{pdfStatus}</p>}
        </section>
      )}
      <ol>
        {thread.map((turn, index) => (
          <li key={index}>
            <p>{turn.question}</p>
            <small>{turn.source}</small>
            <p>{turn.answer}</p>
          </li>
        ))}
      </ol>
      {loading && <p role="status">Thinking...</p>}
      <form onSubmit={ask}>
        <input aria-label="Question" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button type="submit" disabled={loading}>Send</button>
        <button type="button" onClick={() => { setThread([]); setError(""); }}>Clear</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
