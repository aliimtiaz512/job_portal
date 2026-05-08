"use client";

import { Job, StartupJob, IndeedJob, DiceJob, ScraperRun } from "@/lib/api";

interface Props {
  linkedinJobs:  Job[];
  startupJobs:   StartupJob[];
  indeedJobs:    IndeedJob[];
  diceJobs:      DiceJob[];
  runs:          ScraperRun[];
}

function avgDuration(runs: ScraperRun[]): string {
  const completed = runs.filter((r) => r.duration_seconds > 0);
  if (!completed.length) return "—";
  const avg = Math.round(
    completed.reduce((s, r) => s + r.duration_seconds, 0) / completed.length
  );
  const m = Math.floor(avg / 60);
  const s = avg % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export default function StatsRow({ linkedinJobs, startupJobs, indeedJobs, diceJobs, runs = [] }: Props) {
  const stats = [
    { label: "LinkedIn Jobs",  value: linkedinJobs.length,  color: "text-blue-700",   bg: "bg-blue-50 border-blue-200" },
    { label: "Startup Jobs",   value: startupJobs.length,   color: "text-orange-700", bg: "bg-orange-50 border-orange-200" },
    { label: "Indeed Jobs",    value: indeedJobs.length,    color: "text-violet-700", bg: "bg-violet-50 border-violet-200" },
    { label: "Dice Jobs",      value: diceJobs.length,      color: "text-teal-700",   bg: "bg-teal-50 border-teal-200" },
    { label: "Total Runs",     value: runs.length,          color: "text-emerald-700",bg: "bg-emerald-50 border-emerald-200" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-5 gap-4 mb-6">
      {stats.map((s) => (
        <div key={s.label} className={`${s.bg} border rounded-2xl p-5 text-center shadow-md`}>
          <div className={`text-3xl font-black ${s.color}`}>{s.value}</div>
          <div className="text-xs font-bold text-gray-600 mt-2 uppercase tracking-wide">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
