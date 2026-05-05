export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface Job {
  id: number;
  job_title: string;
  company_name: string;
  location_type: string;
  employment_type: string;
  salary: string;
  skills: string;
  about_job: string;
  job_url: string;
  scraped_at: string | null;
}

export interface ScraperStatus {
  running: boolean;
  progress: string;
  total: number;
  scraped: number;
  errors: string[];
  done: boolean;
}

export async function startScraper(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape`, { method: "POST" });
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

export function exportCsvUrl(): string {
  return `${API_BASE}/export/csv`;
}
