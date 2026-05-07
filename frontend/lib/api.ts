export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface Job {
  id: number;
  job_title: string;
  company_name: string;
  job_url: string;
}

export interface ScraperStatus {
  running: boolean;
  progress: string;
  total: number;
  scraped: number;
  errors: string[];
  done: boolean;
  elapsed_seconds?: number;
  daily_runs?: number;
  daily_date?: string;
}

export interface ScraperRun {
  id: number;
  keyword: string;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  pages_scraped: number;
  jobs_found: number;
  jobs_saved: number;
  error_count: number;
  run_status: "success" | "partial" | "failed";
}

export interface ScrapeParams {
  keyword: string;
  date_posted: string;
  salary_range: string;
}

export async function startScraper(params: ScrapeParams): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getStatus(): Promise<ScraperStatus> {
  const res = await fetch(`${API_BASE}/status`);
  return res.json();
}

export async function getJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/jobs`);
  return res.json();
}

export async function clearJobs(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/clear`, { method: "DELETE" });
  return res.json();
}

export async function deleteJob(id: number): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/${id}`, { method: "DELETE" });
  return res.json();
}

export async function getRuns(): Promise<ScraperRun[]> {
  const res = await fetch(`${API_BASE}/runs`);
  return res.json();
}

export function exportCsvUrl(): string {
  return `${API_BASE}/export/csv`;
}
