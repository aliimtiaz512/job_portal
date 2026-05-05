"use client";

import { ScraperStatus } from "@/lib/api";

export default function StatusBar({ status }: { status: ScraperStatus }) {
  const pct = status.total > 0 ? Math.round((status.scraped / status.total) * 100) : 0;

  return (
    <div className="mt-5 bg-gray-50 border border-gray-200 rounded-xl p-4">
      <div className="flex items-center gap-3 mb-3">
        <span
          className={`text-lg ${!status.done ? "animate-spin inline-block" : "text-green-600"}`}
        >
          {status.done ? "✓" : "⧖"}
        </span>
        <span className="font-semibold text-gray-700">{status.progress || "Working..."}</span>
      </div>

      <div className="bg-gray-200 rounded-full h-2 overflow-hidden mb-2">
        <div
          className="h-full bg-blue-600 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex justify-between text-xs text-gray-500">
        <span>{status.scraped} / {status.total} jobs scraped</span>
        {status.errors.length > 0 && (
          <span className="text-red-600">{status.errors.length} error(s)</span>
        )}
      </div>
    </div>
  );
}
