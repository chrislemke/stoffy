---
id: "{{todo_id}}"
title: "{{title}}"
status: "{{status: open | in_progress | done}}"
priority: "{{priority: low | medium | high}}"
due_date: "{{due_date: YYYY-MM-DD}}"
created: "{{created_date: YYYY-MM-DD}}"
people:
  - "{{person_name}}"
context:
  project: "{{project}}"
  ticket: "{{ticket}}"
tags:
  - todo
---

# {{todo_id}}: {{title}}

## Description

{{description}}

## Notes

{{notes}}

## Updates

| Date | Update |
|------|--------|
| {{date: YYYY-MM-DD}} | {{update}} |
