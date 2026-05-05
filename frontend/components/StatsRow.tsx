"use client";

import { Job } from "@/lib/api";

interface Props {
  jobs: Job[];
}

export default function StatsRow({ jobs }: Props) {
  const remote    = jobs.filter((j) => /remote/i.test(j.location_type)).length;
  const hybrid    = jobs.filter((j) => /hybrid/i.test(j.location_type)).length;
  const contract  = jobs.filter((j) => /contract/i.test(j.employment_type)).length;
  const withSalary = jobs.filter((j) => j.salary && j.salary !== "N/A" && j.salary.trim() !== "").length;

  const stats = [
    { label: "Total Jobs",   value: jobs.length, color: "text-blue-600",    bg: "bg-blue-50" },
    { label: "Remote",       value: remote,      color: "text-green-600",   bg: "bg-green-50" },
    { label: "Hybrid",       value: hybrid,      color: "text-yellow-600",  bg: "bg-yellow-50" },
    { label: "Contract",     value: contract,    color: "text-orange-600",  bg: "bg-orange-50" },
    { label: "With Salary",  value: withSalary,  color: "text-emerald-600", bg: "bg-emerald-50" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-5">
      {stats.map((s) => (
        <div key={s.label} className={`${s.bg} rounded-xl p-5 text-center shadow-sm`}>
          <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
          <div className="text-xs text-gray-500 mt-1">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
