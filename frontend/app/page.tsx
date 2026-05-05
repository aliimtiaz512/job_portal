"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  clearJobs,
  exportCsvUrl,
  getJobs,
  getStatus,
  Job,
  ScraperStatus,
  startScraper,
} from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import StatsRow from "@/components/StatsRow";
import JobsTable from "@/components/JobsTable";

const DEFAULT_STATUS: ScraperStatus = {
  running: false,
  progress: "",
  total: 0,
  scraped: 0,
  errors: [],
  done: false,
};

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filtered, setFiltered] = useState<Job[]>([]);
  const [status, setStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [showStatus, setShowStatus] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "" } | null>(null);
  const [search, setSearch] = useState("");
  const [locFilter, setLocFilter] = useState("");
  const [empFilter, setEmpFilter] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showToast = (msg: string, type: "success" | "error" | "" = "") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadJobs = useCallback(async () => {
    try {
      const data = await getJobs();
      setJobs(data);
    } catch {
      showToast("Failed to load jobs — is the backend running?", "error");
    }
  }, []);

  const applyFilters = useCallback(
    (allJobs: Job[], q: string, loc: string, emp: string) => {
      setFiltered(
        allJobs.filter((j) => {
          const text = `${j.job_title} ${j.company_name} ${j.about_job}`.toLowerCase();
          return (
            (!q || text.includes(q.toLowerCase())) &&
            (!loc || j.location_type.toLowerCase().includes(loc)) &&
            (!emp || j.employment_type.toLowerCase().includes(emp))
          );
        })
      );
    },
    []
  );

  useEffect(() => {
    applyFilters(jobs, search, locFilter, empFilter);
  }, [jobs, search, locFilter, empFilter, applyFilters]);

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s = await getStatus();
        setStatus(s);
        if (s.done) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          loadJobs();
        }
      } catch {}
    }, 2000);
  }, [loadJobs]);

  useEffect(() => {
    loadJobs();
    getStatus()
      .then((s) => {
        if (s.running) {
          setStatus(s);
          setShowStatus(true);
          startPolling();
        }
      })
      .catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadJobs, startPolling]);

  const handleStartScraper = async () => {
    try {
      const res = await startScraper();
      if (res.detail) { showToast(res.detail, "error"); return; }
      showToast("Scraper started!", "success");
      setShowStatus(true);
      setStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleExportCSV = () => {
    window.open(exportCsvUrl(), "_blank");
  };

  const handleClearJobs = async () => {
    if (!confirm("Delete all scraped jobs from the database?")) return;
    try {
      await clearJobs();
      showToast("All jobs cleared.", "success");
      setJobs([]);
    } catch {
      showToast("Failed to clear jobs.", "error");
    }
  };

  const isRunning = status.running;

  return (
    <main className="max-w-screen-xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <svg width="38" height="38" viewBox="0 0 24 24" fill="#0a66c2">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
          <h1 className="text-3xl font-bold text-blue-600">LinkedIn Job Scraper</h1>
        </div>
        <p className="text-gray-500 text-sm">Scrapes AI/ML jobs from LinkedIn &amp; stores them in your database</p>
      </div>

      {/* Controls card */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-5">
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleStartScraper}
            disabled={isRunning}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors"
          >
            <span>▶</span> Start Scraper
          </button>

          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-5 py-2.5 bg-green-700 hover:bg-green-800 text-white font-semibold rounded-lg transition-colors"
          >
            <span>⬇</span> Export CSV
          </button>

          <button
            onClick={loadJobs}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors"
          >
            <span>↻</span> Refresh
          </button>

          <button
            onClick={handleClearJobs}
            className="flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors"
          >
            <span>✕</span> Clear All
          </button>
        </div>

        {showStatus && <StatusBar status={status} />}
      </div>

      {/* Stats */}
      <StatsRow jobs={jobs} />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by title, company, or keyword..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[200px] px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:border-blue-500"
        />
        <select
          value={locFilter}
          onChange={(e) => setLocFilter(e.target.value)}
          className="px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:border-blue-500"
        >
          <option value="">All Location Types</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="on-site">On-Site</option>
        </select>
        <select
          value={empFilter}
          onChange={(e) => setEmpFilter(e.target.value)}
          className="px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:border-blue-500"
        >
          <option value="">All Employment Types</option>
          <option value="full-time">Full-Time</option>
          <option value="part-time">Part-Time</option>
          <option value="contract">Contract</option>
        </select>
      </div>

      {/* Table */}
      <JobsTable jobs={filtered} />

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 px-5 py-3 rounded-xl shadow-lg text-white text-sm font-medium z-50 transition-all ${
            toast.type === "success"
              ? "bg-green-700"
              : toast.type === "error"
              ? "bg-red-600"
              : "bg-gray-800"
          }`}
        >
          {toast.msg}
        </div>
      )}
    </main>
  );
}
