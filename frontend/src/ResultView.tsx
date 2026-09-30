import type { Status, Verdict, VerificationResult } from "./types";
import { STATUS_TEXT, VERDICT_TEXT } from "./types";

// Every status has a symbol and words as well as a color, so nothing relies on color alone.
const STATUS_SYMBOL: Record<Status, string> = {
  match: "✓",
  review: "!",
  mismatch: "✕",
  not_found: "✕",
};

const VERDICT_SYMBOL: Record<Verdict, string> = {
  pass: "✓",
  review: "!",
  fail: "✕",
  unreadable: "?",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span className={`badge verdict-${verdict}`}>
      <span aria-hidden="true">{VERDICT_SYMBOL[verdict]}</span> {VERDICT_TEXT[verdict]}
    </span>
  );
}

// Problems first, so nobody has to hunt through the matches to find them.
const STATUS_ORDER: Status[] = ["mismatch", "not_found", "review", "match"];

export default function ResultView({ result }: { result: VerificationResult }) {
  const fields = [...result.fields].sort(
    (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status),
  );

  return (
    <section className="result" aria-live="polite">
      <div className={`banner verdict-${result.verdict}`}>
        <span className="banner-symbol" aria-hidden="true">
          <span>{VERDICT_SYMBOL[result.verdict]}</span>
        </span>
        <div>
          <h2>{VERDICT_TEXT[result.verdict]}</h2>
          <p>
            {result.summary} Checked in {(result.elapsed_ms / 1000).toFixed(1)} seconds.
          </p>
        </div>
      </div>

      <ul className="checklist">
        {fields.map((field) => (
          <li key={field.key} className={`check status-${field.status}`}>
            <span className="check-status">
              <span aria-hidden="true">{STATUS_SYMBOL[field.status]}</span>{" "}
              {STATUS_TEXT[field.status]}
            </span>
            <div className="check-body">
              <h3>{field.title}</h3>
              <p>{field.note}</p>
              <dl>
                <dt>{field.key.startsWith("warning") ? "Required" : "Application says"}</dt>
                <dd>{field.expected}</dd>
                <dt>On the label</dt>
                <dd>{field.found ?? "—"}</dd>
              </dl>
            </div>
          </li>
        ))}
      </ul>

      <details className="raw-text">
        <summary>Show all text read from the label</summary>
        <pre>{result.extracted_text.join("\n") || "No text was read."}</pre>
      </details>
    </section>
  );
}
