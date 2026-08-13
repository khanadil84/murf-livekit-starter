"use client";

import { useEffect, useState } from "react";

type AnalyticsRecord = {
  call_id: string;
  started_at: string;
  ended_at: string;
  outcome: "successful" | "failed";
};

export default function AnalyticsPage() {
  const [records, setRecords] = useState<AnalyticsRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("/api/analytics", {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Failed to load analytics");
      }

      const data = await response.json();
      setRecords(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError("Unable to load call analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();

    const interval = setInterval(loadAnalytics, 5000);

    return () => clearInterval(interval);
  }, []);

  const totalCalls = records.length;
  const successfulCalls = records.filter(
    (record) => record.outcome === "successful"
  ).length;
  const failedCalls = records.filter(
    (record) => record.outcome === "failed"
  ).length;

  const cards = [
    {
      title: "Total Calls",
      value: totalCalls,
      description: "All recorded calls",
    },
    {
      title: "Successful Calls",
      value: successfulCalls,
      description: "Calls that reached the success condition",
    },
    {
      title: "Failed Calls",
      value: failedCalls,
      description: "Calls that did not reach the success condition",
    },
  ];

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-cyan-400">
            BharatMoney Voice AI
          </p>

          <h1 className="text-4xl font-bold tracking-tight">
            Call Analytics Dashboard
          </h1>

          <p className="mt-3 max-w-2xl text-slate-400">
            Real-time performance metrics from actual voice-agent calls.
          </p>
        </div>

        {loading && records.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-400">
            Loading call analytics...
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-900 bg-red-950/40 p-8 text-center text-red-300">
            {error}
          </div>
        ) : (
          <>
            <section className="grid gap-6 md:grid-cols-3">
              {cards.map((card) => (
                <div
                  key={card.title}
                  className="rounded-2xl border border-slate-800 bg-slate-900 p-7 shadow-xl"
                >
                  <p className="text-sm font-medium text-slate-400">
                    {card.title}
                  </p>

                  <p className="mt-4 text-5xl font-bold">{card.value}</p>

                  <p className="mt-3 text-sm text-slate-500">
                    {card.description}
                  </p>
                </div>
              ))}
            </section>

            <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-7">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Call Performance</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Dashboard refreshes automatically every 5 seconds.
                  </p>
                </div>

                <button
                  onClick={loadAnalytics}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-800"
                >
                  Refresh
                </button>
              </div>

              <div className="mt-6 h-3 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full bg-cyan-500 transition-all duration-500"
                  style={{
                    width:
                      totalCalls > 0
                        ? `${(successfulCalls / totalCalls) * 100}%`
                        : "0%",
                  }}
                />
              </div>

              <div className="mt-3 flex justify-between text-sm text-slate-500">
                <span>
                  Success rate:{" "}
                  {totalCalls > 0
                    ? `${Math.round((successfulCalls / totalCalls) * 100)}%`
                    : "0%"}
                </span>

                <span>{totalCalls} recorded calls</span>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}