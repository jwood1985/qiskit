import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "../api/client";

export function GapsDashboard() {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getGaps()
      .then((res) => setMarkdown(res.markdown))
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <>
      <h1>Observability gaps</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        First-class deliverable per <code>CLAUDE.md</code>. Tracks every
        provider observability hook we wish existed, every workaround,
        and every cross-provider behavioural divergence we had to paper
        over.
      </p>
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      <article className="card markdown">
        {markdown === null ? (
          <p>Loading GAPS.md…</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        )}
      </article>
    </>
  );
}
