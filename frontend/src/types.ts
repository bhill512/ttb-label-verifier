export type Status = "match" | "review" | "mismatch" | "not_found";
export type Verdict = "pass" | "review" | "fail" | "unreadable";

export interface Application {
  brand_name: string;
  class_type: string;
  alcohol_content: string;
  net_contents: string;
  bottler: string;
  country_of_origin: string;
}

export interface FieldResult {
  key: string;
  title: string;
  status: Status;
  expected: string;
  found: string | null;
  note: string;
}

export interface VerificationResult {
  verdict: Verdict;
  summary: string;
  fields: FieldResult[];
  extracted_text: string[];
  ocr_confidence: number;
  elapsed_ms: number;
}

export interface Sample {
  filename: string;
  url: string;
  description: string;
  application: Application;
}

export const EMPTY_APPLICATION: Application = {
  brand_name: "",
  class_type: "",
  alcohol_content: "",
  net_contents: "",
  bottler: "",
  country_of_origin: "",
};

export const APPLICATION_FIELDS: {
  key: keyof Application;
  label: string;
  hint: string;
  required?: boolean;
}[] = [
  { key: "brand_name", label: "Brand name", hint: "Example: Old Tom Distillery", required: true },
  { key: "class_type", label: "Class / type", hint: "Example: Kentucky Straight Bourbon Whiskey" },
  { key: "alcohol_content", label: "Alcohol content", hint: "Example: 45% Alc./Vol. (90 Proof)" },
  { key: "net_contents", label: "Net contents", hint: "Example: 750 mL" },
  { key: "bottler", label: "Bottler / producer", hint: "Name and address" },
  { key: "country_of_origin", label: "Country of origin", hint: "Imports only" },
];

export const VERDICT_TEXT: Record<Verdict, string> = {
  pass: "Label matches the application",
  review: "Needs a closer look",
  fail: "Problems found",
  unreadable: "Could not read the label",
};

export const STATUS_TEXT: Record<Status, string> = {
  match: "Matches",
  review: "Check by eye",
  mismatch: "Does not match",
  not_found: "Not found",
};
