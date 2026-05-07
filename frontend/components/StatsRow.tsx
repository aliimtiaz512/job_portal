"use client";

import { Job, ScraperRun } from "@/lib/api";

interface Props {
  jobs: Job[];
  dailyRuns: number;
  runs: ScraperRun[];
}

function avgDuration(runs: ScraperRun[]): string {
  const completed = runs.filter((r) => r.duration_seconds > 0);
  if (!completed.length) return "—";
  const avg = Math.round(completed.reduce((s, r) => s + r.duration_seconds, 0) / completed.length);
  const m = Math.floor(avg / 60);
  const s = avg % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function StatsRow({ jobs, dailyRuns = 0, runs = [] }: Props) {
  const stats = [
    {
      label: "Total Jobs in DB",
      value: jobs.length,
      color: "text-blue-700",
      bg: "bg-blue-50 border-blue-200",
    },
    {
      label: "Scraper Runs Today",
      value: dailyRuns ?? 0,
      color: "text-violet-700",
      bg: "bg-violet-50 border-violet-200",
    },
    {
      label: "Total Runs All Time",
      value: runs.length,
      color: "text-emerald-700",
      bg: "bg-emerald-50 border-emerald-200",
    },
    {
      label: "Avg Run Duration",
      value: avgDuration(runs),
      color: "text-amber-700",
      bg: "bg-amber-50 border-amber-200",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      {stats.map((s) => (
        <div key={s.label} className={`${s.bg} border rounded-2xl p-5 text-center shadow-md`}>
          <div className={`text-3xl font-black ${s.color}`}>{s.value}</div>
          <div className="text-xs font-bold text-gray-600 mt-2 uppercase tracking-wide">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
