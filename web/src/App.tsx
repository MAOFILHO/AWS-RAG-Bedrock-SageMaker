import { FormEvent, useState } from "react";

export default function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");

  async function ask(event: FormEvent) {
    event.preventDefault();
    setAnswer("");
    setError("");
    try {
      const reply = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question }),
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
      <h1>Ask the rag-course PDF</h1>
      <form onSubmit={ask}>
        <input aria-label="Question" value={question} onChange={(e) => setQuestion(e.target.value)} />
      </form>
      {answer && <p>{answer}</p>}
      {error && <p role="alert">{error}</p>}
    </main>
  );
}
