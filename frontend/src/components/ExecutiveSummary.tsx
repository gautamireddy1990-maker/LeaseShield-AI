type FinancialSummary = {
  base_monthly_rent: number;
  estimated_cam_nnn: number;
  total_estimated_monthly_outflow: number;
  security_deposit: number;
  annual_escalation_summary: string;
};

const money = (amount: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount);

export default function ExecutiveSummary({ summary }: { summary: FinancialSummary }) {
  return (
    <section aria-labelledby="financial-summary" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Financial snapshot</p>
          <h2 id="financial-summary" className="mt-1 text-lg font-semibold text-slate-950">Estimated monthly occupancy cost</h2>
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800">Lease figures and estimates</span>
      </div>
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Base rent</p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{money(summary.base_monthly_rent)}</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-sm text-slate-500">Estimated CAM / NNN</p>
          <p className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{money(summary.estimated_cam_nnn)}</p>
        </div>
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-800">Total monthly outflow</p>
          <p className="mt-1 text-xl font-bold tabular-nums text-blue-950">{money(summary.total_estimated_monthly_outflow)}</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap justify-between gap-3 border-t border-slate-100 pt-4 text-sm">
        <p className="text-slate-600"><span className="font-medium text-slate-800">Security deposit:</span> {money(summary.security_deposit)}</p>
        <p className="text-slate-600"><span className="font-medium text-slate-800">Escalations:</span> {summary.annual_escalation_summary}</p>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-500">CAM / NNN and total outflow are estimates based on extracted lease information. Confirm the figures and assumptions before relying on them.</p>
    </section>
  );
}
