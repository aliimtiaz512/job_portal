export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export interface Job {
  id: number;
  job_title: string;
  company_name: string;
  job_url: string;
}

export type StartupJob = Job; // same shape, different table

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
  scraper: string;
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

export interface LinkedInScrapeParams {
  keyword: string;
  date_posted: string;
  salary_range: string;
}

export interface StartupJobsScrapeParams {
  keyword: string;
  job_type: string;
  salary: string;
  time_filter: string;
}

export interface IndeedScrapeParams {
  keyword: string;
  pay: string;
  job_type: string;
  date_posted: string;
}

// ── LinkedIn ──────────────────────────────────────────────────────────────────

export async function startLinkedInScraper(
  params: LinkedInScrapeParams
): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getLinkedInStatus(): Promise<ScraperStatus> {
  const res = await fetch(`${API_BASE}/status`);
  return res.json();
}

export async function getLinkedInJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/jobs`);
  return res.json();
}

export async function clearLinkedInJobs(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/clear`, { method: "DELETE" });
  return res.json();
}

export async function deleteLinkedInJob(id: number): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/${id}`, { method: "DELETE" });
  return res.json();
}

export function exportLinkedInCsvUrl(): string {
  return `${API_BASE}/export/csv`;
}

// ── Startup Jobs ──────────────────────────────────────────────────────────────

export async function startStartupJobsScraper(
  params: StartupJobsScrapeParams
): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape/startupjobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getStartupJobsStatus(): Promise<ScraperStatus> {
  const res = await fetch(`${API_BASE}/status/startupjobs`);
  return res.json();
}

export async function getStartupJobs(): Promise<StartupJob[]> {
  const res = await fetch(`${API_BASE}/jobs/startupjobs`);
  return res.json();
}

export async function clearStartupJobs(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/startupjobs/clear`, { method: "DELETE" });
  return res.json();
}

export function exportStartupJobsCsvUrl(): string {
  return `${API_BASE}/export/startupjobs/csv`;
}

// ── Indeed ────────────────────────────────────────────────────────────────────

export type IndeedJob = Job;

export async function startIndeedScraper(
  params: IndeedScrapeParams
): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape/indeed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getIndeedStatus(): Promise<ScraperStatus> {
  const res = await fetch(`${API_BASE}/status/indeed`);
  return res.json();
}

export async function getIndeedJobs(): Promise<IndeedJob[]> {
  const res = await fetch(`${API_BASE}/jobs/indeed`);
  return res.json();
}

export async function clearIndeedJobs(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/indeed/clear`, { method: "DELETE" });
  return res.json();
}

export function exportIndeedCsvUrl(): string {
  return `${API_BASE}/export/indeed/csv`;
}

// ── Dice ──────────────────────────────────────────────────────────────────────

export type DiceJob = Job;

export interface DiceScrapeParams {
  keyword: string;
  date_posted: string;
  employment_type: string;
}

export async function startDiceScraper(
  params: DiceScrapeParams
): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape/dice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getDiceStatus(): Promise<ScraperStatus> {
  const res = await fetch(`${API_BASE}/status/dice`);
  return res.json();
}

export async function getDiceJobs(): Promise<DiceJob[]> {
  const res = await fetch(`${API_BASE}/jobs/dice`);
  return res.json();
}

export async function clearDiceJobs(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/dice/clear`, { method: "DELETE" });
  return res.json();
}

export function exportDiceCsvUrl(): string {
  return `${API_BASE}/export/dice/csv`;
}

// ── Adzuna ────────────────────────────────────────────────────────────────────

export type AdzunaJob = Job;

export interface AdzunaScrapeParams {
  keyword: string;
  max_days_old: string;
}

export async function startAdzunaScraper(
  params: AdzunaScrapeParams
): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/scrape/adzuna`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function getAdzunaStatus(): Promise<ScraperStatus> {
  const res = await fetch(`${API_BASE}/status/adzuna`);
  return res.json();
}

export async function getAdzunaJobs(): Promise<AdzunaJob[]> {
  const res = await fetch(`${API_BASE}/jobs/adzuna`);
  return res.json();
}

export async function clearAdzunaJobs(): Promise<{ message?: string; detail?: string }> {
  const res = await fetch(`${API_BASE}/jobs/adzuna/clear`, { method: "DELETE" });
  return res.json();
}

export function exportAdzunaCsvUrl(): string {
  return `${API_BASE}/export/adzuna/csv`;
}

// ── Shared ────────────────────────────────────────────────────────────────────

export async function getRuns(): Promise<ScraperRun[]> {
  const res = await fetch(`${API_BASE}/runs`);
  return res.json();
}
