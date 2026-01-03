---
source: "{{source_path}}"
source_title: "{{source_title}}"
type: memory
created: "{{date: YYYY-MM-DD}}"
last_updated: "{{date: YYYY-MM-DD}}"
feedback_count: {{count}}
tags:
  - memory
  - learned
  - {{source_type}}
---

# Memory: {{source_title}}

> Persistent memory capturing human feedback about `{{source_path}}`

---

## Entries

### [{{date}}] {{feedback_type}}

**Source Section**: {{section_reference}}

**Feedback**:
> {{original_feedback}}

**Learned**:
{{structured_insight}}

**Confidence**: {{high|medium|low}}

**Reasoning**:
{{why_this_matters}}

---

## Summary

### Corrections
<!-- Factual errors, inaccuracies, outdated information -->
- {{correction_1}}

### Key Insights
<!-- Crucial points to remember, emphasis markers -->
- {{insight_1}}

### Missing Elements
<!-- Gaps, omissions, connections that should be added -->
- {{missing_1}}

### Connections
<!-- Cross-references to other thinkers, thoughts, sources -->
- [[{{related_path}}]]: {{connection_reason}}

### Preferences
<!-- Stylistic notes, personal framing preferences -->
- {{preference_1}}

### Irrelevant
<!-- Things to skip or de-emphasize -->
- {{irrelevant_1}}

---

## Meta

### Feedback History

| Date | Type | Confidence | Section |
|------|------|------------|---------|
| {{date}} | {{type}} | {{confidence}} | {{section}} |

### Learning Statistics

- **Total entries**: {{feedback_count}}
- **Corrections**: {{correction_count}}
- **Insights**: {{insight_count}}
- **Last reviewed**: {{last_updated}}
