"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  clearLinkedInJobs,
  clearStartupJobs,
  clearIndeedJobs,
  clearDiceJobs,
  clearAdzunaJobs,
  exportLinkedInCsvUrl,
  exportStartupJobsCsvUrl,
  exportIndeedCsvUrl,
  exportDiceCsvUrl,
  exportAdzunaCsvUrl,
  getLinkedInJobs,
  getLinkedInStatus,
  getStartupJobs,
  getStartupJobsStatus,
  getIndeedJobs,
  getIndeedStatus,
  getDiceJobs,
  getDiceStatus,
  getAdzunaJobs,
  getAdzunaStatus,
  getRuns,
  Job,
  StartupJob,
  IndeedJob,
  DiceJob,
  AdzunaJob,
  ScraperRun,
  ScraperStatus,
  startLinkedInScraper,
  startStartupJobsScraper,
  startIndeedScraper,
  startDiceScraper,
  startAdzunaScraper,
} from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import StatsRow from "@/components/StatsRow";
import JobsTable from "@/components/JobsTable";
import RunHistory from "@/components/RunHistory";

type Tab = "linkedin" | "startupjobs" | "indeed" | "dice" | "adzuna";

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

// ── LinkedIn filter options ───────────────────────────────────────────────────

const LI_DATE_OPTIONS = [
  { label: "Any Time",      value: "" },
  { label: "Past 24 Hours", value: "r86400" },
  { label: "Past Week",     value: "r604800" },
  { label: "Past Month",    value: "r2592000" },
];

const LI_SALARY_OPTIONS = [
  { label: "Any Salary",  value: "" },
  { label: "$120,000+",   value: "5" },
  { label: "$140,000+",   value: "6" },
  { label: "$160,000+",   value: "7" },
  { label: "$200,000+",   value: "9" },
];

// ── Startup Jobs filter options ───────────────────────────────────────────────

const SJ_TYPE_OPTIONS = [
  { label: "Any Type",    value: "" },
  { label: "Full Time",   value: "full-time" },
  { label: "Contractor",  value: "contractor" },
  { label: "Part Time",   value: "part-time" },
  { label: "Internship",  value: "internship" },
];

const SJ_SALARY_OPTIONS = [
  { label: "Any Salary",  value: "" },
  { label: "$120,000+",   value: "120000" },
  { label: "$140,000+",   value: "140000" },
  { label: "$160,000+",   value: "160000" },
  { label: "$200,000+",   value: "200000" },
];

const SJ_TIME_OPTIONS = [
  { label: "Any Time",      value: "" },
  { label: "Past 24 Hours", value: "1" },
  { label: "Past Week",     value: "7" },
  { label: "Past Month",    value: "30" },
];

// ── Indeed filter options ─────────────────────────────────────────────────────

const IN_PAY_OPTIONS = [
  { label: "Any Pay",     value: "" },
  { label: "$130,000+",   value: "130000" },
  { label: "$150,000+",   value: "150000" },
  { label: "$175,000+",   value: "175000" },
  { label: "$200,000+",   value: "200000" },
  { label: "$225,000+",   value: "225000" },
];

const IN_TYPE_OPTIONS = [
  { label: "Any Type",    value: "" },
  { label: "Full Time",   value: "fulltime" },
  { label: "Part Time",   value: "parttime" },
  { label: "Contract",    value: "contract" },
  { label: "Internship",  value: "internship" },
  { label: "Temporary",   value: "temporary" },
];

const IN_DATE_OPTIONS = [
  { label: "Any Time",      value: "" },
  { label: "Last 24 Hours", value: "1" },
  { label: "Last 3 Days",   value: "3" },
  { label: "Last 7 Days",   value: "7" },
  { label: "Last 14 Days",  value: "14" },
];

// ── Dice filter options ───────────────────────────────────────────────────────

const DC_DATE_OPTIONS = [
  { label: "No Preference", value: "" },
  { label: "Today",         value: "ONE" },
  { label: "Last 3 Days",   value: "THREE" },
  { label: "Last 7 Days",   value: "SEVEN" },
];

const DC_EMPLOYMENT_OPTIONS = [
  { label: "Full Time",   value: "FULLTIME" },
  { label: "Part Time",   value: "PARTTIME" },
  { label: "Contract",    value: "CONTRACTS" },
  { label: "Third Party", value: "THIRD_PARTY" },
  { label: "Internship",  value: "INTERN" },
];

// ── Adzuna filter options ─────────────────────────────────────────────────────

const AZ_MAX_DAYS_OPTIONS = [
  { label: "Any Time",      value: "" },
  { label: "Last 24 Hours", value: "1" },
  { label: "Last 7 Days",   value: "7" },
  { label: "Last 30 Days",  value: "30" },
];

const AZ_CONTRACT_OPTIONS = [
  { label: "Any Type",  value: "" },
  { label: "Permanent", value: "permanent" },
  { label: "Contract",  value: "contract" },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("linkedin");

  // Data
  const [linkedinJobs, setLinkedinJobs] = useState<Job[]>([]);
  const [startupJobs,  setStartupJobs]  = useState<StartupJob[]>([]);
  const [indeedJobs,   setIndeedJobs]   = useState<IndeedJob[]>([]);
  const [diceJobs,     setDiceJobs]     = useState<DiceJob[]>([]);
  const [adzunaJobs,   setAdzunaJobs]   = useState<AdzunaJob[]>([]);
  const [runs,         setRuns]         = useState<ScraperRun[]>([]);

  // Status per scraper
  const [liStatus, setLiStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [sjStatus, setSjStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [inStatus, setInStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [dcStatus, setDcStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [azStatus, setAzStatus] = useState<ScraperStatus>(DEFAULT_STATUS);
  const [showLiStatus, setShowLiStatus] = useState(false);
  const [showSjStatus, setShowSjStatus] = useState(false);
  const [showInStatus, setShowInStatus] = useState(false);
  const [showDcStatus, setShowDcStatus] = useState(false);
  const [showAzStatus, setShowAzStatus] = useState(false);

  // LinkedIn form state
  const [liKeyword,    setLiKeyword]    = useState("");
  const [liDate,       setLiDate]       = useState("");
  const [liSalary,     setLiSalary]     = useState("");
  const [liSearch,     setLiSearch]     = useState("");

  // Startup Jobs form state
  const [sjKeyword,    setSjKeyword]    = useState("");
  const [sjType,       setSjType]       = useState("");
  const [sjSalary,     setSjSalary]     = useState("");
  const [sjTime,       setSjTime]       = useState("");
  const [sjSearch,     setSjSearch]     = useState("");

  // Indeed form state
  const [inKeyword,    setInKeyword]    = useState("");
  const [inPay,        setInPay]        = useState("");
  const [inType,       setInType]       = useState("");
  const [inDate,       setInDate]       = useState("");
  const [inSearch,     setInSearch]     = useState("");

  // Dice form state
  const [dcKeyword,          setDcKeyword]          = useState("");
  const [dcDate,             setDcDate]             = useState("");
  const [dcEmploymentTypes,  setDcEmploymentTypes]  = useState<string[]>([]);
  const [dcSearch,           setDcSearch]           = useState("");

  // Adzuna form state
  const [azKeyword,       setAzKeyword]       = useState("");
  const [azLocation,      setAzLocation]      = useState("");
  const [azMaxDays,       setAzMaxDays]       = useState("");
  const [azContractType,  setAzContractType]  = useState("");
  const [azSearch,        setAzSearch]        = useState("");

  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "" } | null>(null);

  const liPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sjPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const dcPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const azPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showToast = (msg: string, type: "success" | "error" | "" = "") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  // ── Data loaders ─────────────────────────────────────────────────────────────

  const loadLinkedInJobs = useCallback(async () => {
    try { setLinkedinJobs(await getLinkedInJobs()); } catch { /* ignore */ }
  }, []);

  const loadStartupJobs = useCallback(async () => {
    try { setStartupJobs(await getStartupJobs()); } catch { /* ignore */ }
  }, []);

  const loadIndeedJobs = useCallback(async () => {
    try { setIndeedJobs(await getIndeedJobs()); } catch { /* ignore */ }
  }, []);

  const loadDiceJobs = useCallback(async () => {
    try { setDiceJobs(await getDiceJobs()); } catch { /* ignore */ }
  }, []);

  const loadAdzunaJobs = useCallback(async () => {
    try { setAdzunaJobs(await getAdzunaJobs()); } catch { /* ignore */ }
  }, []);

  const loadRuns = useCallback(async () => {
    try { setRuns(await getRuns()); } catch { /* ignore */ }
  }, []);

  // ── Polling ───────────────────────────────────────────────────────────────────

  const startLiPolling = useCallback(() => {
    if (liPollRef.current) clearInterval(liPollRef.current);
    liPollRef.current = setInterval(async () => {
      try {
        const s = await getLinkedInStatus();
        setLiStatus(s);
        if (s.done) {
          clearInterval(liPollRef.current!);
          liPollRef.current = null;
          loadLinkedInJobs();
          loadRuns();
        }
      } catch { /* ignore */ }
    }, 2000);
  }, [loadLinkedInJobs, loadRuns]);

  const startSjPolling = useCallback(() => {
    if (sjPollRef.current) clearInterval(sjPollRef.current);
    sjPollRef.current = setInterval(async () => {
      try {
        const s = await getStartupJobsStatus();
        setSjStatus(s);
        if (s.done) {
          clearInterval(sjPollRef.current!);
          sjPollRef.current = null;
          loadStartupJobs();
          loadRuns();
        }
      } catch { /* ignore */ }
    }, 2000);
  }, [loadStartupJobs, loadRuns]);

  const startInPolling = useCallback(() => {
    if (inPollRef.current) clearInterval(inPollRef.current);
    inPollRef.current = setInterval(async () => {
      try {
        const s = await getIndeedStatus();
        setInStatus(s);
        if (s.done) {
          clearInterval(inPollRef.current!);
          inPollRef.current = null;
          loadIndeedJobs();
          loadRuns();
        }
      } catch { /* ignore */ }
    }, 2000);
  }, [loadIndeedJobs, loadRuns]);

  const startDcPolling = useCallback(() => {
    if (dcPollRef.current) clearInterval(dcPollRef.current);
    dcPollRef.current = setInterval(async () => {
      try {
        const s = await getDiceStatus();
        setDcStatus(s);
        if (s.done) {
          clearInterval(dcPollRef.current!);
          dcPollRef.current = null;
          loadDiceJobs();
          loadRuns();
        }
      } catch { /* ignore */ }
    }, 2000);
  }, [loadDiceJobs, loadRuns]);

  const startAzPolling = useCallback(() => {
    if (azPollRef.current) clearInterval(azPollRef.current);
    azPollRef.current = setInterval(async () => {
      try {
        const s = await getAdzunaStatus();
        setAzStatus(s);
        if (s.done) {
          clearInterval(azPollRef.current!);
          azPollRef.current = null;
          loadAdzunaJobs();
          loadRuns();
        }
      } catch { /* ignore */ }
    }, 2000);
  }, [loadAdzunaJobs, loadRuns]);

  // ── Init ──────────────────────────────────────────────────────────────────────

  useEffect(() => {
    loadLinkedInJobs();
    loadStartupJobs();
    loadIndeedJobs();
    loadDiceJobs();
    loadAdzunaJobs();
    loadRuns();

    getLinkedInStatus().then((s) => {
      setLiStatus(s);
      if (s.running) { setShowLiStatus(true); startLiPolling(); }
    }).catch(() => {});

    getStartupJobsStatus().then((s) => {
      setSjStatus(s);
      if (s.running) { setShowSjStatus(true); startSjPolling(); }
    }).catch(() => {});

    getIndeedStatus().then((s) => {
      setInStatus(s);
      if (s.running) { setShowInStatus(true); startInPolling(); }
    }).catch(() => {});

    getDiceStatus().then((s) => {
      setDcStatus(s);
      if (s.running) { setShowDcStatus(true); startDcPolling(); }
    }).catch(() => {});

    getAdzunaStatus().then((s) => {
      setAzStatus(s);
      if (s.running) { setShowAzStatus(true); startAzPolling(); }
    }).catch(() => {});

    return () => {
      if (liPollRef.current) clearInterval(liPollRef.current);
      if (sjPollRef.current) clearInterval(sjPollRef.current);
      if (inPollRef.current) clearInterval(inPollRef.current);
      if (dcPollRef.current) clearInterval(dcPollRef.current);
      if (azPollRef.current) clearInterval(azPollRef.current);
    };
  }, [loadLinkedInJobs, loadStartupJobs, loadIndeedJobs, loadDiceJobs, loadAdzunaJobs, loadRuns,
      startLiPolling, startSjPolling, startInPolling, startDcPolling, startAzPolling]);

  // ── Handlers ─────────────────────────────────────────────────────────────────

  const handleStartLinkedIn = async () => {
    if (!liKeyword.trim()) {
      showToast("Please enter a keyword.", "error");
      return;
    }
    try {
      const res = await startLinkedInScraper({
        keyword: liKeyword.trim(),
        date_posted: liDate,
        salary_range: liSalary,
      });
      if (res.detail) { showToast(String(res.detail), "error"); return; }
      showToast("LinkedIn scraper started!", "success");
      setShowLiStatus(true);
      setLiStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startLiPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleStartStartupJobs = async () => {
    if (!sjKeyword.trim()) {
      showToast("Please enter a keyword.", "error");
      return;
    }
    try {
      const res = await startStartupJobsScraper({
        keyword: sjKeyword.trim(),
        job_type: sjType,
        salary: sjSalary,
        time_filter: sjTime,
      });
      if (res.detail) { showToast(String(res.detail), "error"); return; }
      showToast("Startup Jobs scraper started!", "success");
      setShowSjStatus(true);
      setSjStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startSjPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleClearLinkedIn = async () => {
    if (!confirm("Delete all LinkedIn jobs from the database?")) return;
    try {
      await clearLinkedInJobs();
      showToast("LinkedIn jobs cleared.", "success");
      setLinkedinJobs([]);
    } catch { showToast("Failed to clear jobs.", "error"); }
  };

  const handleClearStartupJobs = async () => {
    if (!confirm("Delete all Startup Jobs from the database?")) return;
    try {
      await clearStartupJobs();
      showToast("Startup Jobs cleared.", "success");
      setStartupJobs([]);
    } catch { showToast("Failed to clear jobs.", "error"); }
  };

  const handleStartIndeed = async () => {
    if (!inKeyword.trim()) {
      showToast("Please enter a keyword.", "error");
      return;
    }
    try {
      const res = await startIndeedScraper({
        keyword:     inKeyword.trim(),
        pay:         inPay,
        job_type:    inType,
        date_posted: inDate,
      });
      if (res.detail) { showToast(String(res.detail), "error"); return; }
      showToast("Indeed scraper started!", "success");
      setShowInStatus(true);
      setInStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startInPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleClearIndeed = async () => {
    if (!confirm("Delete all Indeed jobs from the database?")) return;
    try {
      await clearIndeedJobs();
      showToast("Indeed jobs cleared.", "success");
      setIndeedJobs([]);
    } catch { showToast("Failed to clear jobs.", "error"); }
  };

  const toggleDcEmploymentType = (value: string) => {
    setDcEmploymentTypes((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  const handleStartDice = async () => {
    if (!dcKeyword.trim()) {
      showToast("Please enter a keyword.", "error");
      return;
    }
    try {
      const res = await startDiceScraper({
        keyword:         dcKeyword.trim(),
        date_posted:     dcDate,
        employment_type: dcEmploymentTypes.join("|"),
      });
      if (res.detail) { showToast(String(res.detail), "error"); return; }
      showToast("Dice scraper started!", "success");
      setShowDcStatus(true);
      setDcStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startDcPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleClearDice = async () => {
    if (!confirm("Delete all Dice jobs from the database?")) return;
    try {
      await clearDiceJobs();
      showToast("Dice jobs cleared.", "success");
      setDiceJobs([]);
    } catch { showToast("Failed to clear jobs.", "error"); }
  };

  const handleStartAdzuna = async () => {
    if (!azKeyword.trim()) {
      showToast("Please enter a keyword.", "error");
      return;
    }
    try {
      const res = await startAdzunaScraper({
        keyword:       azKeyword.trim(),
        location:      azLocation.trim(),
        max_days_old:  azMaxDays,
        contract_type: azContractType,
      });
      if (res.detail) { showToast(String(res.detail), "error"); return; }
      showToast("Adzuna scraper started!", "success");
      setShowAzStatus(true);
      setAzStatus({ ...DEFAULT_STATUS, running: true, progress: "Starting..." });
      startAzPolling();
    } catch {
      showToast("Cannot reach backend. Is it running on port 8000?", "error");
    }
  };

  const handleClearAdzuna = async () => {
    if (!confirm("Delete all Adzuna jobs from the database?")) return;
    try {
      await clearAdzunaJobs();
      showToast("Adzuna jobs cleared.", "success");
      setAdzunaJobs([]);
    } catch { showToast("Failed to clear jobs.", "error"); }
  };

  // ── Filtered views ────────────────────────────────────────────────────────────

  const filteredLinkedin = linkedinJobs.filter((j) => {
    if (!liSearch) return true;
    return `${j.job_title} ${j.company_name}`.toLowerCase().includes(liSearch.toLowerCase());
  });

  const filteredStartup = startupJobs.filter((j) => {
    if (!sjSearch) return true;
    return `${j.job_title} ${j.company_name}`.toLowerCase().includes(sjSearch.toLowerCase());
  });

  const filteredIndeed = indeedJobs.filter((j) => {
    if (!inSearch) return true;
    return `${j.job_title} ${j.company_name}`.toLowerCase().includes(inSearch.toLowerCase());
  });

  const filteredDice = diceJobs.filter((j) => {
    if (!dcSearch) return true;
    return `${j.job_title} ${j.company_name}`.toLowerCase().includes(dcSearch.toLowerCase());
  });

  const filteredAdzuna = adzunaJobs.filter((j) => {
    if (!azSearch) return true;
    return `${j.job_title} ${j.company_name}`.toLowerCase().includes(azSearch.toLowerCase());
  });

  const SELECT_CLS =
    "px-4 py-3 border-2 border-gray-200 focus:border-blue-500 rounded-xl text-base font-bold bg-gray-50 focus:bg-white focus:outline-none transition-colors";

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <main className="max-w-screen-xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="text-center mb-10">
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl flex items-center justify-center shadow-lg">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="white">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </div>
          <div className="text-left">
            <h1 className="text-5xl font-black text-gray-900 leading-none tracking-tight">Job Scraper Hub</h1>
            <p className="text-base font-bold text-blue-600 mt-1">LinkedIn &bull; Startup.jobs &bull; Remote US Jobs</p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <StatsRow
        linkedinJobs={linkedinJobs}
        startupJobs={startupJobs}
        indeedJobs={indeedJobs}
        diceJobs={diceJobs}
        adzunaJobs={adzunaJobs}
        runs={runs}
      />

      {/* Tab switcher */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab("linkedin")}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors border-2 ${
            activeTab === "linkedin"
              ? "bg-blue-600 border-blue-600 text-white shadow-md"
              : "bg-white border-gray-200 text-gray-600 hover:border-blue-300"
          }`}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
          LinkedIn
        </button>
        <button
          onClick={() => setActiveTab("startupjobs")}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors border-2 ${
            activeTab === "startupjobs"
              ? "bg-orange-500 border-orange-500 text-white shadow-md"
              : "bg-white border-gray-200 text-gray-600 hover:border-orange-300"
          }`}
        >
          🚀 Startup.jobs
        </button>
        <button
          onClick={() => setActiveTab("indeed")}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors border-2 ${
            activeTab === "indeed"
              ? "bg-violet-600 border-violet-600 text-white shadow-md"
              : "bg-white border-gray-200 text-gray-600 hover:border-violet-300"
          }`}
        >
          🔍 Indeed
        </button>
        <button
          onClick={() => setActiveTab("dice")}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors border-2 ${
            activeTab === "dice"
              ? "bg-teal-600 border-teal-600 text-white shadow-md"
              : "bg-white border-gray-200 text-gray-600 hover:border-teal-300"
          }`}
        >
          🎲 Dice
        </button>
        <button
          onClick={() => setActiveTab("adzuna")}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm transition-colors border-2 ${
            activeTab === "adzuna"
              ? "bg-amber-500 border-amber-500 text-white shadow-md"
              : "bg-white border-gray-200 text-gray-600 hover:border-amber-300"
          }`}
        >
          ⚡ Adzuna
        </button>
      </div>

      {/* ── LinkedIn Tab ──────────────────────────────────────────────────────── */}
      {activeTab === "linkedin" && (
        <>
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-7 mb-6">
            <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest mb-5">LinkedIn Search</h2>

            <div className="flex gap-3 mb-5">
              <div className="relative flex-1">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
                <input
                  type="text"
                  placeholder="Job title, skills, or keywords..."
                  value={liKeyword}
                  onChange={(e) => setLiKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !liStatus.running && handleStartLinkedIn()}
                  className="w-full pl-11 pr-5 py-3.5 border-2 border-gray-200 focus:border-blue-500 rounded-xl text-base font-semibold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleStartLinkedIn}
                disabled={liStatus.running}
                className="flex items-center gap-2 px-7 py-3.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors shadow-sm text-base whitespace-nowrap"
              >
                {liStatus.running ? <><span className="animate-spin">⧖</span> Running...</> : <><span>▶</span> Start Scraper</>}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex flex-col gap-1.5 min-w-[180px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Date Posted</label>
                <select value={liDate} onChange={(e) => setLiDate(e.target.value)} className={SELECT_CLS}>
                  {LI_DATE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[180px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Minimum Salary</label>
                <select value={liSalary} onChange={(e) => setLiSalary(e.target.value)} className={SELECT_CLS}>
                  {LI_SALARY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2 ml-auto flex-wrap">
                <span className="flex items-center gap-2 px-4 py-2.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-xl text-sm font-bold">📍 United States</span>
                <span className="flex items-center gap-2 px-4 py-2.5 bg-green-50 text-green-700 border border-green-200 rounded-xl text-sm font-bold">🏠 Remote</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-gray-100">
              <button onClick={() => window.open(exportLinkedInCsvUrl(), "_blank")} className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors text-sm shadow-sm">⬇ Export CSV</button>
              <button onClick={loadLinkedInJobs} className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm">↻ Refresh</button>
              <button onClick={handleClearLinkedIn} className="flex items-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 hover:border-red-300 transition-colors text-sm">✕ Clear All</button>
            </div>

            {showLiStatus && <StatusBar status={liStatus} />}
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
              <input type="text" placeholder="Filter by title or company..." value={liSearch} onChange={(e) => setLiSearch(e.target.value)} className="w-full pl-11 pr-5 py-3 border-2 border-gray-200 rounded-xl text-base font-semibold bg-white focus:outline-none focus:border-blue-500 transition-colors" />
            </div>
            <span className="text-base font-bold text-gray-500">{filteredLinkedin.length} of {linkedinJobs.length} jobs</span>
          </div>

          <JobsTable jobs={filteredLinkedin} />
        </>
      )}

      {/* ── Startup Jobs Tab ──────────────────────────────────────────────────── */}
      {activeTab === "startupjobs" && (
        <>
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-7 mb-6">
            <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest mb-5">Startup.jobs Search</h2>

            <div className="flex gap-3 mb-5">
              <div className="relative flex-1">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
                <input
                  type="text"
                  placeholder="Job title, skills, or keywords..."
                  value={sjKeyword}
                  onChange={(e) => setSjKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !sjStatus.running && handleStartStartupJobs()}
                  className="w-full pl-11 pr-5 py-3.5 border-2 border-gray-200 focus:border-orange-400 rounded-xl text-base font-semibold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleStartStartupJobs}
                disabled={sjStatus.running}
                className="flex items-center gap-2 px-7 py-3.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors shadow-sm text-base whitespace-nowrap"
              >
                {sjStatus.running ? <><span className="animate-spin">⧖</span> Running...</> : <><span>▶</span> Start Scraper</>}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Job Type</label>
                <select value={sjType} onChange={(e) => setSjType(e.target.value)} className={SELECT_CLS}>
                  {SJ_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Minimum Salary</label>
                <select value={sjSalary} onChange={(e) => setSjSalary(e.target.value)} className={SELECT_CLS}>
                  {SJ_SALARY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Date Posted</label>
                <select value={sjTime} onChange={(e) => setSjTime(e.target.value)} className={SELECT_CLS}>
                  {SJ_TIME_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2 ml-auto flex-wrap">
                <span className="flex items-center gap-2 px-4 py-2.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-xl text-sm font-bold">📍 United States</span>
                <span className="flex items-center gap-2 px-4 py-2.5 bg-green-50 text-green-700 border border-green-200 rounded-xl text-sm font-bold">🏠 Remote</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-gray-100">
              <button onClick={() => window.open(exportStartupJobsCsvUrl(), "_blank")} className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors text-sm shadow-sm">⬇ Export CSV</button>
              <button onClick={loadStartupJobs} className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm">↻ Refresh</button>
              <button onClick={handleClearStartupJobs} className="flex items-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 hover:border-red-300 transition-colors text-sm">✕ Clear All</button>
            </div>

            {showSjStatus && <StatusBar status={sjStatus} />}
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
              <input type="text" placeholder="Filter by title or company..." value={sjSearch} onChange={(e) => setSjSearch(e.target.value)} className="w-full pl-11 pr-5 py-3 border-2 border-gray-200 rounded-xl text-base font-semibold bg-white focus:outline-none focus:border-orange-400 transition-colors" />
            </div>
            <span className="text-base font-bold text-gray-500">{filteredStartup.length} of {startupJobs.length} jobs</span>
          </div>

          <JobsTable jobs={filteredStartup} />
        </>
      )}

      {/* ── Indeed Tab ───────────────────────────────────────────────────────── */}
      {activeTab === "indeed" && (
        <>
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-7 mb-6">
            <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest mb-5">Indeed Search</h2>

            <div className="flex gap-3 mb-5">
              <div className="relative flex-1">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
                <input
                  type="text"
                  placeholder="Job title, keyword, or company..."
                  value={inKeyword}
                  onChange={(e) => setInKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !inStatus.running && handleStartIndeed()}
                  className="w-full pl-11 pr-5 py-3.5 border-2 border-gray-200 focus:border-violet-500 rounded-xl text-base font-semibold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleStartIndeed}
                disabled={inStatus.running}
                className="flex items-center gap-2 px-7 py-3.5 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors shadow-sm text-base whitespace-nowrap"
              >
                {inStatus.running ? <><span className="animate-spin">⧖</span> Running...</> : <><span>▶</span> Start Scraper</>}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Pay</label>
                <select value={inPay} onChange={(e) => setInPay(e.target.value)} className={SELECT_CLS}>
                  {IN_PAY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Job Type</label>
                <select value={inType} onChange={(e) => setInType(e.target.value)} className={SELECT_CLS}>
                  {IN_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Date Posted</label>
                <select value={inDate} onChange={(e) => setInDate(e.target.value)} className={SELECT_CLS}>
                  {IN_DATE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2 ml-auto flex-wrap">
                <span className="flex items-center gap-2 px-4 py-2.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-xl text-sm font-bold">📍 United States</span>
                <span className="flex items-center gap-2 px-4 py-2.5 bg-green-50 text-green-700 border border-green-200 rounded-xl text-sm font-bold">🏠 Remote</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-gray-100">
              <button onClick={() => window.open(exportIndeedCsvUrl(), "_blank")} className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors text-sm shadow-sm">⬇ Export CSV</button>
              <button onClick={loadIndeedJobs} className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm">↻ Refresh</button>
              <button onClick={handleClearIndeed} className="flex items-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 hover:border-red-300 transition-colors text-sm">✕ Clear All</button>
            </div>

            {showInStatus && <StatusBar status={inStatus} />}
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
              <input type="text" placeholder="Filter by title or company..." value={inSearch} onChange={(e) => setInSearch(e.target.value)} className="w-full pl-11 pr-5 py-3 border-2 border-gray-200 rounded-xl text-base font-semibold bg-white focus:outline-none focus:border-violet-500 transition-colors" />
            </div>
            <span className="text-base font-bold text-gray-500">{filteredIndeed.length} of {indeedJobs.length} jobs</span>
          </div>

          <JobsTable jobs={filteredIndeed} />
        </>
      )}

      {/* ── Dice Tab ─────────────────────────────────────────────────────────── */}
      {activeTab === "dice" && (
        <>
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-7 mb-6">
            <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest mb-5">Dice Search</h2>

            <div className="flex gap-3 mb-5">
              <div className="relative flex-1">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
                <input
                  type="text"
                  placeholder="Job title, skills, or keywords..."
                  value={dcKeyword}
                  onChange={(e) => setDcKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !dcStatus.running && handleStartDice()}
                  className="w-full pl-11 pr-5 py-3.5 border-2 border-gray-200 focus:border-teal-500 rounded-xl text-base font-semibold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleStartDice}
                disabled={dcStatus.running}
                className="flex items-center gap-2 px-7 py-3.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors shadow-sm text-base whitespace-nowrap"
              >
                {dcStatus.running ? <><span className="animate-spin">⧖</span> Running...</> : <><span>▶</span> Start Scraper</>}
              </button>
            </div>

            <div className="flex flex-wrap items-start gap-6 mb-5">
              <div className="flex flex-col gap-1.5 min-w-[180px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Date Posted</label>
                <select value={dcDate} onChange={(e) => setDcDate(e.target.value)} className={SELECT_CLS}>
                  {DC_DATE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Employment Type</label>
                <div className="flex flex-wrap gap-2">
                  {DC_EMPLOYMENT_OPTIONS.map((o) => (
                    <label
                      key={o.value}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border-2 cursor-pointer text-sm font-bold transition-colors select-none ${
                        dcEmploymentTypes.includes(o.value)
                          ? "bg-teal-600 border-teal-600 text-white"
                          : "bg-gray-50 border-gray-200 text-gray-600 hover:border-teal-400"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={dcEmploymentTypes.includes(o.value)}
                        onChange={() => toggleDcEmploymentType(o.value)}
                      />
                      {o.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 ml-auto flex-wrap self-end">
                <span className="flex items-center gap-2 px-4 py-2.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-xl text-sm font-bold">📍 United States</span>
                <span className="flex items-center gap-2 px-4 py-2.5 bg-green-50 text-green-700 border border-green-200 rounded-xl text-sm font-bold">🏠 Remote</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-gray-100">
              <button onClick={() => window.open(exportDiceCsvUrl(), "_blank")} className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors text-sm shadow-sm">⬇ Export CSV</button>
              <button onClick={loadDiceJobs} className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm">↻ Refresh</button>
              <button onClick={handleClearDice} className="flex items-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 hover:border-red-300 transition-colors text-sm">✕ Clear All</button>
            </div>

            {showDcStatus && <StatusBar status={dcStatus} />}
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
              <input type="text" placeholder="Filter by title or company..." value={dcSearch} onChange={(e) => setDcSearch(e.target.value)} className="w-full pl-11 pr-5 py-3 border-2 border-gray-200 rounded-xl text-base font-semibold bg-white focus:outline-none focus:border-teal-500 transition-colors" />
            </div>
            <span className="text-base font-bold text-gray-500">{filteredDice.length} of {diceJobs.length} jobs</span>
          </div>

          <JobsTable jobs={filteredDice} />
        </>
      )}

      {/* ── Adzuna Tab ───────────────────────────────────────────────────────── */}
      {activeTab === "adzuna" && (
        <>
          <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-7 mb-6">
            <h2 className="text-sm font-black text-gray-500 uppercase tracking-widest mb-5">Adzuna Search</h2>

            <div className="flex gap-3 mb-5">
              <div className="relative flex-1">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
                <input
                  type="text"
                  placeholder="Job title, skills, or keywords..."
                  value={azKeyword}
                  onChange={(e) => setAzKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !azStatus.running && handleStartAdzuna()}
                  className="w-full pl-11 pr-5 py-3.5 border-2 border-gray-200 focus:border-amber-500 rounded-xl text-base font-semibold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
                />
              </div>
              <button
                onClick={handleStartAdzuna}
                disabled={azStatus.running}
                className="flex items-center gap-2 px-7 py-3.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors shadow-sm text-base whitespace-nowrap"
              >
                {azStatus.running ? <><span className="animate-spin">⧖</span> Running...</> : <><span>▶</span> Start Scraper</>}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex flex-col gap-1.5 min-w-[200px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Location</label>
                <input
                  type="text"
                  placeholder="e.g. New York, Remote..."
                  value={azLocation}
                  onChange={(e) => setAzLocation(e.target.value)}
                  className="px-4 py-3 border-2 border-gray-200 focus:border-amber-500 rounded-xl text-base font-bold bg-gray-50 focus:bg-white focus:outline-none transition-colors"
                />
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Date Posted</label>
                <select value={azMaxDays} onChange={(e) => setAzMaxDays(e.target.value)} className={SELECT_CLS}>
                  {AZ_MAX_DAYS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1.5 min-w-[160px]">
                <label className="text-xs font-black text-gray-500 uppercase tracking-wide">Contract Type</label>
                <select value={azContractType} onChange={(e) => setAzContractType(e.target.value)} className={SELECT_CLS}>
                  {AZ_CONTRACT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="flex items-center gap-2 ml-auto flex-wrap">
                <span className="flex items-center gap-2 px-4 py-2.5 bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-xl text-sm font-bold">📍 United States</span>
                <span className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-xl text-sm font-bold">⚡ REST API</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-gray-100">
              <button onClick={() => window.open(exportAdzunaCsvUrl(), "_blank")} className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors text-sm shadow-sm">⬇ Export CSV</button>
              <button onClick={loadAdzunaJobs} className="flex items-center gap-2 px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl transition-colors text-sm">↻ Refresh</button>
              <button onClick={handleClearAdzuna} className="flex items-center gap-2 px-5 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-xl border border-red-200 hover:border-red-300 transition-colors text-sm">✕ Clear All</button>
            </div>

            {showAzStatus && <StatusBar status={azStatus} />}
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">🔎</span>
              <input type="text" placeholder="Filter by title or company..." value={azSearch} onChange={(e) => setAzSearch(e.target.value)} className="w-full pl-11 pr-5 py-3 border-2 border-gray-200 rounded-xl text-base font-semibold bg-white focus:outline-none focus:border-amber-500 transition-colors" />
            </div>
            <span className="text-base font-bold text-gray-500">{filteredAdzuna.length} of {adzunaJobs.length} jobs</span>
          </div>

          <JobsTable jobs={filteredAdzuna} />
        </>
      )}

      {/* Run history — always visible below tabs */}
      <div className="mt-8">
        <RunHistory runs={runs} />
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 px-6 py-4 rounded-2xl shadow-xl text-white text-base font-bold z-50 transition-all ${
          toast.type === "success" ? "bg-emerald-600" : toast.type === "error" ? "bg-red-600" : "bg-gray-800"
        }`}>
          {toast.msg}
        </div>
      )}
    </main>
  );
}
