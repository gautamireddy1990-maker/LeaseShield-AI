"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const steps = [
  "Extracting text & tables...",
  "Scanning CAM & renewal clauses...",
  "Generating negotiation redlines...",
];
const MAX_AUDIT_MS = 180_000;

export default function Upload() {
  const input = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState("");

  function choose(candidate?: File) {
    if (!candidate) return;
    if (candidate.type !== "application/pdf" && !candidate.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF file.");
      return;
    }
    if (candidate.size > 25 * 1024 * 1024) {
      setError("PDF must be 25 MB or smaller.");
      return;
    }
    setError("");
    setFile(candidate);
  }

  async function submit() {
    if (!file || busy) return;
    setBusy(true);
    setStep(0);
    setElapsedSeconds(0);
    setError("");

    const startedAt = Date.now();
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), MAX_AUDIT_MS);
    const progressId = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
      setStep((current) => Math.min(current + 1, steps.length - 1));
    }, 10_000);

    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API}/api/audit`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = typeof body?.detail === "string" ? body.detail : `Audit failed (HTTP ${response.status}).`;
        throw new Error(detail);
      }
      if (!body?.report_id) throw new Error("The audit service returned no report ID. Please try again.");

      const pdfUrl = URL.createObjectURL(file);
      router.push(`/dashboard/${encodeURIComponent(body.report_id)}?pdfUrl=${encodeURIComponent(pdfUrl)}`);
    } catch (reason) {
      if (controller.signal.aborted) {
        setError("The audit took longer than 3 minutes and was stopped. Check that the backend and OpenAI API key are working, then try again.");
      } else if (reason instanceof TypeError) {
        setError(`Could not reach the audit API at ${API}. Confirm the backend is running and NEXT_PUBLIC_API_URL points to it.`);
      } else {
        setError(reason instanceof Error ? reason.message : "Audit failed. Please try again.");
      }
      setBusy(false);
    } finally {
      window.clearTimeout(timeoutId);
      window.clearInterval(progressId);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-5">
      <section className="w-full max-w-xl rounded-3xl border bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold text-blue-700">LeaseShield AI</p>
        <h1 className="mt-2 text-2xl font-bold">Upload your commercial lease</h1>
        <p className="mt-2 text-sm text-slate-600">PDF only · up to 25 MB · file is removed after analysis.</p>
        <button disabled={busy} onClick={() => input.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); choose(event.dataTransfer.files[0]); }} className="mt-6 w-full rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-10 text-center hover:border-blue-500">
          <span className="block font-semibold">{file ? file.name : "Drop your PDF here or browse"}</span>
          <span className="mt-2 block text-sm text-slate-500">Your lease stays private</span>
        </button>
        <input ref={input} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(event) => choose(event.target.files?.[0])} />
        {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        {busy && <div className="mt-5">
          <ol className="space-y-2">{steps.map((label, index) => <li key={label} className={`text-sm ${index <= step ? "font-semibold text-blue-800" : "text-slate-400"}`}>{index < step ? "✓" : index === step ? "◌" : "○"} {label}</li>)}</ol>
          {step === 2 && <p aria-live="polite" className="mt-3 text-xs leading-5 text-slate-500">Audit is still running ({elapsedSeconds}s). Larger leases can take a few minutes while clauses are checked against their page citations.</p>}
        </div>}
        <button disabled={!file || busy} onClick={submit} className="mt-6 w-full rounded-xl bg-blue-700 py-3 font-semibold text-white disabled:opacity-40">{busy ? "Auditing lease…" : "Start lease audit"}</button>
      </section>
    </main>
  );
}
