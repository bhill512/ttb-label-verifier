import type { Application, Sample, VerificationResult } from "./types";

const UNREACHABLE = "Could not reach the checking service. Please try again.";

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Not JSON; fall through to the generic message.
  }
  return `Something went wrong (error ${response.status}). Please try again.`;
}

export async function verifyLabel(
  image: File,
  application: Application,
  signal?: AbortSignal,
): Promise<VerificationResult> {
  const form = new FormData();
  form.append("image", image);
  for (const [key, value] of Object.entries(application)) form.append(key, value);

  let response: Response;
  try {
    response = await fetch("/api/verify", { method: "POST", body: form, signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error(UNREACHABLE);
  }
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json();
}

export async function fetchSamples(): Promise<Sample[]> {
  const response = await fetch("/api/samples");
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json();
}

export async function fetchSampleImage(sample: Sample): Promise<File> {
  const response = await fetch(sample.url);
  if (!response.ok) throw new Error(await errorMessage(response));
  const blob = await response.blob();
  return new File([blob], sample.filename, { type: blob.type });
}
