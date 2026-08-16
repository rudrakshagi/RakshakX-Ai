import { PlaybookItem } from '../types';

export const PLAYBOOKS_CATALOG: PlaybookItem[] = [
  {
    id: 'playbook-jwt',
    name: 'Authentication & JWT Security',
    filename: 'authentication_jwt.md',
    category: 'Broken Authentication',
    description: 'Specialized playbook for algorithm confusion (RS256 to HS256), none algorithm attacks, weak HMAC secret cracking, and kid path traversal.',
    attackVectors: ['Algorithm Confusion', 'None Algorithm', 'Weak Secret Cracking', 'Key ID Traversal'],
    status: 'Active'
  },
  {
    id: 'playbook-sqli',
    name: 'SQL Injection & Database Exploitation',
    filename: 'sql_injection.md',
    category: 'Injection',
    description: 'Systematic testing for boolean-based blind, time-based sleep delays, error-based extraction, and automated SQLmap proxy extraction.',
    attackVectors: ['Time-Based Blind', 'Boolean Blind', 'Error-Based', 'SQLMap Proxy Bridging'],
    status: 'Active'
  },
  {
    id: 'playbook-idor',
    name: 'Insecure Direct Object References (IDOR/BOLA)',
    filename: 'idor.md',
    category: 'Broken Access Control',
    description: 'Multi-account tenant boundary testing, sequential integer fuzzing, UUID guessing, and HTTP method mutation.',
    attackVectors: ['Multi-User Probing', 'Parameter Tampering', 'Method Mutation', 'UUID Probing'],
    status: 'Active'
  },
  {
    id: 'playbook-ssrf',
    name: 'Server-Side Request Forgery (SSRF)',
    filename: 'ssrf.md',
    category: 'Server-Side Request Forgery',
    description: 'Cloud metadata service exfiltration (AWS IMDSv1/v2, GCP, Azure), loopback address bypasses (octal, decimal, IPv6), and DNS rebinding.',
    attackVectors: ['AWS IMDSv1/v2', 'GCP Metadata', 'DNS Rebinding', 'Loopback Bypasses'],
    status: 'Active'
  },
  {
    id: 'playbook-race',
    name: 'Race Conditions & Concurrency Flaws',
    filename: 'race_conditions.md',
    category: 'Broken Business Logic',
    description: 'HTTP/2 single-packet burst testing, async Python flood scripts, single-use coupon double redemption, and balance double-spending.',
    attackVectors: ['HTTP/2 Single-Packet Attack', 'Burst Async Fuzzing', 'Coupon Reuse', 'Balance Race'],
    status: 'Active'
  },
  {
    id: 'playbook-xss',
    name: 'Cross-Site Scripting & DOM Exploitation',
    filename: 'xss.md',
    category: 'Client-Side Attacks',
    description: 'Reflected, Stored, and DOM-based XSS probing with headless Chromium browser validation, CSP filter bypasses, and cookie exfiltration.',
    attackVectors: ['DOM XSS', 'Stored XSS', 'CSP Bypasses', 'Chromium Flag Evaluation'],
    status: 'Active'
  },
  {
    id: 'playbook-rce',
    name: 'Remote Code Execution & Command Injection',
    filename: 'rce.md',
    category: 'Server-Side Execution',
    description: 'Shell metacharacter injection, blind time-delay execution, polyglot web shell uploads, and deserialization exploit vectors.',
    attackVectors: ['Command Separators', 'Blind Sleep Injections', 'Polyglot Web Shells', 'Deserialization'],
    status: 'Active'
  }
];
