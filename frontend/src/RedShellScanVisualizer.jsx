import { useState, useEffect, useRef, useCallback } from "react";

const STAGES = [
  {
    id: "Provisioning",
    code: "01",
    label: "PROVISIONING",
    sublabel: "Cloning target environment",
    color: "#f59e0b",
    glow: "rgba(245,158,11,0.4)",
    logs: [
      "$ git clone https://github.com/target/repo.git",
      "Cloning into 'repo'...",
      "remote: Enumerating objects: 1,247 done.",
      "remote: Counting objects: 100% (1,247/1,247)",
      "Receiving objects: 100% (1,247/1,247), 4.23 MiB",
      "$ pack build redshell-target:latest --builder heroku/buildpacks:22",
      "===> DETECTING ...",
      "heroku/nodejs (v189) detected",
      "===> BUILDING ...",
      "npm install: installing dependencies...",
      "added 847 packages in 12.4s",
      "===> EXPORTING ...",
      "$ docker network create --driver bridge rs-net-a3f9",
      "a3f9e7c2d1b4...",
      "$ docker run -d --network rs-net-a3f9 --name target redshell-target:latest",
      "Container started: 0xf3a9c1...",
      "Waiting for health check...",
      "GET /health → 200 OK ✓",
      "Target endpoint reachable at 172.18.0.3:3000",
    ],
  },
  {
    id: "Provisioned",
    code: "02",
    label: "PROVISIONED",
    sublabel: "Target environment live",
    color: "#10b981",
    glow: "rgba(16,185,129,0.4)",
    logs: [
      "✓ Container running: 172.18.0.3:3000",
      "✓ Health check passed",
      "✓ Attack payload prepared",
      "✓ Endpoint validated: http://172.18.0.3:3000",
      "Initializing Kali container on rs-net-a3f9...",
      "$ docker run -d --network rs-net-a3f9 kalilinux/kali-rolling",
      "Kali container online: 172.18.0.4",
      "Attack surface mapped. Transitioning...",
    ],
  },
  {
    id: "Attacking",
    code: "03",
    label: "ATTACKING",
    sublabel: "Red team tools deployed",
    color: "#ef4444",
    glow: "rgba(239,68,68,0.5)",
    logs: [
      "[ NMAP ] Starting Nmap 7.94 scan...",
      "Scanning 172.18.0.3 [1000 ports]",
      "PORT     STATE SERVICE VERSION",
      "80/tcp   open  http    nginx 1.24.0",
      "3000/tcp open  http    Node.js Express",
      "8080/tcp open  http    (filtered)",
      "Nmap done: 3 ports discovered",
      "",
      "[ FFUF ] Web fuzzer initializing...",
      "Target: http://172.18.0.3:3000/FUZZ",
      "Wordlist: /usr/share/wordlists/dirb/common.txt",
      ":: /api/v1    [Status: 200, Size: 847]",
      ":: /admin     [Status: 302, Size: 0]",
      ":: /api/users [Status: 403, Size: 12]",
      ":: /.env      [Status: 200, Size: 432] ⚠ CRITICAL",
      ":: /api/debug [Status: 200, Size: 2341] ⚠ HIGH",
      "247 endpoints discovered",
      "",
      "[ NUCLEI ] Template scanner loading...",
      "Loaded 4,821 templates",
      "[CVE-2023-44487] HTTP/2 Rapid Reset → POSITIVE ⚠",
      "[exposure:api-key] AWS key in response → POSITIVE ⚠",
      "[misconfig:cors] Wildcard CORS enabled → POSITIVE",
      "[sqli:error-based] SQLi in /api/search → POSITIVE ⚠",
      "",
      "[ SQLMAP ] SQL injection probing...",
      "GET /api/search?q=* testing...",
      "Parameter 'q' is vulnerable!",
      "Type: error-based (UNION 3 cols)",
      "Database: MySQL 8.0.34",
      "Tables: users, sessions, orders → DUMPED",
    ],
  },
  {
    id: "Normalizing",
    code: "04",
    label: "NORMALIZING",
    sublabel: "Structuring findings",
    color: "#8b5cf6",
    glow: "rgba(139,92,246,0.4)",
    logs: [
      "Parsing raw tool outputs...",
      "Mapping nmap → port exposure schema",
      "Mapping ffuf → endpoint discovery schema",
      "Mapping nuclei → CVE finding schema",
      "Mapping sqlmap → injection schema",
      "Assigning severity scores (CVSS v3.1)...",
      "CVE-2023-44487  → CRITICAL (9.8)",
      ".env exposure    → CRITICAL (9.1)",
      "SQL Injection    → HIGH (8.8)",
      "CORS misconfiguration → MEDIUM (6.5)",
      "API debug endpoint → HIGH (7.2)",
      "Generating finding IDs: RS-001 → RS-028",
      "Validating schema consistency...",
      "✓ 28 findings structured",
      "✓ Schema validation passed",
      "Transitioning to report generation...",
    ],
  },
  {
    id: "Generating_Report",
    code: "05",
    label: "GENERATING REPORT",
    sublabel: "Compiling intelligence",
    color: "#06b6d4",
    glow: "rgba(6,182,212,0.4)",
    logs: [
      "Initializing report generator...",
      "Writing executive summary...",
      "Target: github.com/target/repo",
      "Scan duration: 4m 23s",
      "Total findings: 28",
      "  CRITICAL: 2",
      "  HIGH:     7",
      "  MEDIUM:   11",
      "  LOW:      8",
      "Generating vulnerability sections...",
      "RS-001: SQL Injection in /api/search → written",
      "RS-002: .env file exposed → written",
      "RS-003: HTTP/2 Rapid Reset (CVE-2023-44487) → written",
      "RS-004: Wildcard CORS → written",
      "... 24 more findings documented",
      "Embedding evidence and PoC payloads...",
      "Writing remediation guidance...",
      "Storing report: job:a3f9e7c2:report → Redis ✓",
      "✓ Report generated successfully",
    ],
  },
  {
    id: "Completed",
    code: "06",
    label: "COMPLETED",
    sublabel: "Report ready",
    color: "#22c55e",
    glow: "rgba(34,197,94,0.5)",
    logs: [
      "Stopping attack container...",
      "Stopping target container...",
      "Removing network rs-net-a3f9...",
      "Freeing resources...",
      "✓ All containers stopped",
      "✓ Network removed",
      "✓ Resources freed",
      "",
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
      "  SCAN COMPLETED SUCCESSFULLY",
      "  Job ID: a3f9e7c2d1b4f8e3",
      "  Duration: 4m 23s",
      "  Findings: 28 (2 CRITICAL)",
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
      "",
      "▶ Report available at /report/a3f9e7c2",
    ],
  },
];

const SEVERITY_DATA = [
  { label: "CRITICAL", count: 2, color: "#ef4444" },
  { label: "HIGH", count: 7, color: "#f97316" },
  { label: "MEDIUM", count: 11, color: "#f59e0b" },
  { label: "LOW", count: 8, color: "#3b82f6" },
];

function HexGrid() {
  return (
    <svg
      style={{
        position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
        opacity: 0.04, pointerEvents: "none", zIndex: 0
      }}
    >
      <defs>
        <pattern id="hex" x="0" y="0" width="56" height="48" patternUnits="userSpaceOnUse">
          <polygon
            points="28,4 52,16 52,40 28,52 4,40 4,16"
            fill="none" stroke="#ff2222" strokeWidth="0.8"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#hex)" />
    </svg>
  );
}

function Scanline() {
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
      background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)",
      pointerEvents: "none", zIndex: 1
    }} />
  );
}

function RadarRing({ stage, active }) {
  const rings = [1, 2, 3];
  return (
    <div style={{ position: "relative", width: 180, height: 180 }}>
      {rings.map((r, i) => (
        <div key={r} style={{
          position: "absolute",
          top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          width: 60 * r, height: 60 * r,
          borderRadius: "50%",
          border: `1px solid ${active ? stage.color : "#333"}`,
          opacity: active ? (1 - i * 0.25) : 0.15,
          animation: active ? `radarPulse ${1.5 + i * 0.5}s ease-out infinite` : "none",
          animationDelay: `${i * 0.3}s`,
          transition: "all 0.5s ease",
          boxShadow: active ? `0 0 ${8 + i * 4}px ${stage.glow}` : "none",
        }} />
      ))}
      {/* Sweep line */}
      {active && (
        <div style={{
          position: "absolute", top: "50%", left: "50%",
          width: "50%", height: 1,
          background: `linear-gradient(90deg, transparent, ${stage.color})`,
          transformOrigin: "left center",
          animation: "radarSweep 2s linear infinite",
        }} />
      )}
      {/* Center dot */}
      <div style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%, -50%)",
        width: 8, height: 8, borderRadius: "50%",
        background: active ? stage.color : "#333",
        boxShadow: active ? `0 0 12px ${stage.color}` : "none",
        transition: "all 0.5s",
      }} />
    </div>
  );
}

function TerminalLog({ logs, stageColor }) {
  const bottomRef = useRef(null);
  const [displayedLogs, setDisplayedLogs] = useState([]);
  const [currentLine, setCurrentLine] = useState(0);
  const [currentChar, setCurrentChar] = useState(0);

  useEffect(() => {
    setDisplayedLogs([]);
    setCurrentLine(0);
    setCurrentChar(0);
  }, [logs]);

  useEffect(() => {
    if (currentLine >= logs.length) return;
    const line = logs[currentLine];
    if (currentChar < line.length) {
      const t = setTimeout(() => setCurrentChar(c => c + 1), 18);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => {
        setDisplayedLogs(prev => [...prev, line]);
        setCurrentLine(l => l + 1);
        setCurrentChar(0);
      }, 60);
      return () => clearTimeout(t);
    }
  }, [currentLine, currentChar, logs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayedLogs, currentChar]);

  const currentTyping = currentLine < logs.length ? logs[currentLine].slice(0, currentChar) : null;

  const colorize = (line) => {
    if (line.includes("CRITICAL") || line.includes("⚠ CRITICAL")) return "#ef4444";
    if (line.includes("HIGH") || line.includes("⚠ HIGH")) return "#f97316";
    if (line.includes("MEDIUM")) return "#f59e0b";
    if (line.includes("✓")) return "#22c55e";
    if (line.startsWith("$") || line.startsWith("[")) return stageColor;
    if (line.startsWith("::")) return "#c084fc";
    if (line === "") return "#333";
    if (line.startsWith("━")) return stageColor;
    if (line.includes("COMPLETED")) return "#22c55e";
    return "#94a3b8";
  };

  return (
    <div style={{
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 12,
      lineHeight: "1.7",
      height: 280,
      overflowY: "auto",
      padding: "12px 16px",
      background: "rgba(0,0,0,0.6)",
      border: `1px solid rgba(255,255,255,0.07)`,
      borderTop: `1px solid ${stageColor}33`,
    }}>
      {displayedLogs.map((line, i) => (
        <div key={i} style={{ color: colorize(line), whiteSpace: "pre" }}>
          {line || "\u00A0"}
        </div>
      ))}
      {currentTyping !== null && (
        <div style={{ color: colorize(logs[currentLine] || ""), whiteSpace: "pre" }}>
          {currentTyping}
          <span style={{
            display: "inline-block", width: 7, height: 13,
            background: stageColor, marginLeft: 1,
            animation: "blink 0.7s step-end infinite",
            verticalAlign: "middle",
          }} />
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function StageNode({ stage, status, onClick, isLast }) {
  // status: 'pending' | 'active' | 'done' | 'failed'
  const isDone = status === "done";
  const isActive = status === "active";
  const isPending = status === "pending";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div
        onClick={onClick}
        style={{
          cursor: "pointer",
          display: "flex", flexDirection: "column", alignItems: "center",
          gap: 6,
        }}
      >
        <div style={{
          width: 48, height: 48, borderRadius: "50%",
          border: `2px solid ${isDone ? stage.color : isActive ? stage.color : "#2a2a2a"}`,
          background: isDone ? `${stage.color}22` : isActive ? `${stage.color}15` : "transparent",
          display: "flex", alignItems: "center", justifyContent: "center",
          position: "relative",
          boxShadow: isActive ? `0 0 20px ${stage.glow}, 0 0 40px ${stage.glow}` : isDone ? `0 0 10px ${stage.glow}` : "none",
          transition: "all 0.4s ease",
          animation: isActive ? "activeNodePulse 2s ease-in-out infinite" : "none",
        }}>
          {isDone ? (
            <svg width="18" height="18" viewBox="0 0 18 18">
              <polyline points="3,9 7,13 15,5" fill="none" stroke={stage.color} strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          ) : (
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11, fontWeight: "bold",
              color: isActive ? stage.color : "#444",
              transition: "color 0.3s",
            }}>{stage.code}</span>
          )}
          {isActive && (
            <div style={{
              position: "absolute", inset: -4,
              borderRadius: "50%",
              border: `1px solid ${stage.color}`,
              opacity: 0.5,
              animation: "ripple 1.5s ease-out infinite",
            }} />
          )}
        </div>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, fontWeight: "bold", letterSpacing: "0.12em",
          color: isDone ? stage.color : isActive ? stage.color : "#333",
          textAlign: "center", maxWidth: 72,
          transition: "color 0.3s",
        }}>{stage.label}</span>
      </div>
      {!isLast && (
        <div style={{
          width: 1, height: 32, marginTop: 4,
          background: isDone
            ? `linear-gradient(180deg, ${stage.color}, ${STAGES[STAGES.indexOf(stage) + 1]?.color || stage.color})`
            : "#1a1a1a",
          transition: "background 0.5s",
          position: "relative",
          overflow: "hidden",
        }}>
          {isDone && (
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
              background: "linear-gradient(180deg, transparent, white, transparent)",
              animation: "flowDown 1.5s linear infinite",
              opacity: 0.4,
            }} />
          )}
        </div>
      )}
    </div>
  );
}

function SeverityBar({ item, animate, delay }) {
  const [width, setWidth] = useState(0);
  const max = 11;
  useEffect(() => {
    if (animate) {
      const t = setTimeout(() => setWidth((item.count / max) * 100), delay);
      return () => clearTimeout(t);
    }
  }, [animate, item.count, delay]);

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: item.color, letterSpacing: "0.1em" }}>
          {item.label}
        </span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#666" }}>
          {animate ? item.count : 0}
        </span>
      </div>
      <div style={{ height: 4, background: "#111", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", borderRadius: 2,
          width: `${width}%`,
          background: item.color,
          boxShadow: `0 0 8px ${item.color}`,
          transition: `width 1s cubic-bezier(0.34, 1.56, 0.64, 1)`,
        }} />
      </div>
    </div>
  );
}

export default function RedShellScanVisualizer() {
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [stageStatuses, setStageStatuses] = useState(
    STAGES.map((_, i) => (i === 0 ? "active" : "pending"))
  );
  const [elapsed, setElapsed] = useState(0);
  const [isRunning, setIsRunning] = useState(true);
  const [showReport, setShowReport] = useState(false);
  const timerRef = useRef(null);
  const stageTimerRef = useRef(null);

  const STAGE_DURATIONS = [8000, 3000, 14000, 5000, 5000, 3000];

  const advanceStage = useCallback((idx) => {
    if (idx >= STAGES.length - 1) {
      setStageStatuses(STAGES.map(() => "done"));
      setIsRunning(false);
      setTimeout(() => setShowReport(true), 800);
      return;
    }
    setStageStatuses(prev => {
      const next = [...prev];
      next[idx] = "done";
      next[idx + 1] = "active";
      return next;
    });
    setCurrentStageIdx(idx + 1);
    stageTimerRef.current = setTimeout(() => advanceStage(idx + 1), STAGE_DURATIONS[idx + 1]);
  }, []);

  useEffect(() => {
    stageTimerRef.current = setTimeout(() => advanceStage(0), STAGE_DURATIONS[0]);
    return () => clearTimeout(stageTimerRef.current);
  }, []);

  useEffect(() => {
    if (!isRunning) return;
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, [isRunning]);

  const activeStage = STAGES[currentStageIdx];
  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const handleReset = () => {
    clearTimeout(stageTimerRef.current);
    clearInterval(timerRef.current);
    setCurrentStageIdx(0);
    setStageStatuses(STAGES.map((_, i) => (i === 0 ? "active" : "pending")));
    setElapsed(0);
    setIsRunning(true);
    setShowReport(false);
    stageTimerRef.current = setTimeout(() => advanceStage(0), STAGE_DURATIONS[0]);
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#050505",
      fontFamily: "'JetBrains Mono', monospace",
      position: "relative", overflow: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700;800&family=Bebas+Neue&display=swap');
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes radarPulse { 0%{transform:translate(-50%,-50%) scale(1);opacity:0.8} 100%{transform:translate(-50%,-50%) scale(1.15);opacity:0} }
        @keyframes radarSweep { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes activeNodePulse { 0%,100%{box-shadow:0 0 20px var(--glow), 0 0 40px var(--glow)} 50%{box-shadow:0 0 30px var(--glow), 0 0 60px var(--glow)} }
        @keyframes ripple { 0%{transform:scale(1);opacity:0.8} 100%{transform:scale(2.2);opacity:0} }
        @keyframes flowDown { 0%{transform:translateY(-100%)} 100%{transform:translateY(100%)} }
        @keyframes fadeInUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes glitch { 0%,95%,100%{clip-path:none;transform:none} 96%{clip-path:inset(20% 0 60% 0);transform:translate(-2px,0)} 97%{clip-path:inset(60% 0 10% 0);transform:translate(2px,0)} 98%{clip-path:none;transform:none} }
        @keyframes scanPulse { 0%,100%{opacity:0.6} 50%{opacity:1} }
        @keyframes reportReveal { from{opacity:0;transform:scale(0.96)} to{opacity:1;transform:scale(1)} }
        ::-webkit-scrollbar { width: 4px; background: #0a0a0a; }
        ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 2px; }
      `}</style>

      <HexGrid />
      <Scanline />

      {/* TOP BAR */}
      <div style={{
        position: "relative", zIndex: 10,
        borderBottom: "1px solid #111",
        padding: "12px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(5,5,5,0.95)",
        backdropFilter: "blur(8px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{
            fontFamily: "'Bebas Neue', sans-serif",
            fontSize: 22, color: "#ef4444", letterSpacing: "0.15em",
            textShadow: "0 0 20px rgba(239,68,68,0.5)",
            animation: "glitch 8s infinite",
          }}>REDSHELL</span>
          <span style={{ color: "#2a2a2a", fontSize: 10 }}>|</span>
          <span style={{ color: "#333", fontSize: 10, letterSpacing: "0.1em" }}>
            ENGAGEMENT // <span style={{ color: "#ef4444" }}>a3f9e7c2d1b4f8e3</span>
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 9, color: "#333", letterSpacing: "0.1em" }}>ELAPSED</div>
            <div style={{ fontSize: 16, color: isRunning ? activeStage.color : "#22c55e", fontWeight: "bold" }}>
              {formatTime(elapsed)}
            </div>
          </div>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: isRunning ? "#ef4444" : "#22c55e",
            boxShadow: isRunning ? "0 0 12px #ef4444" : "0 0 12px #22c55e",
            animation: isRunning ? "scanPulse 1s ease-in-out infinite" : "none",
          }} />
          <span style={{ fontSize: 9, color: isRunning ? "#ef4444" : "#22c55e", letterSpacing: "0.15em" }}>
            {isRunning ? "LIVE" : "COMPLETE"}
          </span>
        </div>
      </div>

      {/* TARGET URL BAR */}
      <div style={{
        position: "relative", zIndex: 10,
        padding: "10px 32px",
        borderBottom: "1px solid #0f0f0f",
        background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", gap: 12,
      }}>
        <span style={{ fontSize: 9, color: "#333", letterSpacing: "0.1em" }}>TARGET</span>
        <span style={{ color: "#2a2a2a" }}>→</span>
        <span style={{ fontSize: 11, color: "#64748b" }}>https://github.com/</span>
        <span style={{ fontSize: 11, color: "#94a3b8", fontWeight: "bold" }}>target/repo</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ fontSize: 9, color: "#1a1a1a", letterSpacing: "0.1em" }}>
            {STAGES.filter((_, i) => stageStatuses[i] === "done").length}/{STAGES.length} PHASES
          </span>
        </div>
      </div>

      {/* MAIN LAYOUT */}
      <div style={{
        position: "relative", zIndex: 10,
        display: "grid",
        gridTemplateColumns: "80px 1fr 280px",
        gap: 0,
        height: "calc(100vh - 100px)",
      }}>

        {/* LEFT — STAGE PIPELINE */}
        <div style={{
          borderRight: "1px solid #0f0f0f",
          padding: "32px 0",
          display: "flex", flexDirection: "column", alignItems: "center",
          gap: 0, overflowY: "auto",
          background: "rgba(0,0,0,0.3)",
        }}>
          {STAGES.map((stage, i) => (
            <StageNode
              key={stage.id}
              stage={stage}
              status={stageStatuses[i]}
              isLast={i === STAGES.length - 1}
              onClick={() => {}}
            />
          ))}
        </div>

        {/* CENTER — MAIN DISPLAY */}
        <div style={{
          padding: "28px 32px",
          display: "flex", flexDirection: "column", gap: 20,
          overflowY: "auto",
        }}>

          {/* Stage Header */}
          <div style={{
            animation: "fadeInUp 0.4s ease",
            key: activeStage.id,
          }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 4 }}>
              <span style={{
                fontFamily: "'Bebas Neue', sans-serif",
                fontSize: 40, lineHeight: 1,
                color: activeStage.color,
                textShadow: `0 0 30px ${activeStage.glow}`,
                letterSpacing: "0.08em",
              }}>
                {showReport ? "OPERATION COMPLETE" : activeStage.label}
              </span>
              {!showReport && (
                <span style={{
                  fontSize: 9, color: "#333", letterSpacing: "0.15em",
                  paddingLeft: 8, borderLeft: `1px solid #1a1a1a`,
                }}>
                  PHASE {activeStage.code} / 06
                </span>
              )}
            </div>
            <div style={{ fontSize: 11, color: "#444", letterSpacing: "0.08em" }}>
              {showReport ? "All containers stopped. Report ready." : activeStage.sublabel}
            </div>
          </div>

          {/* Radar + Status Row */}
          {!showReport && (
            <div style={{
              display: "flex", alignItems: "center", gap: 32,
              padding: "20px 24px",
              border: `1px solid ${activeStage.color}22`,
              background: `${activeStage.color}08`,
              borderLeft: `3px solid ${activeStage.color}`,
            }}>
              <RadarRing stage={activeStage} active={true} />
              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 9, color: "#333", letterSpacing: "0.1em", marginBottom: 4 }}>
                    CURRENT OPERATION
                  </div>
                  <div style={{ fontSize: 14, color: activeStage.color, fontWeight: "bold", letterSpacing: "0.05em" }}>
                    {activeStage.sublabel.toUpperCase()}
                  </div>
                </div>
                {/* Progress bar */}
                <div style={{ height: 2, background: "#111", borderRadius: 1, overflow: "hidden" }}>
                  <div style={{
                    height: "100%",
                    background: `linear-gradient(90deg, ${activeStage.color}, ${activeStage.color}88)`,
                    boxShadow: `0 0 8px ${activeStage.color}`,
                    animation: "progressFlow 2s ease-in-out infinite alternate",
                    width: "100%",
                  }} />
                </div>
                <style>{`@keyframes progressFlow { from{opacity:0.4;transform:scaleX(0.3)} to{opacity:1;transform:scaleX(1)} }`}</style>
              </div>
            </div>
          )}

          {/* Terminal */}
          {!showReport && (
            <div>
              <div style={{
                display: "flex", alignItems: "center", gap: 8, padding: "6px 16px",
                background: "#0a0a0a", borderBottom: "1px solid #111",
                borderTop: `1px solid ${activeStage.color}44`,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} />
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#f59e0b" }} />
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e" }} />
                <span style={{ marginLeft: 8, fontSize: 10, color: "#2a2a2a", letterSpacing: "0.1em" }}>
                  kali@redshell-{activeStage.id.toLowerCase()} ~ %
                </span>
                <span style={{ marginLeft: "auto", fontSize: 9, color: activeStage.color, letterSpacing: "0.1em" }}>
                  LIVE OUTPUT
                </span>
              </div>
              <TerminalLog key={activeStage.id} logs={activeStage.logs} stageColor={activeStage.color} />
            </div>
          )}

          {/* REPORT PANEL */}
          {showReport && (
            <div style={{ animation: "reportReveal 0.6s cubic-bezier(0.34,1.56,0.64,1)" }}>
              <div style={{
                border: "1px solid #1a1a1a",
                borderTop: "2px solid #ef4444",
                background: "rgba(0,0,0,0.6)",
                padding: "24px",
              }}>
                {/* Report header */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 9, color: "#333", letterSpacing: "0.15em", marginBottom: 6 }}>
                    SECURITY ASSESSMENT REPORT // RS-2025-a3f9
                  </div>
                  <div style={{ fontSize: 22, color: "#f8fafc", fontFamily: "'Bebas Neue', sans-serif", letterSpacing: "0.1em" }}>
                    TARGET: GITHUB.COM/TARGET/REPO
                  </div>
                  <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
                    <span style={{ fontSize: 10, color: "#444" }}>Duration: 4m 23s</span>
                    <span style={{ color: "#1a1a1a" }}>·</span>
                    <span style={{ fontSize: 10, color: "#444" }}>Scan ID: a3f9e7c2</span>
                    <span style={{ color: "#1a1a1a" }}>·</span>
                    <span style={{ fontSize: 10, color: "#444" }}>28 Findings</span>
                  </div>
                </div>

                {/* Severity summary */}
                <div style={{
                  display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 20,
                }}>
                  {SEVERITY_DATA.map(s => (
                    <div key={s.label} style={{
                      padding: "12px",
                      border: `1px solid ${s.color}33`,
                      background: `${s.color}0a`,
                      textAlign: "center",
                    }}>
                      <div style={{ fontSize: 28, fontFamily: "'Bebas Neue', sans-serif", color: s.color, lineHeight: 1 }}>
                        {s.count}
                      </div>
                      <div style={{ fontSize: 9, color: s.color, letterSpacing: "0.12em", marginTop: 4 }}>
                        {s.label}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Sample finding */}
                <div style={{ borderTop: "1px solid #111", paddingTop: 20 }}>
                  <div style={{ fontSize: 9, color: "#333", letterSpacing: "0.1em", marginBottom: 12 }}>
                    TOP FINDING PREVIEW
                  </div>
                  <div style={{
                    padding: "16px",
                    background: "rgba(239,68,68,0.05)",
                    border: "1px solid rgba(239,68,68,0.2)",
                    borderLeft: "3px solid #ef4444",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                      <span style={{ fontSize: 12, color: "#f8fafc", fontWeight: "bold" }}>
                        RS-001 — SQL Injection in /api/search
                      </span>
                      <span style={{
                        fontSize: 9, padding: "2px 8px",
                        background: "rgba(239,68,68,0.2)", color: "#ef4444",
                        letterSpacing: "0.1em",
                        animation: "scanPulse 2s ease-in-out infinite",
                      }}>
                        CRITICAL
                      </span>
                    </div>
                    <div style={{ fontSize: 10, color: "#555", marginBottom: 10 }}>
                      The parameter 'q' in /api/search is vulnerable to error-based SQL injection allowing full database extraction.
                    </div>
                    <div style={{
                      padding: "8px 12px", background: "#000",
                      border: "1px solid #1a1a1a", fontSize: 10,
                      color: "#22c55e", fontFamily: "monospace",
                    }}>
                      GET /api/search?q=1'+AND+EXTRACTVALUE(1,CONCAT(0x7e,version()))--
                    </div>
                  </div>
                </div>

                {/* CTA */}
                <div style={{ marginTop: 20, display: "flex", gap: 12 }}>
                  <button
                    onClick={handleReset}
                    style={{
                      flex: 1, padding: "12px",
                      background: "transparent",
                      border: "1px solid #ef4444",
                      color: "#ef4444",
                      fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                      letterSpacing: "0.15em", fontWeight: "bold",
                      cursor: "pointer",
                    }}
                  >
                    ↩ RUN NEW SCAN
                  </button>
                  <button style={{
                    flex: 2, padding: "12px",
                    background: "#ef4444",
                    border: "none",
                    color: "#fff",
                    fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                    letterSpacing: "0.15em", fontWeight: "bold",
                    cursor: "pointer",
                    boxShadow: "0 0 20px rgba(239,68,68,0.4)",
                  }}>
                    VIEW FULL REPORT →
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div style={{
          borderLeft: "1px solid #0f0f0f",
          padding: "24px 20px",
          display: "flex", flexDirection: "column", gap: 24,
          overflowY: "auto",
          background: "rgba(0,0,0,0.3)",
        }}>

          {/* Phase status list */}
          <div>
            <div style={{ fontSize: 9, color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 14 }}>
              OPERATION LOG
            </div>
            {STAGES.map((stage, i) => {
              const status = stageStatuses[i];
              return (
                <div key={stage.id} style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "8px 10px", marginBottom: 2,
                  background: status === "active" ? `${stage.color}0a` : "transparent",
                  borderLeft: status === "active" ? `2px solid ${stage.color}` : "2px solid transparent",
                  transition: "all 0.3s",
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                    background: status === "done" ? stage.color : status === "active" ? stage.color : "#1a1a1a",
                    boxShadow: status === "active" ? `0 0 8px ${stage.color}` : "none",
                    animation: status === "active" ? "scanPulse 1s infinite" : "none",
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontSize: 9, letterSpacing: "0.08em", fontWeight: "bold",
                      color: status === "done" ? "#444" : status === "active" ? stage.color : "#222",
                    }}>{stage.label}</div>
                  </div>
                  <div style={{
                    fontSize: 8, letterSpacing: "0.1em",
                    color: status === "done" ? "#22c55e" : status === "active" ? stage.color : "#1a1a1a",
                  }}>
                    {status === "done" ? "✓" : status === "active" ? "●" : "○"}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Severity bars (show when attacking or further) */}
          {(currentStageIdx >= 2 || showReport) && (
            <div>
              <div style={{ fontSize: 9, color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 14 }}>
                FINDINGS SEVERITY
              </div>
              {SEVERITY_DATA.map((item, i) => (
                <SeverityBar
                  key={item.label}
                  item={item}
                  animate={currentStageIdx >= 3 || showReport}
                  delay={i * 200}
                />
              ))}
            </div>
          )}

          {/* System stats */}
          <div>
            <div style={{ fontSize: 9, color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 14 }}>
              SYSTEM TELEMETRY
            </div>
            {[
              ["CONTAINERS", currentStageIdx >= 1 ? "2 ACTIVE" : "0 ACTIVE", currentStageIdx >= 1 ? "#22c55e" : "#333"],
              ["NETWORK", currentStageIdx >= 0 ? "rs-net-a3f9" : "—", "#64748b"],
              ["ENDPOINTS", currentStageIdx >= 2 ? "247 FOUND" : currentStageIdx >= 1 ? "SCANNING..." : "—", currentStageIdx >= 2 ? "#f59e0b" : "#333"],
              ["FINDINGS", currentStageIdx >= 3 ? "28 TOTAL" : currentStageIdx >= 2 ? "ANALYZING..." : "—", currentStageIdx >= 3 ? "#ef4444" : "#333"],
              ["REPORT", showReport ? "READY" : "PENDING", showReport ? "#22c55e" : "#222"],
            ].map(([key, val, color]) => (
              <div key={key} style={{
                display: "flex", justifyContent: "space-between",
                padding: "6px 0",
                borderBottom: "1px solid #0a0a0a",
              }}>
                <span style={{ fontSize: 9, color: "#222", letterSpacing: "0.1em" }}>{key}</span>
                <span style={{ fontSize: 9, color, letterSpacing: "0.08em", fontWeight: "bold" }}>{val}</span>
              </div>
            ))}
          </div>

          {/* Tool status */}
          {currentStageIdx >= 2 && (
            <div>
              <div style={{ fontSize: 9, color: "#2a2a2a", letterSpacing: "0.15em", marginBottom: 14 }}>
                TOOLS DEPLOYED
              </div>
              {[
                ["nmap", currentStageIdx >= 3, "#f59e0b"],
                ["ffuf", currentStageIdx >= 3, "#8b5cf6"],
                ["nuclei", currentStageIdx >= 3, "#06b6d4"],
                ["sqlmap", currentStageIdx >= 3, "#ef4444"],
              ].map(([tool, done, color]) => (
                <div key={tool} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "5px 0", borderBottom: "1px solid #0a0a0a",
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: "50%",
                    background: done ? color : currentStageIdx === 2 ? color : "#1a1a1a",
                    animation: currentStageIdx === 2 && !done ? "scanPulse 1s infinite" : "none",
                    boxShadow: done ? `0 0 6px ${color}` : "none",
                  }} />
                  <span style={{
                    fontSize: 10, color: done ? color : currentStageIdx === 2 ? "#444" : "#1a1a1a",
                    fontWeight: "bold", letterSpacing: "0.05em",
                  }}>{tool}</span>
                  <span style={{ marginLeft: "auto", fontSize: 8, color: done ? "#22c55e" : "#2a2a2a" }}>
                    {done ? "COMPLETE" : currentStageIdx === 2 ? "RUNNING" : "QUEUED"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
