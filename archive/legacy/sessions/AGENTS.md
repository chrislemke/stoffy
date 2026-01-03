# Sessions

> **For entity lookups and global rules**: See `../agents_index.yaml`
> 
> **Index Updates**: This folder is primarily for storage; no index updates typically required unless adding subfolder structure.

This folder contains saved chat sessions with LLM agents (Claude, ChatGPT, etc.).

## Purpose

- Preserve valuable conversations for future reference
- Track problem-solving approaches and decisions made with AI assistance
- Enable continuation of complex multi-session tasks

## File Naming Convention

- Format: `session-<session_id>.md` or `YYYY-MM-DD_<topic>.md`
- Use lowercase with underscores/hyphens
- Include descriptive topic when possible

## Content Guidelines

Sessions may contain:
- Full conversation transcripts
- Summaries of key decisions
- Code snippets or solutions generated
- Links to files created/modified during the session

## Cross-References

When a session involves:
- **A person**: Consider adding link to their `../communication/people/<name>/references.md`
- **A project**: Consider linking from `../project_management/<project>/`
- **A ticket**: Consider updating `../tickets/<TICKET-ID>.md`
