"use client";

import { useState } from "react";
import { Job } from "@/lib/api";
import JobDetailModal from "./JobDetailModal";

function locationBadge(loc: string) {
  const l = loc.toLowerCase();
  if (l.includes("remote")) return "bg-green-100 text-green-700";
  if (l.includes("hybrid")) return "bg-yellow-100 text-yellow-700";
  if (l.includes("on-site") || l.includes("onsite")) return "bg-blue-100 text-blue-700";
  return "bg-gray-100 text-gray-500";
}

function employBadge(emp: string) {
  const e = emp.toLowerCase();
  if (e.includes("full")) return "bg-purple-100 text-purple-700";
  if (e.includes("part")) return "bg-pink-100 text-pink-700";
  if (e.includes("contract")) return "bg-orange-100 text-orange-700";
  if (e.includes("intern")) return "bg-teal-100 text-teal-700";
  return "bg-gray-100 text-gray-500";
}

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function na(val: string) {
  return !val || val === "N/A";
}

interface Props {
  jobs: Job[];
}

export default function JobsTable({ jobs }: Props) {
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  if (!jobs.length) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-16 text-center text-gray-400 text-sm">
        No jobs found. Click <span className="font-semibold text-blue-600">Start Scraper</span> to begin.
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-blue-600 text-white text-left">
              {["#", "Job Title", "Company", "Location", "Employment", "Salary", "Skills", "Scraped At", ""].map(
                (h) => (
                  <th key={h} className="px-4 py-3 font-semibold whitespace-nowrap">
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {jobs.map((job, i) => {
              const skills = job.skills && !na(job.skills)
                ? job.skills.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 3)
                : [];

              return (
                <tr
                  key={job.id}
                  className="border-b border-gray-100 hover:bg-blue-50 transition-colors"
                >
                  <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>

                  <td className="px-4 py-3 font-semibold text-gray-800 max-w-[200px]">
                    <span className="line-clamp-2 leading-snug">{job.job_title}</span>
                  </td>

                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{job.company_name}</td>

                  <td className="px-4 py-3 whitespace-nowrap">
                    {na(job.location_type) ? (
                      <span className="text-gray-400 text-xs">—</span>
                    ) : (
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${locationBadge(job.location_type)}`}>
                        {job.location_type}
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 whitespace-nowrap">
                    {na(job.employment_type) ? (
                      <span className="text-gray-400 text-xs">—</span>
                    ) : (
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${employBadge(job.employment_type)}`}>
                        {job.employment_type}
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 whitespace-nowrap">
                    {na(job.salary) ? (
                      <span className="text-gray-400 text-xs">—</span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">
                        {job.salary}
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 max-w-[180px]">
                    {skills.length === 0 ? (
                      <span className="text-gray-400 text-xs">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {skills.map((s) => (
                          <span key={s} className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-xs rounded border border-blue-100 whitespace-nowrap">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>

                  <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                    {fmt(job.scraped_at)}
                  </td>

                  <td className="px-4 py-3 whitespace-nowrap">
                    <button
                      onClick={() => setSelectedJob(job)}
                      className="px-3 py-1.5 text-xs font-semibold text-blue-600 hover:text-white hover:bg-blue-600 border border-blue-200 hover:border-blue-600 rounded-lg transition-colors"
                    >
                      Details
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedJob && (
        <JobDetailModal job={selectedJob} onClose={() => setSelectedJob(null)} />
      )}
    </>
  );
}
