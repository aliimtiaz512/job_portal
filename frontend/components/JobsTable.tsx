"use client";

import { Job } from "@/lib/api";

interface Props {
  jobs: Job[];
}

export default function JobsTable({ jobs }: Props) {
  if (!jobs.length) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-16 text-center text-gray-400 text-base font-semibold">
        No jobs found. Click <span className="font-bold text-blue-600">Start Scraper</span> to begin.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-base">
          <thead>
            <tr className="bg-gradient-to-r from-blue-700 to-blue-600 text-white text-left">
              {["#", "Job Title", "Company", "Job URL"].map(
                (h) => (
                  <th key={h} className="px-5 py-4 font-bold text-sm uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {jobs.map((job, i) => (
              <tr
                key={job.id}
                className="border-b border-gray-100 hover:bg-blue-50/60 transition-colors"
              >
                <td className="px-5 py-4 text-gray-400 text-sm font-semibold">{i + 1}</td>

                <td className="px-5 py-4 font-bold text-gray-900 max-w-[250px]">
                  <span className="leading-snug text-base">{job.job_title}</span>
                </td>

                <td className="px-5 py-4 text-gray-700 font-semibold whitespace-nowrap text-base">{job.company_name}</td>

                <td className="px-5 py-4 max-w-[350px]">
                  <a
                    href={job.job_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 hover:underline font-semibold text-sm break-all leading-relaxed"
                  >
                    {job.job_url}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
