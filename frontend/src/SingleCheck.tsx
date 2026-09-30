import { type FormEvent, useEffect, useState } from "react";
import { fetchSampleImage, fetchSamples, verifyLabel } from "./api";
import ResultView from "./ResultView";
import type { Application, Sample, VerificationResult } from "./types";
import { APPLICATION_FIELDS, EMPTY_APPLICATION } from "./types";

export default function SingleCheck() {
  const [application, setApplication] = useState<Application>(EMPTY_APPLICATION);
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    // The examples are a convenience; the page works without them.
    fetchSamples().then(setSamples, () => setSamples([]));
  }, []);

  useEffect(() => {
    if (!image) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(image);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);

  function clearOutcome() {
    setResult(null);
    setError(null);
  }

  async function loadSample(filename: string) {
    const sample = samples.find((s) => s.filename === filename);
    if (!sample) return;
    clearOutcome();
    try {
      setImage(await fetchSampleImage(sample));
      setApplication(sample.application);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!image) {
      setError("Choose the label image first.");
      return;
    }
    clearOutcome();
    setChecking(true);
    try {
      setResult(await verifyLabel(image, application));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setChecking(false);
    }
  }

  function startOver() {
    setApplication(EMPTY_APPLICATION);
    setImage(null);
    clearOutcome();
  }

  return (
    <>
      {samples.length > 0 && (
        <div className="examples">
          <label htmlFor="example">New here? Try an example label:</label>
          <select id="example" value="" onChange={(e) => loadSample(e.target.value)}>
            <option value="" disabled>
              Choose an example…
            </option>
            {samples.map((sample) => (
              <option key={sample.filename} value={sample.filename}>
                {sample.application.brand_name} — {sample.description}
              </option>
            ))}
          </select>
        </div>
      )}

      <form onSubmit={submit} className="columns">
        <section className="card">
          <h2>
            <span className="step">1</span> Application details
          </h2>
          <p className="help">Type what the application says. Leave a box empty to skip it.</p>
          {APPLICATION_FIELDS.map(({ key, label, hint, required }) => (
            <div className="field" key={key}>
              <label htmlFor={key}>
                {label} {!required && <span className="optional">(optional)</span>}
              </label>
              <input
                id={key}
                type="text"
                value={application[key]}
                required={required}
                placeholder={hint}
                autoComplete="off"
                onChange={(e) => setApplication({ ...application, [key]: e.target.value })}
              />
            </div>
          ))}
        </section>

        <section className="card">
          <h2>
            <span className="step">2</span> Label image
          </h2>
          <p className="help">A photo or scan of the label, as a JPG or PNG.</p>
          <label className="file-picker">
            <input
              type="file"
              accept="image/*"
              onChange={(e) => {
                setImage(e.target.files?.[0] ?? null);
                clearOutcome();
                e.target.value = "";
              }}
            />
            <span className="button secondary">{image ? "Choose a different image" : "Choose label image"}</span>
          </label>
          {image && preview && (
            <figure className="preview">
              <img src={preview} alt="The label to be checked" />
              <figcaption>{image.name}</figcaption>
            </figure>
          )}
        </section>

        <div className="actions">
          <button type="submit" className="button primary" disabled={checking}>
            {checking ? "Checking…" : "Check this label"}
          </button>
          <button type="button" className="button secondary" onClick={startOver} disabled={checking}>
            Start over
          </button>
        </div>
      </form>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result && <ResultView result={result} />}
    </>
  );
}
