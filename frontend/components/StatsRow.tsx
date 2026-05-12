"use client";

import { Job, StartupJob, IndeedJob, DiceJob, AdzunaJob, ScraperRun } from "@/lib/api";

interface Props {
  linkedinJobs:  Job[];
  startupJobs:   StartupJob[];
  indeedJobs:    IndeedJob[];
  diceJobs:      DiceJob[];
  adzunaJobs:    AdzunaJob[];
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

export default function StatsRow({ linkedinJobs, startupJobs, indeedJobs, diceJobs, adzunaJobs, runs = [] }: Props) {
  // Count runs whose started_at falls on today in the user's LOCAL timezone.
  // started_at is stored as a UTC ISO string ("2026-05-08T20:00:00Z").
  // new Date(utcStr).getFullYear/Month/Date() returns LOCAL time components,
  // so this correctly handles midnight roll-overs for any timezone offset.
  function localDateStr(d: Date): string {
    return (
      d.getFullYear() +
      "-" + String(d.getMonth() + 1).padStart(2, "0") +
      "-" + String(d.getDate()).padStart(2, "0")
    );
  }
  const todayLocal = localDateStr(new Date());
  const todayRunCount = runs.filter((r) => {
    if (!r.started_at) return false;
    return localDateStr(new Date(r.started_at)) === todayLocal;
  }).length;

  const stats = [
    { label: "LinkedIn Jobs",  value: linkedinJobs.length,  color: "text-blue-700",   bg: "bg-blue-50 border-blue-200" },
    { label: "Startup Jobs",   value: startupJobs.length,   color: "text-orange-700", bg: "bg-orange-50 border-orange-200" },
    { label: "Indeed Jobs",    value: indeedJobs.length,    color: "text-violet-700", bg: "bg-violet-50 border-violet-200" },
    { label: "Dice Jobs",      value: diceJobs.length,      color: "text-teal-700",   bg: "bg-teal-50 border-teal-200" },
    { label: "Adzuna Jobs",    value: adzunaJobs.length,    color: "text-amber-700",  bg: "bg-amber-50 border-amber-200" },
    { label: "Runs Today",     value: todayRunCount,        color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 xl:grid-cols-6 gap-4 mb-6">
      {stats.map((s) => (
        <div key={s.label} className={`${s.bg} border rounded-2xl p-5 text-center shadow-md`}>
          <div className={`text-3xl font-black ${s.color}`}>{s.value}</div>
          <div className="text-xs font-bold text-gray-600 mt-2 uppercase tracking-wide">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
