"use client";

import { useState } from "react";

export type RiskFlag = {
  id: string;
  category: "CAM_NNN" | "PERSONAL_GUARANTEE" | "RENT_ESCALATION" | "HVAC_REPAIRS" | "SUBLEASE_EXIT" | "AUTO_RENEWAL" | "OTHER";
  severity: "HIGH" | "MEDIUM" | "LOW";
  title: string;
  plain_english_explanation: string;
  page_number: number;
  section_reference: string;
  verbatim_quote: string;
  recommended_redline: string;
};

const tone = {
  HIGH: { badge: "bg-red-100 text-red-800", border: "border-l-red-500", label: "High risk" },
  MEDIUM: { badge: "bg-amber-100 text-amber-900", border: "border-l-amber-500", label: "Medium risk" },
  LOW: { badge: "bg-emerald-100 text-emerald-800", border: "border-l-emerald-500", label: "Low risk" },
};

export default function RiskFlagCard({ flag, onSelect, unlocked = true }: { flag: RiskFlag; onSelect: (page: number) => void; unlocked?: boolean }) {
  const [copied, setCopied] = useState(false);
  const styles = tone[flag.severity];

  async function copyRedline() {
    try {
      await navigator.clipboard.writeText(flag.recommended_redline);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <article className={`rounded-xl border border-slate-200 border-l-4 ${styles.border} bg-white p-4 shadow-sm`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{flag.category.replaceAll("_", " ")}</p>
          <h3 className="mt-1 font-semibold text-slate-950">{flag.title}</h3>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${styles.badge}`}>{styles.label}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{flag.plain_english_explanation}</p>
      <button type="button" onClick={() => onSelect(flag.page_number)} className="mt-3 text-left text-xs font-semibold text-blue-700 underline decoration-blue-300 underline-offset-4 hover:text-blue-900">
        View source · Page {flag.page_number}{flag.section_reference ? ` · ${flag.section_reference}` : ""}
      </button>
      <blockquote className={`mt-3 border-l-2 border-slate-300 bg-slate-50 px-3 py-2 text-sm italic leading-6 text-slate-700 ${!unlocked ? "select-none blur-sm" : ""}`}>“{flag.verbatim_quote}”</blockquote>
      <div className="mt-3 rounded-lg bg-blue-50 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-900">Suggested counter-clause</p>
        <p className={`mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800 ${!unlocked ? "select-none blur-sm" : ""}`}>{flag.recommended_redline}</p>
        <button type="button" disabled={!unlocked} onClick={copyRedline} className="mt-3 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xs font-semibold text-blue-800 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-50">
          {copied ? "Copied" : "Copy Counter-Clause Redline"}
        </button>
      </div>
    </article>
  );
}
