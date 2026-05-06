"use client";

import { useEffect } from "react";
import { Job } from "@/lib/api";

function locationBadge(loc: string) {
  const l = loc.toLowerCase();
  if (l.includes("remote")) return "bg-green-100 text-green-700 border-green-200";
  if (l.includes("hybrid")) return "bg-yellow-100 text-yellow-700 border-yellow-200";
  if (l.includes("on-site") || l.includes("onsite")) return "bg-blue-100 text-blue-700 border-blue-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

function employBadge(emp: string) {
  const e = emp.toLowerCase();
  if (e.includes("full")) return "bg-purple-100 text-purple-700 border-purple-200";
  if (e.includes("part")) return "bg-pink-100 text-pink-700 border-pink-200";
  if (e.includes("contract")) return "bg-orange-100 text-orange-700 border-orange-200";
  if (e.includes("intern")) return "bg-teal-100 text-teal-700 border-teal-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

interface Props {
  job: Job;
  onClose: () => void;
}

export default function JobDetailModal({ job, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const skills = job.skills && job.skills !== "N/A"
    ? job.skills.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  const lines = (job.about_job || "")
    .replace(/^About the job\s*/i, "")
    .split("\n")
    .map((l) => l.trim());

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-start justify-between p-6 border-b border-gray-100">
          <div className="flex-1 min-w-0 pr-4">
            <h2 className="text-xl font-bold text-gray-900 leading-snug">{job.job_title}</h2>
            <p className="text-sm text-gray-500 mt-1 font-medium">{job.company_name}</p>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 transition-colors text-lg leading-none"
          >
            ×
          </button>
        </div>

        <div className="flex flex-wrap gap-2 px-6 py-4 border-b border-gray-100">
          {job.location_type && job.location_type !== "N/A" && (
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${locationBadge(job.location_type)}`}>
              {job.location_type}
            </span>
          )}
          {job.employment_type && job.employment_type !== "N/A" && (
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${employBadge(job.employment_type)}`}>
              {job.employment_type}
            </span>
          )}
        </div>

        {skills.length > 0 && (
          <div className="px-6 py-3 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Skills</p>
            <div className="flex flex-wrap gap-1.5">
              {skills.map((s) => (
                <span key={s} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-md border border-blue-100">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-6 py-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">About the Job</p>
          <div className="text-sm text-gray-700 space-y-1 leading-relaxed">
            {lines.map((line, i) =>
              line ? (
                <p key={i}>{line}</p>
              ) : (
                <div key={i} className="h-2" />
              )
            )}
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-2xl">
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            Apply on LinkedIn ↗
          </a>
        </div>
      </div>
    </div>
  );
}
