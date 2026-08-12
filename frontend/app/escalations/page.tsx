"use client";

import { useEffect, useState } from "react";

type Escalation = {
  reference_id: string;
  created_at: string;
  user_id: string;
  reason: string;
  what_happened: string;
  what_was_checked: string;
  urgency: string;
  caller_language: string;
  preferred_follow_up: string;
  status: string;
};

export default function EscalationsPage() {
  const [requests, setRequests] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRequests() {
      try {
        const response = await fetch("/api/escalations", {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Failed to load requests");
        }

        const data = await response.json();
        setRequests(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    loadRequests();

    const interval = setInterval(loadRequests, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f5f7fb",
        padding: "40px",
        fontFamily: "Arial, sans-serif",
        color: "#111827",
      }}
    >
      <div
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            background: "#111827",
            color: "white",
            padding: "28px",
            borderRadius: "16px",
            marginBottom: "24px",
          }}
        >
          <h1
            style={{
              margin: 0,
              fontSize: "32px",
            }}
          >
            BharatMoney Human Help
          </h1>

          <p
            style={{
              marginTop: "8px",
              marginBottom: 0,
              color: "#d1d5db",
            }}
          >
            Open escalation requests from BharatMoney Voice AI
          </p>
        </div>

        <div
          style={{
            background: "white",
            padding: "20px",
            borderRadius: "14px",
            marginBottom: "24px",
            border: "1px solid #e5e7eb",
          }}
        >
          <strong>Open Requests: </strong>
          {requests.filter((request) => request.status === "OPEN").length}
        </div>

        {loading ? (
          <div
            style={{
              background: "white",
              padding: "30px",
              borderRadius: "14px",
            }}
          >
            Loading requests...
          </div>
        ) : requests.length === 0 ? (
          <div
            style={{
              background: "white",
              padding: "30px",
              borderRadius: "14px",
            }}
          >
            No human-help requests yet.
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gap: "20px",
            }}
          >
            {requests
              .slice()
              .reverse()
              .map((request) => (
                <div
                  key={request.reference_id}
                  style={{
                    background: "white",
                    borderRadius: "16px",
                    padding: "24px",
                    border: "1px solid #e5e7eb",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "20px",
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontSize: "14px",
                          color: "#6b7280",
                        }}
                      >
                        Reference ID
                      </div>

                      <div
                        style={{
                          fontSize: "24px",
                          fontWeight: "700",
                          marginTop: "4px",
                        }}
                      >
                        {request.reference_id}
                      </div>
                    </div>

                    <div
                      style={{
                        padding: "8px 14px",
                        borderRadius: "999px",
                        background:
                          request.urgency.toLowerCase() === "high"
                            ? "#fee2e2"
                            : "#fef3c7",
                        color:
                          request.urgency.toLowerCase() === "high"
                            ? "#991b1b"
                            : "#92400e",
                        fontWeight: "700",
                      }}
                    >
                      {request.urgency} Priority
                    </div>

                    <div
                      style={{
                        padding: "8px 14px",
                        borderRadius: "999px",
                        background: "#dcfce7",
                        color: "#166534",
                        fontWeight: "700",
                      }}
                    >
                      {request.status}
                    </div>
                  </div>

                  <hr
                    style={{
                      border: 0,
                      borderTop: "1px solid #e5e7eb",
                      margin: "20px 0",
                    }}
                  />

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(250px, 1fr))",
                      gap: "18px",
                    }}
                  >
                    <Info
                      label="Reason"
                      value={request.reason}
                    />

                    <Info
                      label="What happened"
                      value={request.what_happened}
                    />

                    <Info
                      label="What the agent checked"
                      value={request.what_was_checked}
                    />

                    <Info
                      label="Caller language"
                      value={request.caller_language}
                    />

                    <Info
                      label="Preferred follow-up"
                      value={request.preferred_follow_up}
                    />

                    <Info
                      label="Created"
                      value={new Date(
                        request.created_at
                      ).toLocaleString()}
                    />
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </main>
  );
}

function Info({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div
        style={{
          fontSize: "13px",
          color: "#6b7280",
          marginBottom: "5px",
          fontWeight: "600",
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: "15px",
          lineHeight: "1.5",
        }}
      >
        {value || "Not provided"}
      </div>
    </div>
  );
}