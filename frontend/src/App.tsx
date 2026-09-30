import { useState } from "react";
import BatchCheck from "./BatchCheck";
import SingleCheck from "./SingleCheck";

type Mode = "single" | "batch";

const MODES: { id: Mode; label: string }[] = [
  { id: "single", label: "Check one label" },
  { id: "batch", label: "Check many labels" },
];

export default function App() {
  const [mode, setMode] = useState<Mode>("single");

  return (
    <>
      <header className="site-header">
        <div className="page">
          <h1>Label Verification</h1>
          <p>Compares a label image with its application and checks the government warning.</p>
        </div>
      </header>

      <main className="page">
        <nav className="modes" aria-label="What would you like to do?">
          {MODES.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              className={mode === id ? "mode active" : "mode"}
              aria-current={mode === id ? "page" : undefined}
              onClick={() => setMode(id)}
            >
              {label}
            </button>
          ))}
        </nav>

        {/* Both stay mounted so switching tabs never loses work in progress. */}
        <div hidden={mode !== "single"}>
          <SingleCheck />
        </div>
        <div hidden={mode !== "batch"}>
          <BatchCheck />
        </div>
      </main>
    </>
  );
}
