"use client";

import { ScraperRun } from "@/lib/api";

function formatDuration(seconds: number): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

const STATUS_STYLES: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-700 border-emerald-200",
  partial: "bg-amber-100 text-amber-700 border-amber-200",
  failed:  "bg-red-100 text-red-700 border-red-200",
};

export default function RunHistory({ runs }: { runs: ScraperRun[] }) {
  if (!runs.length) {
    return (
      <div className="bg-white rounded-2xl shadow-md border border-gray-100 p-8 text-center text-gray-400 font-semibold">
        No scraper runs recorded yet. Start a scrape to begin tracking history.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-md border border-gray-100 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest">
          Scraper Run History
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-xs font-black text-gray-500 uppercase tracking-wider">
              <th className="px-5 py-3 text-left">Date / Time</th>
              <th className="px-5 py-3 text-left">Keyword</th>
              <th className="px-5 py-3 text-center">Pages</th>
              <th className="px-5 py-3 text-center">Found</th>
              <th className="px-5 py-3 text-center">Saved</th>
              <th className="px-5 py-3 text-center">Duration</th>
              <th className="px-5 py-3 text-center">Errors</th>
              <th className="px-5 py-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {runs.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-5 py-3 text-gray-600 whitespace-nowrap">{formatDate(r.started_at)}</td>
                <td className="px-5 py-3 font-semibold text-gray-800 max-w-[180px] truncate">{r.keyword}</td>
                <td className="px-5 py-3 text-center tabular-nums text-gray-700">{r.pages_scraped}</td>
                <td className="px-5 py-3 text-center tabular-nums text-blue-700 font-bold">{r.jobs_found}</td>
                <td className="px-5 py-3 text-center tabular-nums text-emerald-700 font-bold">{r.jobs_saved}</td>
                <td className="px-5 py-3 text-center tabular-nums text-gray-600">{formatDuration(r.duration_seconds)}</td>
                <td className="px-5 py-3 text-center tabular-nums">
                  {r.error_count > 0
                    ? <span className="text-red-600 font-bold">{r.error_count}</span>
                    : <span className="text-gray-400">0</span>}
                </td>
                <td className="px-5 py-3 text-center">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${STATUS_STYLES[r.run_status] ?? "bg-gray-100 text-gray-600"}`}>
                    {r.run_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
