import type { Report } from '../api/types'

export const MOCK_STATS = {
  scansRun: 1247,
  vulnsFound: 8931,
  reposTested: 432,
}

/* ─── Full Mock Report (matches Report type from api/types) ─── */
/* Used as fallback when backend is unreachable and for the landing page preview */

export const MOCK_REPORT: Report = {
  job_id: 'mock-87779fe6-d3ba-4517-818e-d301cacb6f4c',
  status: 'success',
  target: 'github.com:443',
  sandbox: {
    sandbox_id: 'mock-sandbox-001',
    sandbox_url: 'https://sandbox.redshell.local:3000',
    github_url: 'https://github.com/acme/webapp',
  },
  scan_summary: {
    open_ports: ['22/tcp', '80/tcp', '443/tcp', '3000/tcp', '8080/tcp'],
    services_detected: ['OpenSSH 8.9', 'nginx 1.24.0', 'Node.js Express', 'Jetty 9.4.51'],
    total_findings: 5,
  },
  findings: [
    {
      id: 'F-001',
      title: 'SQL Injection in POST /api/login (username parameter)',
      severity: 'Critical',
      category: 'WSTG-INPV-05',
      tool: 'run_sqlmap_post',
      evidence: '$ sqlmap -u "https://target:3000/api/login" --data="username=admin&password=test" --batch\n\n[INFO] testing parameter: username (POST)\n[INFO] POST parameter \'username\' is vulnerable\n    Type: boolean-based blind\n    Title: AND boolean-based blind - WHERE or HAVING clause\n    Payload: username=admin\' AND 5831=5831--\n\n[INFO] back-end DBMS: PostgreSQL 15.2\n[INFO] current database: \'webapp_prod\'',
      description: 'The login endpoint builds SQL via string interpolation, vulnerable to injection.',
      impact: 'Full database compromise: auth bypass, data exfiltration, potential RCE.',
      remediation: 'Use parameterized queries / prepared statements. Never concatenate user input into SQL.',
    },
    {
      id: 'F-002',
      title: 'Sensitive File Exposure: Exposed .env configuration file at /.env',
      severity: 'High',
      category: 'WSTG-CONF-05',
      tool: 'run_httpx_probe',
      evidence: '$ httpx -u "https://target:3000/.env" -status-code -title\n\nhttps://target:3000/.env [200] [text/plain]\n\nDB_HOST=prod-db.internal\nDB_PASSWORD=s3cret_pr0d!\nJWT_SECRET=eyJhbGciOiJIUz...\nAWS_SECRET_ACCESS_KEY=AKIA...',
      description: 'File /.env is publicly accessible (HTTP 200). Contains sensitive configuration data.',
      impact: 'Database credentials, secrets, and API keys leaked to any unauthenticated attacker.',
      remediation: 'Remove /.env from web root or block access with server-side rules (e.g., nginx deny).',
    },
    {
      id: 'F-003',
      title: 'IDOR: Direct Object Reference on /api/account/:id without authorization',
      severity: 'High',
      category: 'WSTG-ATHN-03',
      tool: 'run_httpx_probe',
      evidence: '$ httpx -u "https://target:3000/api/account/1" -status-code\n[200] {"id":1,"email":"admin@acme.com","role":"admin"}\n\n$ httpx -u "https://target:3000/api/account/2" -status-code\n[200] {"id":2,"email":"jane@acme.com","role":"user"}',
      description: 'Any user\'s account data can be accessed by incrementing the ID parameter without authentication.',
      impact: 'Mass user data exposure. Attacker can enumerate all accounts.',
      remediation: 'Implement server-side authorization: verify the requester owns the requested resource.',
    },
    {
      id: 'F-004',
      title: 'Open Redirect: /redirect?next= accepts arbitrary external URLs',
      severity: 'Medium',
      category: 'WSTG-CLNT-04',
      tool: 'run_httpx_probe',
      evidence: '$ httpx -u "https://target:3000/redirect?next=https://evil.com" -status-code -follow-redirects\n[302] → https://evil.com\n\nRedirect accepted arbitrary external URL without validation.',
      description: 'The /redirect endpoint forwards to any URL without validation.',
      impact: 'Phishing attacks via trusted domain redirect.',
      remediation: 'Validate \'next\' param against an allow-list of trusted domains.',
    },
    {
      id: 'F-005',
      title: 'Exposed SQL backup with credentials at /backup/users.sql',
      severity: 'High',
      category: 'WSTG-CONF-05',
      tool: 'run_httpx_probe',
      evidence: '$ httpx -u "https://target:3000/backup/users.sql" -status-code\n[200] [application/octet-stream]\n\n-- PostgreSQL dump\nCREATE TABLE users (\n  id serial PRIMARY KEY,\n  email varchar(255),\n  password_hash varchar(255)\n);\nINSERT INTO users VALUES (1, \'admin@acme.com\', \'$2b$10$...\');',
      description: 'File /backup/users.sql is publicly accessible (HTTP 200). Contains database dump with credentials.',
      impact: 'Database credentials, user data, and schema leaked to any unauthenticated attacker.',
      remediation: 'Remove /backup/users.sql from web root or block access with server-side rules.',
    },
  ],
  metadata: {
    generated_at: '2026-02-27T23:02:48.622556+00:00',
    agent: 'RedShell v2.0',
    total_steps: 3,
    total_actions: 29,
    elapsed_seconds: 625.7,
  },
  logs: [
    { ts: '2026-02-27T22:52:22.246+00:00', event: 'sandbox_build_started', repo: 'https://github.com/acme/webapp' },
    { ts: '2026-02-27T22:52:22.246+00:00', event: 'tool_started', tool: 'build_sandbox', timeout: 600 },
    { ts: '2026-02-27T22:57:11.180+00:00', event: 'tool_completed', tool: 'build_sandbox', elapsed: 288.9 },
    { ts: '2026-02-27T22:57:11.244+00:00', event: 'tool_started', tool: 'run_nmap', timeout: 120 },
    { ts: '2026-02-27T22:57:38.499+00:00', event: 'tool_completed', tool: 'run_nmap', elapsed: 27.3 },
    { ts: '2026-02-27T22:58:33.504+00:00', event: 'tool_started', tool: 'run_httpx_probe', timeout: 60 },
    { ts: '2026-02-27T22:58:35.061+00:00', event: 'tool_completed', tool: 'run_httpx_probe', elapsed: 1.6 },
    { ts: '2026-02-27T22:58:46.619+00:00', event: 'tool_started', tool: 'run_ffuf_dirs', timeout: 180 },
    { ts: '2026-02-27T22:58:46.724+00:00', event: 'tool_completed', tool: 'run_ffuf_dirs', elapsed: 0.1 },
    { ts: '2026-02-27T22:58:57.143+00:00', event: 'tool_started', tool: 'run_dalfox', timeout: 120 },
    { ts: '2026-02-27T22:59:43.805+00:00', event: 'tool_completed', tool: 'run_dalfox', elapsed: 46.7 },
    { ts: '2026-02-27T22:59:44.287+00:00', event: 'tool_started', tool: 'run_sqlmap_post', timeout: 600 },
    { ts: '2026-02-27T23:02:21.247+00:00', event: 'tool_completed', tool: 'run_sqlmap_post', elapsed: 157.0 },
    { ts: '2026-02-27T23:02:21.247+00:00', event: 'tool_started', tool: 'run_httpx_probe', timeout: 60 },
    { ts: '2026-02-27T23:02:23.257+00:00', event: 'tool_completed', tool: 'run_httpx_probe', elapsed: 2.0 },
  ],
}

export const MOCK_TERMINAL_LINES = [
  '$ redshell --target https://github.com/acme/webapp',
  '[*] Cloning repository...',
  '[*] Detecting buildpack: nodejs@18.x',
  '[+] Container image built: sha256:a4f3b8c...',
  '[*] Deploying to sandbox: 10.0.3.47:3000',
  '[+] Application live. Starting scan suite.',
  '',
  '──── NMAP SCAN ────────────────────────────',
  'Starting Nmap 7.94 ( https://nmap.org )',
  'PORT     STATE SERVICE  VERSION',
  '22/tcp   open  ssh      OpenSSH 8.9',
  '80/tcp   open  http     nginx 1.24.0',
  '443/tcp  open  ssl/http nginx 1.24.0',
  '3000/tcp open  http     Node.js Express',
  '8080/tcp open  http     Jetty 9.4.51',
  '[+] 5 open ports discovered',
  '',
  '──── FFUF FUZZ ───────────────────────────',
  '[Status: 200] [Size: 1243] /api/v1/users',
  '[Status: 200] [Size: 892]  /api/v1/config',
  '[Status: 403] [Size: 162]  /api/v1/admin',
  '[Status: 200] [Size: 2041] /api/v1/debug',
  '[Status: 301] [Size: 0]    /.env',
  '[Status: 200] [Size: 447]  /api/v1/health',
  '[+] 247 endpoints discovered. 12 interesting.',
  '',
  '──── NUCLEI SCAN ─────────────────────────',
  '[critical] exposed-debug-endpoint /api/v1/debug',
  '[high] missing-security-headers (X-Frame-Options)',
  '[high] cors-misconfiguration (Access-Control-*)',
  '[medium] directory-listing /assets/',
  '[medium] outdated-nginx-version 1.24.0',
  '[low] missing-sri-hashes /static/app.js',
  '[info] tech-detect: Node.js, Express, React',
  '[+] 28 vulnerabilities found',
  '',
  '──── SQLMAP PROBE ─────────────────────────',
  '[*] Testing parameter: id (GET /api/v1/users?id=1)',
  '[+] VULNERABLE: Boolean-based blind SQL injection',
  '[+] Payload: id=1 AND 1=1--',
  '[*] Database: PostgreSQL 15.2',
  '[+] 1 SQL injection point confirmed',
  '',
  '[★] SCAN COMPLETE. 28 findings. Report generated.',
]

export const PIPELINE_PHASES = [
  {
    number: '01',
    title: 'ACQUIRE',
    description: 'Paste your public GitHub repo URL. No credentials, no installs, no configuration.',
    icon: 'crosshair',
  },
  {
    number: '02',
    title: 'PROVISION',
    description: 'We replicate your production environment. Your code runs exactly as deployed.',
    icon: 'container',
  },
  {
    number: '03',
    title: 'ATTACK',
    description: 'nmap. ffuf. nuclei. sqlmap. A full automated red-team runs against your live application.',
    icon: 'lightning',
  },
  {
    number: '04',
    title: 'REPORT',
    description: 'Every vulnerability documented. Every finding actionable. Delivered as a clean security report.',
    icon: 'document',
  },
]

/* ─── Arsenal (Section D) ─── */

export const ARSENAL_TOOLS = [
  {
    name: 'nmap',
    description: 'Network reconnaissance and port scanning. Maps your attack surface before anything fires.',
    icon: 'sonar',
  },
  {
    name: 'ffuf',
    description: 'High-speed web fuzzer for directory and endpoint discovery. Finds what shouldn\'t be findable.',
    icon: 'fuzz',
  },
  {
    name: 'nuclei',
    description: 'Template-based vulnerability scanner. Checks for thousands of known CVEs and misconfigurations.',
    icon: 'atom',
  },
  {
    name: 'sqlmap',
    description: 'Automated SQL injection detection and exploitation. Tests every input that touches a database.',
    icon: 'syringe',
  },
  {
    name: 'Kali Linux',
    description: 'The entire attack suite runs from an isolated Kali container — the industry standard for offensive security.',
    icon: 'kali',
  },
]

/* ─── Report Preview (Section E) ─── */

export const MOCK_REPORT_FINDING = {
  title: 'Boolean-Based Blind SQL Injection',
  severity: 'CRITICAL' as const,
  evidence: [
    '$ sqlmap -u "https://target:3000/api/v1/users?id=1" --batch',
    '',
    '[*] testing parameter: id (GET)',
    '[+] parameter \'id\' is vulnerable',
    '    Type: boolean-based blind',
    '    Title: AND boolean-based blind - WHERE or HAVING clause',
    '    Payload: id=1 AND 5831=5831',
    '',
    '[+] back-end DBMS: PostgreSQL 15.2',
    '[+] current database: \'webapp_prod\'',
    '[*] dumped 247 rows from \'users\' table',
  ],
  impact:
    'An unauthenticated attacker can extract the entire database contents including user credentials, session tokens, and PII. This allows full account takeover and data exfiltration.',
  remediation:
    'Use parameterised queries or prepared statements for all database interactions. Never concatenate user input into SQL strings. Apply an ORM layer and enable WAF SQL injection rule sets.',
}

export const SEVERITY_BREAKDOWN = [
  { label: 'Critical', count: 2, color: '#FF3B3B', maxRatio: 0.15 },
  { label: 'High', count: 5, color: '#FF6B35', maxRatio: 0.36 },
  { label: 'Medium', count: 11, color: '#FFB800', maxRatio: 0.79 },
  { label: 'Low', count: 8, color: '#00B8D4', maxRatio: 0.57 },
  { label: 'Info', count: 14, color: '#3A4468', maxRatio: 1.0 },
]

/* ─── Status Timeline (Section F) ─── */

export const STATUS_PHASES = [
  {
    status: 'QUEUED',
    label: 'Job received',
    detail: 'Engagement ID assigned: RS-2026-04821',
  },
  {
    status: 'PROVISIONING',
    label: 'Building environment',
    detail: 'Cloning repo… Building container… Detecting ports…',
  },
  {
    status: 'DEPLOYED',
    label: 'Application live',
    detail: 'Target live at 10.0.3.47:3000 — Kali container launching…',
  },
  {
    status: 'ATTACKING',
    label: 'Red team active',
    detail: 'Running nmap… ffuf sweep complete (247 endpoints)… nuclei scanning… sqlmap probing…',
  },
  {
    status: 'REPORT READY',
    label: 'Scan complete',
    detail: '28 findings documented. Click to view your report.',
  },
]
