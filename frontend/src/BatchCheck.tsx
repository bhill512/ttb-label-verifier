import Papa from "papaparse";
import { useRef, useState } from "react";
import { verifyLabel } from "./api";
import ResultView, { VerdictBadge } from "./ResultView";
import type { Application, VerificationResult } from "./types";
import { EMPTY_APPLICATION, VERDICT_TEXT } from "./types";

// The server reads one label at a time; two requests keep it busy without a queue building up.
const CONCURRENT_CHECKS = 2;

interface Row {
  filename: string;
  application: Application;
}

type Outcome =
  | { state: "waiting" }
  | { state: "checking" }
  | { state: "done"; result: VerificationResult }
  | { state: "error"; message: string };

type Filter = "all" | "fail" | "review" | "pass";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "fail", label: "Problems" },
  { id: "review", label: "Needs a closer look" },
  { id: "pass", label: "Matches" },
];

function bucket(outcome: Outcome | undefined): Filter | null {
  if (!outcome || outcome.state === "waiting" || outcome.state === "checking") return null;
  if (outcome.state === "error") return "fail";
  const { verdict } = outcome.result;
  return verdict === "unreadable" ? "fail" : verdict;
}

function parseApplications(text: string): Row[] {
  const parsed = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header) => header.trim().toLowerCase(),
  });
  const columns = parsed.meta.fields ?? [];
  if (!columns.includes("filename") || !columns.includes("brand_name")) {
    throw new Error(
      'The spreadsheet needs a "filename" column and a "brand_name" column. Download the example to see the layout.',
    );
  }
  const keys = Object.keys(EMPTY_APPLICATION) as (keyof Application)[];
  return parsed.data
    .filter((record) => record.filename?.trim())
    .map((record) => ({
      filename: record.filename.trim(),
      application: Object.fromEntries(
        keys.map((key) => [key, record[key]?.trim() ?? ""]),
      ) as unknown as Application,
    }));
}

export default function BatchCheck() {
  const [rows, setRows] = useState<Row[]>([]);
  const [images, setImages] = useState<Map<string, File>>(new Map());
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  const imageFor = (row: Row) => images.get(row.filename.toLowerCase());
  const missing = rows.filter((row) => !imageFor(row)).length;
  const finished = rows.filter((row) => bucket(outcomes[row.filename])).length;
  const started = Object.keys(outcomes).length > 0;
  const counts = Object.fromEntries(
    FILTERS.map(({ id }) => [
      id,
      id === "all" ? finished : rows.filter((row) => bucket(outcomes[row.filename]) === id).length,
    ]),
  );

  async function chooseSpreadsheet(file: File | undefined) {
    if (!file) return;
    setError(null);
    setOutcomes({});
    try {
      const parsed = parseApplications(await file.text());
      if (parsed.length === 0) throw new Error("The spreadsheet has no applications in it.");
      setRows(parsed);
    } catch (e) {
      setRows([]);
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function chooseImages(files: FileList | null) {
    setOutcomes({});
    setImages(new Map(Array.from(files ?? []).map((file) => [file.name.toLowerCase(), file])));
  }

  async function run() {
    const controller = new AbortController();
    abort.current = controller;
    setRunning(true);
    setFilter("all");
    setOpen(null);

    const initial: Record<string, Outcome> = {};
    for (const row of rows) {
      initial[row.filename] = imageFor(row)
        ? { state: "waiting" }
        : { state: "error", message: "No image was chosen with this file name." };
    }
    setOutcomes(initial);
    const record = (filename: string, outcome: Outcome) =>
      setOutcomes((current) => ({ ...current, [filename]: outcome }));

    const queue = rows.filter(imageFor);
    async function worker() {
      for (let row = queue.shift(); row && !controller.signal.aborted; row = queue.shift()) {
        record(row.filename, { state: "checking" });
        try {
          const result = await verifyLabel(imageFor(row)!, row.application, controller.signal);
          record(row.filename, { state: "done", result });
        } catch (e) {
          if (controller.signal.aborted) {
            record(row.filename, { state: "waiting" });
          } else {
            record(row.filename, {
              state: "error",
              message: e instanceof Error ? e.message : String(e),
            });
          }
        }
      }
    }
    await Promise.all(Array.from({ length: CONCURRENT_CHECKS }, worker));
    setRunning(false);
  }

  function downloadResults() {
    const lines = rows.map((row) => {
      const outcome = outcomes[row.filename];
      const result = outcome?.state === "done" ? outcome.result : null;
      return {
        filename: row.filename,
        brand_name: row.application.brand_name,
        result: result
          ? VERDICT_TEXT[result.verdict]
          : outcome?.state === "error"
            ? "Not checked"
            : "",
        summary: result?.summary ?? (outcome?.state === "error" ? outcome.message : ""),
        details: (result?.fields ?? [])
          .filter((field) => field.status !== "match")
          .map((field) => `${field.title}: ${field.note}`)
          .join(" | "),
      };
    });
    const url = URL.createObjectURL(new Blob([Papa.unparse(lines)], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "label-check-results.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const visible = rows.filter(
    (row) => filter === "all" || bucket(outcomes[row.filename]) === filter,
  );

  return (
    <>
      <div className="columns">
        <section className="card">
          <h2>
            <span className="step">1</span> Application spreadsheet
          </h2>
          <p className="help">
            A CSV file with one row per application. It needs a <code>filename</code> column that
            names each label image. <a href="/samples/applications.csv">Download an example</a>.
          </p>
          <label className="file-picker">
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={running}
              onChange={(e) => chooseSpreadsheet(e.target.files?.[0])}
            />
            <span className="button secondary">Choose spreadsheet</span>
          </label>
          {rows.length > 0 && <p className="picked">{rows.length} applications loaded.</p>}
        </section>

        <section className="card">
          <h2>
            <span className="step">2</span> Label images
          </h2>
          <p className="help">Select all the label images at once. Names must match the spreadsheet.</p>
          <label className="file-picker">
            <input
              type="file"
              accept="image/*"
              multiple
              disabled={running}
              onChange={(e) => chooseImages(e.target.files)}
            />
            <span className="button secondary">Choose label images</span>
          </label>
          {images.size > 0 && <p className="picked">{images.size} images chosen.</p>}
          {rows.length > 0 && images.size > 0 && missing > 0 && (
            <p className="picked warn">
              {missing} of the {rows.length} applications {missing === 1 ? "has" : "have"} no image
              with a matching name.
            </p>
          )}
        </section>

        <div className="actions">
          {running ? (
            <button type="button" className="button secondary" onClick={() => abort.current?.abort()}>
              Stop
            </button>
          ) : (
            <button
              type="button"
              className="button primary"
              disabled={rows.length === 0 || images.size === 0}
              onClick={run}
            >
              Check all labels
            </button>
          )}
          {started && !running && (
            <button type="button" className="button secondary" onClick={downloadResults}>
              Download results
            </button>
          )}
        </div>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {started && (
        <section className="result">
          <div className="progress" role="status">
            <progress value={finished} max={rows.length} />
            <span>
              {finished} of {rows.length} checked
            </span>
          </div>

          <div className="filters" role="group" aria-label="Show">
            {FILTERS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                className={filter === id ? "filter active" : "filter"}
                aria-pressed={filter === id}
                onClick={() => setFilter(id)}
              >
                {label} ({counts[id]})
              </button>
            ))}
          </div>

          <ul className="batch-list">
            {visible.map((row) => {
              const outcome = outcomes[row.filename];
              const isOpen = open === row.filename;
              return (
                <li key={row.filename} className="batch-row">
                  <div className="batch-summary">
                    <div>
                      <strong>{row.application.brand_name}</strong>
                      <span className="filename">{row.filename}</span>
                    </div>
                    <div className="batch-outcome">
                      {outcome?.state === "done" && (
                        <>
                          <VerdictBadge verdict={outcome.result.verdict} />
                          <span>{outcome.result.summary}</span>
                        </>
                      )}
                      {outcome?.state === "error" && (
                        <>
                          <span className="badge verdict-unreadable">Not checked</span>
                          <span>{outcome.message}</span>
                        </>
                      )}
                      {outcome?.state === "checking" && <span className="muted">Checking…</span>}
                      {outcome?.state === "waiting" && <span className="muted">Waiting</span>}
                    </div>
                    {outcome?.state === "done" && (
                      <button
                        type="button"
                        className="button small"
                        aria-expanded={isOpen}
                        onClick={() => setOpen(isOpen ? null : row.filename)}
                      >
                        {isOpen ? "Hide details" : "Show details"}
                      </button>
                    )}
                  </div>
                  {isOpen && outcome?.state === "done" && <ResultView result={outcome.result} />}
                </li>
              );
            })}
            {visible.length === 0 && <li className="muted">Nothing to show here yet.</li>}
          </ul>
        </section>
      )}
    </>
  );
}
