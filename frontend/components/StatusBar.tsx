"use client";

import { ScraperStatus } from "@/lib/api";

export default function StatusBar({ status }: { status: ScraperStatus }) {
  const pct = status.total > 0 ? Math.round((status.scraped / status.total) * 100) : 0;

  return (
    <div className="mt-5 bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center gap-3 mb-3">
        <span
          className={`text-xl ${!status.done ? "animate-spin inline-block" : "text-green-600"}`}
        >
          {status.done ? "✓" : "⧖"}
        </span>
        <span className="font-bold text-gray-800 text-base">{status.progress || "Working..."}</span>
      </div>

      <div className="bg-gray-200 rounded-full h-3 overflow-hidden mb-2">
        <div
          className="h-full bg-gradient-to-r from-blue-600 to-blue-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex justify-between text-sm font-semibold text-gray-500">
        <span>{status.scraped} / {status.total} jobs scraped</span>
        {status.errors.length > 0 && (
          <span className="text-red-600">{status.errors.length} error(s)</span>
        )}
      </div>
    </div>
  );
}
