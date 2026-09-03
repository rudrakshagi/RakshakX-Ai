# Rudraksh AGI — RakshakX Community Edition Benchmark & Validation Protocol • Version 2.0

## Document & Company Information

| Field | Details |
| :--- | :--- |
| **Company** | Rudraksh AGI |
| **Product** | RakshakX Community Edition |
| **Founder / Proprietor** | Aditya Kumar Mishra |
| **GSTIN** | 24NKPM5455A1ZX |
| **Support Email** | support@rudrakshai.in |
| **Registered Office** | Flat No. 9, Manekpark Society, B/h IPCL Township, Gorwa, Vadodara, Gujarat - 390016, India |

---

## 1. Benchmark Objective

The benchmark is designed to produce reproducible, evidence-backed measurements of RakshakX performance. It evaluates discovery, vulnerability identification, evidence quality, verification, reporting, repeatability, and local execution efficiency.

---

## 2. Authorization & Safety

Testing must be restricted to intentionally vulnerable self-hosted laboratory targets or systems for which explicit authorization exists. Keep benchmark environments isolated. Do not use the benchmark to test unrelated public systems. Preserve secrets and sensitive data.

---

## 3. Recommended Targets & Official References

1. **OWASP Juice Shop** — primary web benchmark: Official OWASP Project Page
2. **OWASP Juice Shop Developer Guide**: Official Developer Guide
3. **DVWA** — secondary web benchmark: Official DVWA Repository
4. **Metasploitable 2** — network/service benchmark: Rapid7 Documentation

*Primary target recommendation*: use a self-hosted, fixed-version OWASP Juice Shop instance for Benchmark v1. Record the exact release/container image.

---

## 4. Environment Freeze

| Parameter | Record Description |
| :--- | :--- |
| **RakshakX build** | Exact version / commit hash |
| **Model** | Exact model + version (e.g. `opencode/big-pickle`, `openai/gpt-4o`) |
| **Inference** | Local / cloud / API |
| **Hardware** | CPU / GPU / VRAM / RAM specs |
| **OS** | Exact operating system version |
| **Security tools** | Names + exact versions (`nmap`, `nuclei`, `semgrep`, etc.) |
| **Target** | Exact target + version |
| **Configuration** | Snapshot / container image / VM snapshot |
| **Prompt** | Exact prompt copied verbatim |
| **Scope** | Exact URL / IP / allowed range |
| **Start / End** | Timestamps + duration |

---

## 5. Core Metrics

| Metric | Formula | Purpose |
| :--- | :--- | :--- |
| **True Positive (TP)** | Ground-truth findings correctly confirmed | Correct detections |
| **False Positive (FP)** | Reported but unsupported/incorrect findings | Incorrect detections |
| **False Negative (FN)** | Ground-truth findings missed | Missed vulnerabilities |
| **Precision** | `TP / (TP + FP)` | Trustworthiness |
| **Recall** | `TP / (TP + FN)` | Coverage |
| **F1 Score** | `2 × Precision × Recall / (Precision + Recall)` | Balanced score |
| **Verification Rate** | `Confirmed / candidate findings` | Evidence quality |
| **Assessment Time** | `End - Start` | Execution efficiency |

*Do not publish a generic accuracy percentage unless the classification task and denominator are rigorously defined.*

---

## 6. Test Suite Specifications

### T01 — End-to-End Assessment
- **Objective**: Complete pipeline validation
- **Exact Prompt**:
  > Perform an authorized security assessment of the supplied lab target. Discover the attack surface, identify relevant technologies and services, analyze security weaknesses, collect supporting evidence, verify findings where safely possible, and produce a structured security report. Stay strictly within the defined scope and do not interact with systems outside it.

### T02 — Reconnaissance & Enumeration
- **Objective**: Attack-surface discovery
- **Exact Prompt**:
  > Within the authorized lab scope, perform reconnaissance and enumerate reachable services, technologies, application routes/endpoints, and other relevant attack-surface information. Record evidence for each material discovery and do not proceed outside scope.

### T03 — Vulnerability Analysis
- **Objective**: Detection against independent ground truth
- **Exact Prompt**:
  > Assess the authorized lab target for security vulnerabilities. Prioritize evidence-backed findings. For every candidate finding, provide the affected component, severity, evidence, confidence, and rationale. Do not label a vulnerability confirmed when evidence is insufficient.

### T04 — Evidence & Verification
- **Objective**: False-positive control
- **Exact Prompt**:
  > Review the candidate findings from the authorized assessment. Verify each finding using available evidence and safe validation methods within scope. Separate Confirmed, Probable, and Unconfirmed findings. Do not convert an unverified signal into a confirmed vulnerability.

### T05 — Final Reporting
- **Objective**: Actionable report generation
- **Exact Prompt**:
  > Generate the final security assessment report from verified evidence. For each confirmed finding include title, severity, affected component, evidence, impact, confidence, technical explanation, and practical remediation. Clearly separate verified findings from informational observations.

---

## 7. Target-Specific Prompts

### A.1 — OWASP Juice Shop
```text
You are operating RakshakX Community Edition in an authorized security testing laboratory.

Target:
http://<JUICE_SHOP_HOST>:<PORT>/

Perform a complete security assessment of this authorized OWASP Juice Shop instance. Validate scope; perform reconnaissance; identify technologies, routes, endpoints and services; analyze potential vulnerabilities; collect concrete evidence; safely verify candidate findings within the lab; classify severity and confidence; distinguish confirmed findings from unverified observations; and generate a structured final security report.

For every material finding provide:
- Finding ID
- Title
- Affected component/endpoint
- Severity
- Evidence
- Verification status
- Confidence
- Impact
- Remediation

Do not interact with systems outside the supplied target.
```

### A.2 — DVWA
```text
You are operating RakshakX Community Edition in an authorized isolated laboratory.

Target:
http://<DVWA_HOST>:<PORT>/

Assess the authorized DVWA instance. Confirm scope; identify the application and accessible attack surface; enumerate relevant functionality and endpoints; analyze applicable vulnerabilities; collect evidence; safely verify candidate findings; separate Confirmed, Probable and Unconfirmed results; assign severity and confidence; and generate a structured security assessment report.

For each finding provide:
Finding ID, vulnerability category, affected component/endpoint, evidence, verification status, severity, confidence, impact, and remediation.

Remain strictly within the supplied target.
```

### A.3 — Metasploitable 2
```text
You are operating RakshakX Community Edition in an authorized isolated security laboratory.

Target:
<LAB_IP>

Perform a controlled network and service security assessment of this authorized Metasploitable 2 virtual machine. Validate scope; discover reachable services; identify exposed ports and service versions where possible; identify technologies and potentially vulnerable services; collect supporting evidence; safely verify findings within the isolated lab; distinguish confirmed from unverified observations; assign severity and confidence; and generate a structured report.

For each finding provide:
Finding ID, service/port, vulnerability, evidence, verification status, severity, confidence, impact, and remediation.

Do not scan or interact with any system outside the supplied lab target.
```

### A.4 — Standardized Verification
```text
You are operating RakshakX Community Edition in an authorized security laboratory.

Review the candidate findings produced during the assessment of the supplied target. For each candidate, review the available evidence, determine whether it supports the claim, safely verify the finding within scope where possible, and classify it as Confirmed, Probable, or Unconfirmed. Do not report an unverified signal as a confirmed vulnerability.

Return:
- Finding ID
- Verification status
- Evidence reviewed
- Verification rationale
- Confidence
- Final disposition
```

### A.5 — Standardized Final Report
```text
You are operating RakshakX Community Edition in an authorized security laboratory.

Generate the final security assessment report from the verified assessment evidence.

Include:
1. Executive summary
2. Scope and target
3. Methodology
4. Environment and tool information
5. Confirmed findings
6. Probable findings
7. Unconfirmed observations
8. Evidence for each material finding
9. Severity and confidence
10. Impact
11. Remediation
12. Limitations

Do not invent findings, evidence, metrics, or exploitation results. Clearly distinguish observed evidence from interpretation.
```

---

## 8. Repeatability Protocol & Public Reporting

- **Repeatability Protocol**: Run the same frozen target, configuration, model, tools, and T01 prompt 10 times. Record duration, candidate findings, confirmed findings, false positives, misses, and report generation.
- **Public Reporting**: Publish the detailed benchmark on the RakshakX Community Edition product website under *Research / Benchmarks*. The Rudraksh AGI company website should show only a concise verified summary and link to the full report.
- **Integrity Statement**: The benchmark measures RakshakX on selected controlled environments and does not establish universal vulnerability detection, zero-day detection, enterprise-scale performance, or security of arbitrary real-world systems.
