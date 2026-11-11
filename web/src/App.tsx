import { FormEvent, useEffect, useState } from "react";

type Source = { id: string; name: string; description: string };

export default function App() {
  const [sources, setSources] = useState<Source[]>([]);
  const [source, setSource] = useState("pdf");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");

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
    setAnswer("");
    setError("");
    try {
      const reply = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question, source }),
      });
      const body = await reply.json();
      if (reply.ok) setAnswer(body.answer);
      else setError(body.error);
    } catch {
      setError("Could not reach the server. Try again.");
    }
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
      <form onSubmit={ask}>
        <input aria-label="Question" value={question} onChange={(e) => setQuestion(e.target.value)} />
      </form>
      {answer && <p>{answer}</p>}
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
