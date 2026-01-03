# Communication

> **For entity lookups and global rules**: See `../agents_index.yaml`
>
> **Index Updates**: When adding a new person folder, you MUST also add an entry to `../agents_index.yaml` in the `people` registry and update `meta.last_updated` and `changelog`.

This folder structures stakeholder communication, team meetings, and cross-team collaboration for the ML/AI team.

## Folder Structure

```
communication/
├── meetings/            # Multi-person meetings (non-1:1)
│   └── global_meetings/ # Company/department-wide meetings
└── people/              # Per-person profiles, notes, references
```

## People Folders

Each person has a folder under `communication/people/<first>_<last>/` containing:

| File | Purpose | When to update |
|------|---------|----------------|
| `profile.md` | Canonical info & relationship | When role/relationship changes |
| `notes.md` | Free-form notes, 1:1 impressions | After interactions with insights |
| `thoughts.md` | Ideas and reflections to remember | When planning discussions |
| `references.md` | Links to other files where involved | After creating any doc mentioning them |
| `meetings/` | Meeting notes (JFs, 1:1s) | After each meeting |

### Adding a New Person

1. Create folder: `communication/people/<first>_<last>/`
2. Copy templates from `../templates/`:
   - `person_profile.md` → `profile.md`
   - `person_notes.md` → `notes.md`
   - `person_thoughts.md` → `thoughts.md`
   - `person_references.md` → `references.md`
3. Fill in `profile.md` with known information
4. **REQUIRED**: Update `../agents_index.yaml`:
   - Add entry to `people` registry with path, role, relationship
   - Update `meta.last_updated` to today's date
   - Add changelog entry: "Added <person_name> to people registry"

### Cross-Referencing Workflow

After creating/updating content involving a person:
1. Add link to their `references.md`
2. Add personal insights to `notes.md` if relevant
3. Capture strategic ideas in `thoughts.md` if applicable

## Meeting Notes Location

| Scenario | Location |
|----------|----------|
| 1:1 with one person | `communication/people/<person>/meetings/` |
| Team sync (ML/AI team) | `communication/meetings/<group_slug>/` |
| Cross-team meeting | `communication/meetings/<group_slug>/` |
| Company-wide meeting | `communication/meetings/global_meetings/` |

**Group folder naming**: Lowercase first names of other participants (excluding yourself), alphabetically sorted, joined with underscores. Example: `peter_michael`

## Communication Principles

- **Transparency**: Clear on progress, risks, and decisions
- **Proactive**: Escalate early, don't wait for problems to grow
- **Collaborative**: Build constructive relationships across teams
- **Diplomatic**: Use tact, especially in high-tension situations

## Key Relationships
| Stakeholder | Communication Focus |
|-------------|---------------------|
| Christopher Lemke | ML/AI strategy, ML team structure |
