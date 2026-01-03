---
project: "{{project_name}}"
date: "{{date: YYYY-MM-DD}}"
period_start: "{{period_start: YYYY-MM-DD}}"
period_end: "{{period_end: YYYY-MM-DD}}"
activity_status: "{{activity_status: Normal_Activity | High_Activity | Low_Activity | Dormant}}"
maturity_score: "{{maturity_score}}"
tags:
  - report
  - progress
---

# Project Progress Report: {{project_name}}

## Executive Summary

{{executive_summary}}

**Legal/Compliance Status**: {{legal_compliance_status}}

## Project Maturity Score: {{maturity_score}}/14

| Dimension | Score | Notes |
|-----------|-------|-------|
| Documentation | {{doc_score}}/2 | {{doc_notes}} |
| Testing | {{test_score}}/2 | {{test_notes}} |
| CI/CD | {{cicd_score}}/2 | {{cicd_notes}} |
| Code Quality | {{code_score}}/2 | {{code_notes}} |
| Architecture | {{arch_score}}/2 | {{arch_notes}} |
| Data Pipeline | {{data_score}}/2 | {{data_notes}} |
| ML/AI Specifics | {{ml_score}}/2 | {{ml_notes}} |

## Contributor Analysis

### Summary

| Contributor | Commits | Lines Changed | Primary Focus Areas | Productivity Rating |
|-------------|---------|---------------|---------------------|---------------------|
| {{contributor_name}} | {{commits}} | {{lines_changed}} | {{focus_areas}} | {{productivity_rating}} |

### {{contributor_name}}
- **GitHub**: {{github_username}}
- **Commits**: {{commits}}
- **Focus Areas**:
  - {{focus_area}}
- **Key Contributions**:
  - {{contribution}}
- **Summary**: {{contributor_summary}}

## Technical Overview

### Architecture
{{architecture_description}}

### Key Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| {{package}} | {{version}} | {{purpose}} |

## Risk Assessment

### Critical Blockers
{{critical_blockers}}

### Technical Debt
| Item | Severity | Description | Recommendation |
|------|----------|-------------|----------------|
| {{item}} | {{severity: High | Medium | Low}} | {{description}} | {{recommendation}} |

## Recommendations

### High Priority
1. {{high_priority_recommendation}}

### Medium Priority
2. {{medium_priority_recommendation}}

### Low Priority
3. {{low_priority_recommendation}}
