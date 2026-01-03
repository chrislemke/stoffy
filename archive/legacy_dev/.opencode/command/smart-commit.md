---
description: Analyze uncommitted changes and create a conventional commit with AI-generated message
subtask: true
---

# Smart Commit

Analyze all uncommitted git changes (staged, unstaged, and untracked), generate an appropriate conventional commit message, and commit the changes.

---

## Step 1: Check for Uncommitted Changes

Run the status command to see if there are any changes to commit:

```bash
python scripts/git_commit_helper.py status --json
```

**If `has_changes` is `false`**: Stop here and inform the user: "Nothing to commit. Working tree is clean."

**If `has_changes` is `true`**: Continue to Step 2.

---

## Step 2: Get the Full Diff

Retrieve the complete diff of all changes for analysis:

```bash
python scripts/git_commit_helper.py diff
```

This returns:
- Staged changes (already added to index)
- Unstaged changes (modified tracked files)
- Untracked files (new files not yet tracked)

**Important: Infrastructure Files**

The diff output automatically **excludes** infrastructure files from analysis:
- `.opencode/` directory
- `scripts/` directory
- Any `AGENTS.md` file
- `conda-lock.yml`, `environment.yml`, `opencode.jsonc`

These files will be listed in a summary section at the end of the diff but their content is hidden. They **will be committed** but should **NOT be mentioned** in the commit message or description.

---

## Step 3: Analyze Changes and Generate Commit Message

Based on the diff output (excluding infrastructure files), determine:

1. **Commit Type** - Select the most appropriate type:
   - `feat`: A new feature
   - `fix`: A bug fix
   - `docs`: Documentation only changes
   - `style`: Formatting, missing semicolons, etc. (no code change)
   - `refactor`: Code change that neither fixes a bug nor adds a feature
   - `perf`: Performance improvement
   - `test`: Adding or correcting tests
   - `build`: Changes to build process or dependencies
   - `ci`: CI configuration changes
   - `chore`: Maintenance tasks, updates to tooling

2. **Scope** (optional) - A noun describing the section of the codebase:
   - Examples: `(api)`, `(parser)`, `(auth)`, `(docs)`
   - Only use if the change is clearly scoped to one area

3. **Subject Line** - A concise description:
   - Use imperative mood ("add" not "added")
   - Do NOT end with a period
   - Maximum 50 characters (soft limit), 72 characters (hard limit)
   - Start with lowercase after the colon

4. **Description** (body) - Explain the "what" and "why":
   - Separate from subject with a blank line
   - Wrap at 72 characters
   - Explain motivation for the change
   - Can include bullet points for multiple changes
   - **Do NOT mention infrastructure files** (they are committed silently)

---

## Step 4: Execute the Commit

Once you have determined the commit message and description, execute:

```bash
python scripts/git_commit_helper.py commit --stage-all --message "<type>[optional scope]: <subject>" --description "<body>"
```

**Important flags:**
- `--stage-all`: Stages all changes (staged + unstaged + untracked) before committing
- `--message` / `-m`: The subject line (required, conventional commit format)
- `--description` / `-d`: The commit body (optional but recommended for non-trivial changes)

---

## Conventional Commits Format Reference

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Valid Types
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style/formatting (no logic change) |
| `refactor` | Code restructuring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Test additions/corrections |
| `build` | Build system/dependencies |
| `ci` | CI/CD configuration |
| `chore` | Maintenance/tooling |
| `revert` | Reverting a previous commit |

### Examples

**Simple feature:**
```
feat: add user authentication endpoint
```

**Bug fix with scope:**
```
fix(parser): handle empty input gracefully
```

**Documentation with body:**
```
docs: update API documentation

- Added examples for all endpoints
- Fixed typos in authentication section
- Updated response schema descriptions
```

**Breaking change:**
```
feat(api)!: change response format to JSON:API

BREAKING CHANGE: API responses now follow JSON:API specification.
All clients need to update their response parsing logic.
```

---

## Error Handling

If the commit fails, the script will output an error message. Common issues:
- Invalid commit message format (not conventional commits)
- No staged changes after staging (e.g., only ignored files)
- Git hooks preventing commit

Report the error to the user with the specific message from the script.
