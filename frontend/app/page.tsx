"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  clearJobs,
  exportCsvUrl,
  getJobs,
  getRuns,
  getStatus,
  Job,
  ScraperRun,
  ScraperStatus,
  ScrapeParams,
  startScraper,
} from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import StatsRow from "@/components/StatsRow";
import JobsTable from "@/components/JobsTable";
import RunHistory from "@/components/RunHistory";

const DEFAULT_STATUS: ScraperStatus = {
  running: false,
  progress: "",
  total: 0,
  scraped: 0,
  errors: [],
  done: false,
  elapsed_seconds: 0,
  daily_runs: 0,
  daily_date: "",
};

const DATE_OPTIONS = [
  { label: "Any Time", value: "" },
  { label: "Past 24 Hours", value: "r86400" },
  { label: "Past Week", value: "r604800" },
  { label: "Past Month", value: "r2592000" },
];

const SALARY_OPTIONS = [
  { label: "Any Salary", value: "" },
  { label: "$120,000+", value: "5" },
  { label: "$140,000+", value: "6" },
  { label: "$160,000+", value: "7" },
  { label: "$200,000+", value: "9" },
];

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filtered, setFiltered] = useState<Job[]>([]);
  const [runs, setRuns] = useState<ScraperRun[]>([]);
  const [status, setStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [showStatus, setShowStatus] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "" } | null>(null);

  const [keyword, setKeyword] = useState("");
  const [datePosted, setDatePosted] = useState("");
  const [salaryRange, setSalaryRange] = useState("");

  const [tableSearch, setTableSearch] = useState("");

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

  const loadRuns = useCallback(async () => {
    try {
      const data = await getRuns();
      setRuns(data);
    } catch {}
  }, []);

  useEffect(() => {
    const q = tableSearch.toLowerCase();
    setFiltered(
      jobs.filter((j) => {
        if (!q) return true;
        return `${j.job_title} ${j.company_name}`.toLowerCase().includes(q);
      })
    );
  }, [jobs, tableSearch]);

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
          loadRuns();
        }
      } catch {}
    }, 2000);
  }, [loadJobs, loadRuns]);

  useEffect(() => {
    loadJobs();
    loadRuns();
    getStatus()
      .then((s) => {
        setStatus(s);
        if (s.running) {
          setShowStatus(true);
          startPolling();
        }
      })
      .catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadJobs, loadRuns, startPolling]);

  const handleStartScraper = async () => {
    if (!keyword.trim()) {
      showToast("Please enter a job keyword before starting the scraper.", "error");
      return;
    }
    const params: ScrapeParams = {
      keyword: keyword.trim(),
      date_posted: datePosted,
      salary_range: salaryRange,
    };
    try {
      const res = await startScraper(params);
      if (res.detail) {
        const msg = typeof res.detail === "string" ? res.detail : JSON.stringify(res.detail);
        showToast(msg, "error");
        return;
      }
      showToast("Scraper started!", "success");
      setShowStatus(true);
      setStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleExportCSV = () => window.open(exportCsvUrl(), "_blank");

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
    <main className="max-w-screen-xl mx-auto px-6 py-10">

      <div className="text-center mb-10">
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl flex items-center justify-center shadow-lg">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="white">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </div>
          <div className="text-left">
            <h1 className="text-5xl font-black text-gray-900 leading-none tracking-tight">LinkedIn Job Scraper</h1>
            <p className="text-base font-bold text-blue-600 mt-1">Remote US Jobs &bull; AI-Powered Aggregation</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-7 mb-6">
        <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest mb-5">Search Configuration</h2>

        <div className="flex gap-3 mb-5">
          <div className="relative flex-1">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
            <input
              type="text"
              placeholder="Enter job title, skills, or keywords (e.g., AI Engineer, Data Scientist...)"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !isRunning && handleStartScraper()}
              className="w-full pl-11 pr-5 py-3.5 border-2 border-gray-200 focus:border-blue-500 rounded-xl text-base font-semibold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
            />
          </div>
          <button
            onClick={handleStartScraper}
            disabled={isRunning}
            className="flex items-center gap-2 px-7 py-3.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors shadow-sm text-base whitespace-nowrap"
          >
            {isRunning ? (
              <>
                <span className="animate-spin">⧖</span> Running...
              </>
            ) : (
              <>
                <span>▶</span> Start Scraper
              </>
            )}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex flex-col gap-1.5 min-w-[180px]">
            <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Date Posted</label>
            <select
              value={datePosted}
              onChange={(e) => setDatePosted(e.target.value)}
              className="px-4 py-3 border-2 border-gray-200 focus:border-blue-500 rounded-xl text-base font-bold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
            >
              {DATE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5 min-w-[180px]">
            <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Minimum Salary</label>
            <select
              value={salaryRange}
              onChange={(e) => setSalaryRange(e.target.value)}
              className="px-4 py-3 border-2 border-gray-200 focus:border-blue-500 rounded-xl text-base font-bold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
            >
              {SALARY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 ml-auto flex-wrap">
            <span className="flex items-center gap-2 px-4 py-2.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-xl text-sm font-bold">
              📍 Location: United States
            </span>
            <span className="flex items-center gap-2 px-4 py-2.5 bg-green-50 text-green-700 border border-green-200 rounded-xl text-sm font-bold">
              🏠 Work Type: Remote
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-gray-100">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors text-sm shadow-sm"
          >
            ⬇ Export CSV
          </button>
          <button
            onClick={loadJobs}
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm"
          >
            ↻ Refresh
          </button>
          <button
            onClick={handleClearJobs}
            className="flex items-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 hover:border-red-300 transition-colors text-sm"
          >
            ✕ Clear All
          </button>
        </div>

        {showStatus && <StatusBar status={status} />}
      </div>

      <StatsRow jobs={jobs} dailyRuns={status.daily_runs ?? 0} runs={runs} />

      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
          <input
            type="text"
            placeholder="Filter loaded jobs by title, company, or keyword..."
            value={tableSearch}
            onChange={(e) => setTableSearch(e.target.value)}
            className="w-full pl-11 pr-5 py-3 border-2 border-gray-200 rounded-xl text-base font-semibold bg-white focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
        <span className="text-base font-bold text-gray-500">
          {filtered.length} of {jobs.length} jobs
        </span>
      </div>

      <JobsTable jobs={filtered} />

      <div className="mt-8">
        <RunHistory runs={runs} />
      </div>

      {toast && (
        <div
          className={`fixed bottom-6 right-6 px-6 py-4 rounded-2xl shadow-xl text-white text-base font-bold z-50 transition-all ${
            toast.type === "success"
              ? "bg-emerald-600"
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
