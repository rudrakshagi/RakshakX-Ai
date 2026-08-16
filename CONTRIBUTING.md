# Contributing to RakshakX

Thank you for your interest in contributing to **RakshakX**! We are committed to building the most capable, empirical, and developer-friendly autonomous AI penetration testing engine.

---

## 🛠️ Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/rakshakx/rakshakx.git
   cd rakshakx
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies in Editable Mode**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Build the Sandbox Docker Image**:
   ```bash
   docker build -t rakshakx/sandbox:latest -f containers/Dockerfile .
   ```

---

## 🧪 Running Tests & Code Quality

Before opening a pull request, ensure all tests and linting passes:

```bash
# Run pytest suite
pytest tests/

# Type checking
mypy rakshak/

# Code formatting & linting
ruff check rakshak/
ruff format rakshak/
```

---

## 🛡️ Adding a New Vulnerability Playbook (Skill)

We encourage contributions of new offensive skills and vulnerability methodologies:

1. Create a markdown playbook in `rakshak/skills/vulnerabilities/<vulnerability_name>.md`.
2. Follow the standard 4-part structure:
   - **Overview & Attack Surface**: Root cause, parameters, headers.
   - **Detection & Heuristic Probing**: Initial fuzzing patterns.
   - **Exploitation & Verification**: Exact commands/scripts to run in sandbox.
   - **Verification & Reporting**: CWE ID, CVSS 3.1 metrics, and remediation guidance.

---

## 📜 Pull Request Process

1. Create a branch: `git checkout -b feature/my-enhancement`.
2. Keep commits descriptive and atomic.
3. Open a Pull Request on GitHub describing what was added/fixed and test evidence.
