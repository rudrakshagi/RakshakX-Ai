export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface CodeLocation {
  file: string;
  start_line: number;
  end_line: number;
  snippet: string;
}

export interface VulnerabilityFinding {
  id: string;
  title: string;
  category: string;
  cwe_id: string;
  cvss_score: number;
  severity: SeverityLevel;
  cvss_vector: string;
  endpoint: string;
  description: string;
  poc: string;
  remediation_patch: string;
  code_locations?: CodeLocation[];
  verified: boolean;
  confidence: 'High' | 'Verified' | 'Probable';
  timestamp?: string;
}

export interface AgentNode {
  id: string;
  name: string;
  role: string;
  status: 'running' | 'completed' | 'waiting' | 'idle';
  task: string;
  parentId?: string | null;
  messagesCount: number;
  skills: string[];
}

export interface ScanRecord {
  id: string;
  target: string;
  mode: 'Black Box' | 'White Box';
  status: 'Analyzing' | 'Completed' | 'Queued' | 'Stopped';
  startTime: string;
  duration: string;
  endpointsCount: number;
  findings: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  };
}

export interface PlaybookItem {
  id: string;
  name: string;
  filename: string;
  category: string;
  description: string;
  attackVectors: string[];
  status?: string;
}

export interface PipelineStage {
  id: string;
  number: string;
  badge: string;
  title: string;
  summary: string;
  details: string;
  tool: string;
  outputArtifact?: string;
}

export interface ChildWorkerProcess {
  pid: number;
  name: string;
  status: string;
  cpu_percent: number;
  memory_mb: number;
}

export interface SystemTelemetry {
  timestamp?: number;
  backend: {
    status: string;
    port: number;
    pid?: number;
    latency_ms: number;
    uptime: string;
    python_version: string;
    os: string;
    process_memory_mb?: number;
    process_cpu_percent?: number;
    active_threads?: number;
  };
  child_workers?: ChildWorkerProcess[];
  mcp_bridge: {
    status: string;
    protocol: string;
    supported_tools: string[];
    clients: string[];
  };
  sandbox: {
    status: string;
    container: string;
    proxy_port: number;
    tools_installed: string[];
  };
  resources: {
    cpu_percent: number;
    ram_used_gb: number;
    ram_total_gb: number;
    ram_percent: number;
  };
}
