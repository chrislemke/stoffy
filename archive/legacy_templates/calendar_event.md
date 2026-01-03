---
id: "{{event_id}}"
title: "{{title}}"
type: "{{type: meeting | reminder | deadline | appointment | personal | holiday | vacation | blocked}}"
date: "{{date: YYYY-MM-DD}}"
time: "{{time: HH:MM}}"
duration: "{{duration}}"
end_date: "{{end_date: YYYY-MM-DD}}"
location: "{{location}}"
participants:
  - "{{person_slug}}"
recurrence:
  pattern: "{{pattern: daily | weekly | monthly | yearly}}"
  interval: "{{interval}}"
  weekdays: "{{weekdays}}"
  day_of_month: "{{day_of_month}}"
  end_date: "{{recurrence_end_date}}"
  count: "{{count}}"
status: "{{status: scheduled | completed | cancelled}}"
reminder: "{{reminder}}"
context:
  project: "{{project}}"
  ticket: "{{ticket}}"
  meeting_file: "{{meeting_file}}"
tags:
  - calendar
created: "{{created_date: YYYY-MM-DD}}"
---

# {{event_id}}: {{title}}

## Description

{{description}}

## Notes

{{notes}}

## Updates

| Date | Update |
|------|--------|
| {{date: YYYY-MM-DD}} | {{update}} |
