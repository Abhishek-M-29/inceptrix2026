export const MOCK_STATS = {
  scansRun: 1247,
  vulnsFound: 8931,
  reposTested: 432,
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
