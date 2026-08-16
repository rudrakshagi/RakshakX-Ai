import { VulnerabilityFinding, AgentNode, ScanRecord, PipelineStage } from '../types';

export const INITIAL_FINDINGS: VulnerabilityFinding[] = [
  {
    id: 'VULN-001',
    title: 'Authentication Bypass via JWT Algorithm Confusion',
    category: 'Broken Authentication',
    cwe_id: 'CWE-347',
    cvss_score: 9.8,
    severity: 'critical',
    cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
    endpoint: 'https://example.com/api/v1/auth/verify',
    description: 'The verification endpoint accepts tokens signed with HMAC-SHA256 (HS256) using the public RSA key, allowing arbitrary administrator token forgery.',
    poc: `jwt_tool eyJhbGciOiJSUzI1NiJ9... -X k -pk /workspace/public.pem
curl -i -s -H "Authorization: Bearer eyJhbGciOiJIUzI1Ni..." https://example.com/api/v1/admin/users`,
    remediation_patch: `// Fix: Explicitly enforce RS256 algorithm verification
jwt.verify(token, publicKey, { algorithms: ['RS256'] });`,
    code_locations: [
      {
        file: 'src/middleware/auth.ts',
        start_line: 42,
        end_line: 46,
        snippet: 'const decoded = jwt.verify(token, key); // missing algorithms whitelist'
      }
    ],
    verified: true,
    confidence: 'Verified',
    timestamp: '12 mins ago'
  },
  {
    id: 'VULN-002',
    title: 'Time-Based Blind SQL Injection in Search Endpoint',
    category: 'Injection',
    cwe_id: 'CWE-89',
    cvss_score: 8.6,
    severity: 'high',
    cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N',
    endpoint: 'https://example.com/api/v1/catalog/search?q=electronics',
    description: 'The `q` query parameter is directly concatenated into a raw PostgreSQL query, allowing time-delay payloads to confirm arbitrary database execution.',
    poc: `curl -i -s "https://example.com/api/v1/catalog/search?q=electronics'%20OR%20(SELECT%20pg_sleep(5))--%20-"`,
    remediation_patch: `// Fix: Utilize parameterized prepared statements
const query = 'SELECT * FROM products WHERE name ILIKE $1';
const result = await db.query(query, [\`%\${searchTerm}%\`]);`,
    code_locations: [
      {
        file: 'src/controllers/catalog.controller.ts',
        start_line: 88,
        end_line: 91,
        snippet: 'const sql = `SELECT * FROM items WHERE name ILIKE \'%${q}%\'`;'
      }
    ],
    verified: true,
    confidence: 'Verified',
    timestamp: '28 mins ago'
  },
  {
    id: 'VULN-003',
    title: 'Server-Side Request Forgery (SSRF) via Webhook Importer',
    category: 'Server-Side Request Forgery',
    cwe_id: 'CWE-918',
    cvss_score: 8.2,
    severity: 'high',
    cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N',
    endpoint: 'https://example.com/api/v1/integrations/webhook',
    description: 'Webhook verification fetches remote URLs without validating loopback or cloud metadata IP ranges, enabling AWS IMDSv1 token exfiltration.',
    poc: `curl -X POST "https://example.com/api/v1/integrations/webhook" \\
  -H "Authorization: Bearer $USER_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"target_url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/"}'`,
    remediation_patch: `// Fix: Validate target IP against internal network denylist
if (isPrivateIP(targetIP) || isMetadataIP(targetIP)) {
  throw new Error("Forbidden loopback or metadata destination");
}`,
    verified: true,
    confidence: 'Verified',
    timestamp: '45 mins ago'
  },
  {
    id: 'VULN-004',
    title: 'Race Condition in Single-Use Promo Code Redemption',
    category: 'Broken Business Logic',
    cwe_id: 'CWE-362',
    cvss_score: 6.5,
    severity: 'medium',
    cvss_vector: 'CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:H/A:N',
    endpoint: 'https://example.com/api/v1/coupons/redeem',
    description: 'Non-atomic check-then-act database operation permits parallel burst requests to redeem single-use coupon codes multiple times.',
    poc: `python3 -m rakshak.exploit.race --target "https://example.com/api/v1/coupons/redeem" --code "SAVE50" --concurrency 20`,
    remediation_patch: `// Fix: Enforce database transaction row locking
BEGIN TRANSACTION;
SELECT * FROM coupons WHERE code = $1 AND is_used = false FOR UPDATE;
UPDATE coupons SET is_used = true WHERE code = $1;
COMMIT;`,
    verified: true,
    confidence: 'Verified',
    timestamp: '1 hour ago'
  },
  {
    id: 'VULN-005',
    title: 'Insecure Direct Object Reference (IDOR) on Order Export',
    category: 'Broken Access Control',
    cwe_id: 'CWE-639',
    cvss_score: 6.1,
    severity: 'medium',
    cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N',
    endpoint: 'https://example.com/api/v1/orders/1042/invoice.pdf',
    description: 'Missing tenant boundary check allows authenticated user A to download invoice PDF files belonging to user B by altering the numerical order ID.',
    poc: `curl -s -H "Authorization: Bearer $ATTACKER_TOKEN" "https://example.com/api/v1/orders/1042/invoice.pdf" -o stolen_invoice.pdf`,
    remediation_patch: `// Fix: Verify requester ownership against document tenant
if (invoice.userId !== currentUser.id && !currentUser.isAdmin) {
  return res.status(403).json({ error: "Access denied" });
}`,
    verified: true,
    confidence: 'Verified',
    timestamp: '2 hours ago'
  },
  {
    id: 'VULN-006',
    title: 'Stored Cross-Site Scripting (XSS) in User Profile Bio',
    category: 'Client-Side Attacks',
    cwe_id: 'CWE-79',
    cvss_score: 5.4,
    severity: 'medium',
    cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N',
    endpoint: 'https://example.com/settings/profile',
    description: 'Bio field does not escape HTML entities when rendered in public team view, enabling execution of injected script tags.',
    poc: `agent-browser navigate "https://example.com/users/alice"
agent-browser eval "window.__xss_fired"`,
    remediation_patch: `// Fix: Sanitize rich text markup via DOMPurify before rendering
const cleanHTML = DOMPurify.sanitize(userBio);`,
    verified: true,
    confidence: 'Verified',
    timestamp: '3 hours ago'
  },
  {
    id: 'VULN-007',
    title: 'Missing Content Security Policy (CSP) Frame-Ancestors',
    category: 'Security Misconfiguration',
    cwe_id: 'CWE-1021',
    cvss_score: 3.8,
    severity: 'low',
    cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:L/A:N',
    endpoint: 'https://example.com/login',
    description: 'Missing `Content-Security-Policy: frame-ancestors none` header allows framing of authentication screens in clickjacking attacks.',
    poc: `<iframe src="https://example.com/login" width="500" height="500"></iframe>`,
    remediation_patch: `// Add HTTP Header
Content-Security-Policy: frame-ancestors 'none';
X-Frame-Options: DENY;`,
    verified: true,
    confidence: 'High',
    timestamp: '4 hours ago'
  }
];

export const INITIAL_AGENTS: AgentNode[] = [
  {
    id: 'agent-root',
    name: 'Root Orchestrator',
    role: 'Scope & Task Dispatcher',
    status: 'running',
    task: 'Mapping attack surface and coordinating specialist subagents.',
    parentId: null,
    messagesCount: 18,
    skills: ['scope_analyzer', 'coordinator']
  },
  {
    id: 'agent-recon',
    name: 'Recon & Surface Agent',
    role: 'Endpoint Discovery',
    status: 'completed',
    task: 'Discovered 42 HTTP endpoints, 9 API routes, and 4 auth flows via Katana & FFuF.',
    parentId: 'agent-root',
    messagesCount: 8,
    skills: ['katana_spider', 'ffuf_fuzzer']
  },
  {
    id: 'agent-auth',
    name: 'Authentication Specialist',
    role: 'JWT & Token Security',
    status: 'completed',
    task: 'Tested JWT for algorithm confusion (RS256 to HS256) and verified admin takeover.',
    parentId: 'agent-root',
    messagesCount: 14,
    skills: ['authentication_jwt', 'jwt_tool']
  },
  {
    id: 'agent-sqli',
    name: 'SQLi Prober Specialist',
    role: 'Database Exploitation',
    status: 'completed',
    task: 'Verified time-based blind SQL injection on /api/v1/catalog/search.',
    parentId: 'agent-root',
    messagesCount: 12,
    skills: ['sql_injection', 'sqlmap']
  },
  {
    id: 'agent-race',
    name: 'Concurrency Specialist',
    role: 'Business Logic Testing',
    status: 'running',
    task: 'Executing 20 parallel HTTP/2 burst requests on /api/v1/coupons/redeem.',
    parentId: 'agent-root',
    messagesCount: 6,
    skills: ['race_conditions', 'async_burst']
  }
];

export const RECENT_SCANS: ScanRecord[] = [
  {
    id: 'scan-8821',
    target: 'example.com',
    mode: 'Black Box',
    status: 'Analyzing',
    startTime: 'Today, 11:42 AM',
    duration: '14m 20s',
    endpointsCount: 42,
    findings: { critical: 1, high: 2, medium: 3, low: 1, total: 7 }
  },
  {
    id: 'scan-7740',
    target: 'api.internal.dev',
    mode: 'White Box',
    status: 'Completed',
    startTime: 'Yesterday, 04:15 PM',
    duration: '28m 05s',
    endpointsCount: 68,
    findings: { critical: 2, high: 1, medium: 4, low: 2, total: 9 }
  },
  {
    id: 'scan-6102',
    target: 'auth-gateway.service',
    mode: 'Black Box',
    status: 'Completed',
    startTime: '2 days ago',
    duration: '18m 50s',
    endpointsCount: 19,
    findings: { critical: 0, high: 1, medium: 2, low: 0, total: 3 }
  }
];

export const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'stage-1',
    number: '01',
    title: 'Target Intake',
    summary: 'Scope validation & container initialization',
    details: 'Validates authorization scope, generates isolated Kali Linux Docker container, and starts transparent Caido proxy daemon.',
    tool: 'Docker SDK / Session Manager',
    badge: 'Init'
  },
  {
    id: 'stage-2',
    number: '02',
    title: 'Reconnaissance',
    summary: 'Passive & active asset discovery',
    details: 'Performs DNS enumeration, TLS certificate inspection, and HTTP technology stack fingerprinting.',
    tool: 'Katana / Httpx / Nmap',
    badge: 'Recon'
  },
  {
    id: 'stage-3',
    number: '03',
    title: 'Surface Mapping',
    summary: 'Endpoints, routes & auth flows',
    details: 'Spiders web applications and extracts REST/GraphQL parameters into structured attack surface trees.',
    tool: 'FFuF / Gospider',
    badge: 'Mapping'
  },
  {
    id: 'stage-4',
    number: '04',
    title: 'Specialized Analysis',
    summary: 'Multi-agent tactical delegation',
    details: 'Root Orchestrator delegates specialized subtasks to dedicated subagents (JWT, SQLi, SSRF, IDOR).',
    tool: 'AgentCoordinator',
    badge: 'Multi-Agent'
  },
  {
    id: 'stage-5',
    number: '05',
    title: 'Evidence Collection',
    summary: 'Traffic capture & DOM traces',
    details: 'Records full HTTP request/response pairs through the Caido proxy and captures headless browser DOM screenshots.',
    tool: 'Caido GraphQL / Agent-Browser',
    badge: 'Capture'
  },
  {
    id: 'stage-6',
    number: '06',
    title: 'PoC Verification',
    summary: 'Empirical exploit reproduction',
    details: 'Executes repeatable verification commands. Findings without executable proofs are discarded to guarantee 0% false positives.',
    tool: 'Sandbox Exec / PoC Engine',
    badge: 'Verify'
  },
  {
    id: 'stage-7',
    number: '07',
    title: 'Risk Scoring',
    summary: 'CVSS 3.1 & Hash Deduplication',
    details: 'Calculates exact CVSS 3.1 base score vectors and merges duplicate findings using composite SHA-256 hashing.',
    tool: 'CVSS 3.1 Calculator',
    badge: 'Scoring'
  },
  {
    id: 'stage-8',
    number: '08',
    title: 'Actionable Reporting',
    summary: 'SARIF 2.1.0, PDF & Markdown',
    details: 'Emits standardized OASIS SARIF for GitHub Code Scanning, styled executive PDF reports, and developer remediation diffs.',
    tool: 'SARIF & ReportLab Exporter',
    badge: 'Report'
  }
];
