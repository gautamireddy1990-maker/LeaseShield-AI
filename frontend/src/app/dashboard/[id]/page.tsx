"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import ExecutiveSummary from "../../../components/ExecutiveSummary";
import NegotiationModal from "../../../components/NegotiationModal";
import RiskFlagCard, { type RiskFlag } from "../../../components/RiskFlagCard";
import PaywallBanner from "../../../components/PaywallBanner";

type Report = {
  report_id: string;
  file_name: string;
  overall_risk_score: number;
  financial_summary: {
    base_monthly_rent: number;
    estimated_cam_nnn: number;
    total_estimated_monthly_outflow: number;
    security_deposit: number;
    annual_escalation_summary: string;
  };
  critical_dates: { event_name: string; date_or_deadline: string; notice_period_days: number | null; action_required: string }[];
  risk_flags: RiskFlag[];
  landlord_negotiation_email: string;
  is_unlocked: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const severityFilters = ["ALL", "HIGH", "MEDIUM", "LOW"] as const;

export default function DashboardPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const reportId = params.id;
  const pdfUrl = searchParams.get("pdfUrl");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<(typeof severityFilters)[number]>("ALL");
  const [selectedPage, setSelectedPage] = useState(1);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/report/${encodeURIComponent(reportId)}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 404 ? "This report is unavailable. Reports are held only while the audit server is running." : "Could not load this audit report.");
        return response.json() as Promise<Report>;
      })
      .then(setReport)
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Could not load this report."); });
    return () => controller.abort();
  }, [reportId]);

  const filteredFlags = useMemo(() => report?.risk_flags.filter((flag) => filter === "ALL" || flag.severity === filter) ?? [], [filter, report]);
  const onSelectPage = useCallback((page: number) => setSelectedPage(page), []);

  if (error) return <main className="grid min-h-screen place-items-center bg-slate-50 p-6"><div className="max-w-lg rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm"><h1 className="text-xl font-semibold text-slate-950">Audit unavailable</h1><p className="mt-2 text-sm leading-6 text-slate-600">{error}</p></div></main>;
  if (!report) return <main className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-600">Loading your lease audit…</main>;

  const scoreColor = report.overall_risk_score >= 70 ? "bg-red-100 text-red-800" : report.overall_risk_score >= 40 ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-800";
  const pdfSrc = pdfUrl ? `${pdfUrl}#page=${selectedPage}&toolbar=0` : "";

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-4 px-5 py-4 lg:px-8">
          <div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-[0.15em] text-blue-700">LeaseShield AI · Lease audit</p><h1 className="mt-1 max-w-xl truncate text-lg font-semibold text-slate-950">{report.file_name}</h1></div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-3 py-2 text-sm font-semibold ${scoreColor}`}>Risk score · {report.overall_risk_score}/100</span>
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800">Zero-Retention · Auto-deletes in 24h</span>
            <a href={`${API_BASE}/api/report/${encodeURIComponent(reportId)}/calendar`} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Download .ICS Deadlines</a>
            {report.is_unlocked ? <><a href={`${API_BASE}/api/report/${encodeURIComponent(reportId)}/export-pdf`} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Export PDF Report</a><NegotiationModal email={report.landlord_negotiation_email} /></> : <button disabled className="cursor-not-allowed rounded-lg bg-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-600">Copy Landlord Email · Locked</button>}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-5 p-5 lg:grid-cols-[45fr_55fr] lg:items-start lg:px-8">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm lg:sticky lg:top-24">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3"><div><h2 className="font-semibold text-slate-900">Lease document</h2><p className="text-xs text-slate-500">Select a risk citation to jump to its page.</p></div>{selectedPage > 1 && <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">Page {selectedPage}</span>}</div>
          <div className="aspect-[3/4] min-h-[520px] bg-slate-100 lg:h-[calc(100vh-150px)] lg:aspect-auto">
            {pdfSrc ? <iframe key={selectedPage} title={`Lease PDF page ${selectedPage}`} src={pdfSrc} className="h-full w-full border-0" /> : <div className="grid h-full place-items-center p-8 text-center"><div className="max-w-sm"><div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-white text-slate-500 shadow-sm">PDF</div><p className="mt-4 font-semibold text-slate-800">PDF preview unavailable</p><p className="mt-2 text-sm leading-6 text-slate-600">The audit API does not retain uploaded PDFs. Pass a temporary browser PDF URL as the <code className="rounded bg-white px-1 py-0.5">pdfUrl</code> query parameter to enable the viewer during this session.</p></div></div>}
          </div>
        </section>

        <div className="space-y-5">
          <ExecutiveSummary summary={report.financial_summary} />
          {!report.is_unlocked && <PaywallBanner reportId={reportId} high={report.risk_flags.filter(f=>f.severity==="HIGH").length} medium={report.risk_flags.filter(f=>f.severity==="MEDIUM").length} />}
          <section aria-labelledby="risk-heading" className="space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Clause-by-clause findings</p><h2 id="risk-heading" className="mt-1 text-xl font-semibold text-slate-950">Risk flags <span className="text-base font-medium text-slate-500">({filteredFlags.length})</span></h2></div><label className="flex items-center gap-2 text-sm text-slate-600">Filter <select value={filter} onChange={(event) => setFilter(event.target.value as (typeof severityFilters)[number])} className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-800"><option value="ALL">All severity</option><option value="HIGH">High</option><option value="MEDIUM">Medium</option><option value="LOW">Low</option></select></label></div>
            {filteredFlags.length ? <div className="space-y-3">{filteredFlags.map((flag) => <RiskFlagCard key={flag.id} flag={flag} onSelect={onSelectPage} unlocked={report.is_unlocked} />)}</div> : <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-600">No findings in this severity filter.</div>}
          </section>
          {report.critical_dates.length > 0 && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-slate-950">Critical dates</h2><ul className="mt-3 divide-y divide-slate-100">{report.critical_dates.map((item, index) => <li key={`${item.event_name}-${index}`} className="py-3 first:pt-0 last:pb-0"><div className="flex flex-wrap justify-between gap-2"><p className="text-sm font-medium text-slate-800">{item.event_name}</p><p className="text-sm font-semibold text-slate-900">{item.date_or_deadline}</p></div><p className="mt-1 text-sm text-slate-600">{item.action_required}{item.notice_period_days ? ` · ${item.notice_period_days} days’ notice` : ""}</p></li>)}</ul></section>}
        </div>
      </div>
    </main>
  );
}
