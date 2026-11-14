"use client";

import { useState } from "react";

export default function NegotiationModal({ email }: { email: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyEmail() {
    try {
      await navigator.clipboard.writeText(email);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-slate-700">Copy Landlord Email</button>
      {open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
        <section role="dialog" aria-modal="true" aria-labelledby="negotiation-title" className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl">
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-wider text-blue-700">Negotiation draft</p><h2 id="negotiation-title" className="mt-1 text-xl font-semibold text-slate-950">Email to landlord or broker</h2></div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="rounded-lg px-2 py-1 text-xl text-slate-500 hover:bg-slate-100">×</button>
          </div>
          <p className="mt-2 text-sm text-slate-600">Review the message and personalize names and details before sending.</p>
          <textarea readOnly value={email} className="mt-4 min-h-72 w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800 focus:outline-none" />
          <div className="mt-4 flex justify-end gap-2"><button type="button" onClick={() => setOpen(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">Close</button><button type="button" onClick={copyEmail} className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">{copied ? "Copied" : "Copy email"}</button></div>
        </section>
      </div>}
    </>
  );
}
