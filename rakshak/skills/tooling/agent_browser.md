# Offensive Tool Guide: Headless Agent Browser Automation

## 1. Overview
The sandbox container includes `agent-browser` (Chromium with stealth flags, custom Root CA trust, and auto-screenshot capture). Agents invoke `agent-browser` via shell `exec_command` to explore client-side apps, test DOM XSS, clickjacking, and multi-step authentication workflows.

## 2. Common CLI Commands

### Navigation & Screenshots
```bash
# Navigate to URL
agent-browser navigate "https://target.local/login"

# Capture screenshot (saved to /workspace/.agent-browser-screenshots/)
agent-browser screenshot --output /workspace/.agent-browser-screenshots/login.png
```

### Form Interaction & Clicking
```bash
# Fill input field
agent-browser fill "#username" "admin"
agent-browser fill "#password" "password123"

# Click element
agent-browser click "button[type='submit']"

# Wait for selector or navigation
agent-browser wait "#dashboard" --timeout 5000
```

### JavaScript Evaluation & DOM Inspection
```bash
# Extract cookies or local storage
agent-browser eval "document.cookie"
agent-browser eval "localStorage.getItem('auth_token')"

# Check for client-side XSS execution flag
agent-browser eval "window.__xss_fired"
```

## 3. Best Practices for Agents
1. Always take a screenshot before and after submitting complex auth forms.
2. Check Caido proxy (`list_requests`) after browser actions to inspect intercepted backend API calls.
3. Keep browser sessions focused and short to prevent excessive memory usage.
