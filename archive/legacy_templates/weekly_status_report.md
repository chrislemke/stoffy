---
week: "{{week: YYYY-WXX}}"
date: "{{date: YYYY-MM-DD}}"
period_start: "{{period_start: YYYY-MM-DD}}"
period_end: "{{period_end: YYYY-MM-DD}}"
tags:
  - report
  - weekly
---

# AI Team Weekly Status Report - {{week: YYYY-WXX}}

---

## {{project_name}}

**Status**: {{status: ON_TRACK | AT_RISK | OFF_TRACK}}

### Atlassian Status (280 chars)

```
This week: {{highlights}}. Next: {{planned_work}}. Risks: {{risks}}.
```

### This week
- {{completed_item}}

### Next week
- {{planned_item}}

### Risks / blockers
- {{risk_or_blocker}}

**Repository:** {{repository_link}}

---

## {{project_name_2}}

**Status**: {{status: ON_TRACK | AT_RISK | OFF_TRACK}}

... (Repeat structure) ...

---

## Overall Summary

| Metric | Value |
|--------|-------|
| Active repositories | {{active_repos}} |
| Total repositories | {{total_repos}} |

**Cross-project narrative:**

{{narrative_summary}}
