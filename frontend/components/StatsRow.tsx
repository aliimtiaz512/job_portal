"use client";

import { Job } from "@/lib/api";

interface Props {
  jobs: Job[];
  dailyRuns: number;
}

export default function StatsRow({ jobs, dailyRuns = 0 }: Props) {
  const stats = [
    { label: "Total Jobs", value: jobs.length, color: "text-blue-700", bg: "bg-blue-50 border-blue-200" },
    { label: "Scraper Runs Today", value: dailyRuns, color: "text-violet-700", bg: "bg-violet-50 border-violet-200" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-2 gap-5 mb-6">
      {stats.map((s) => (
        <div key={s.label} className={`${s.bg} border rounded-2xl p-6 text-center shadow-md`}>
          <div className={`text-4xl font-black ${s.color}`}>{s.value}</div>
          <div className="text-sm font-bold text-gray-600 mt-2 uppercase tracking-wide">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
