# open_assistant 🤖❤️📒

> *I'm not disorganized, I'm just delegating my memory to a Markdown file.*

<p align="center">
  <img src="../assets/images/monitor_image.png" alt="open_assistant" width="300">
</p>

An AI-powered assistant workspace template. Built on [opencode](https://opencode.ai), this project provides a structured environment for managing teams, projects, meetings, tickets, calendar events, and institutional knowledge — turning "I think I wrote that down somewhere" into actual searchable files.

This tool runs with all kinds of AI models, including ChatGPT, Claude, Gemini or local setups like [LLM Studio](https://lmstudio.ai/). Just pick your favorite AI model within the setup process

## Overview

**open_assistant** is a template repository that combines:

- **Custom AI Agents** - Specialized agents for code review, project analysis, ticket improvement, and more
- **Slash Commands** - Quick actions for common workflows like generating reports, improving prompts, and smart commits
- **Custom Tools** - Integrations with Atlassian (JIRA/Confluence), Amplitude, AWS SageMaker, and calendar management
- **Structured Knowledge Base** - Hierarchical index system for efficient information retrieval
- **Calendar & Reminders** - Native macOS notifications for events and deadlines

> **Before getting started**, it's recommended to familiarize yourself with opencode:
> - **Documentation**: https://opencode.ai/docs
> - **GitHub Repository**: https://github.com/sst/opencode

---

## What Can You Do With This?

Here are a few examples of what you can do with open_assistant. Think of it as having a second brain that actually remembers things — unlike Christopher, who once forgot his own team member's name during a standup.

### Example 1: Meeting Notes to Actionable Chaos

```
Yesterday I had a meeting with Amelia Earhart. She said she'll handle
the Pacific route optimization by next Friday. I need to review the
navigation algorithm before she starts, and we should sync with
Charles Lindbergh about the fuel calculations.

Give me the todos I have until next Friday.
```

```
📝 Meeting processed and stored!

Created: communication/meetings/2025-12-12_amelia_earhart_meeting.md
Updated: communication/people/amelia_earhart/notes.md (new person created!)
Updated: communication/people/amelia_earhart/references.md

 📅 Calendar events created:
  • 2025-12-19: "Due: Pacific route optimization" (Amelia Earhart)
  • Reminder: "Sync with Charles Lindbergh re: fuel calculations"

✅ Your TODOs until Friday (2025-12-19):

| ID | Task | Due | Priority |
|----|------|-----|----------|
| TODO-007 | Review navigation algorithm before Amelia starts | 2025-12-18 | high |
| TODO-002 | Schedule AI topic meeting with Jensen Huang | 2025-12-20 | high |
| TODO-003 | Demo Lead stuff to Dario Amodei | - | medium |

*Note: Amelia Earhart added to contacts. If she's THE Amelia Earhart,
that's impressive networking, Christopher. If not, maybe double-check
your meeting invites.*
```

*One rambling sentence became: a meeting file, a new contact, calendar deadlines, and a prioritized todo list. Meanwhile, Christopher's handwritten notes from 2019 are still illegible.*

### Example 2: Ingest Knowledge Without Reading
Using the `/ingest` command, you can automatically add data to your knowledge base.

```
/ingest https://invia.atlassian.net/wiki/spaces/IFGIT/pages/329286323/Data+Layer+-+Solution+Blueprint
```

```
> ╔══════════════════════════════════════════════════════════════════╗
> ║                    INGESTION COMPLETE                            ║
> ╠══════════════════════════════════════════════════════════════════╣
> ║ SOURCE: confluence                                               ║
> ╠══════════════════════════════════════════════════════════════════╣
> ║ FILES CREATED:                                                   ║
> ║   ✓ idea_development/confluence_ai_ml_knowledge.md (updated)     ║
> ║                                                                  ║
> ║ FILES UPDATED:                                                   ║
> ║   ✓ communication/people/mogens_winther/references.md            ║
> ║   ✓ project_management/galactic_roadmap/project.md               ║
> ║                                                                  ║
> ║ DETECTED ENTITIES:                                               ║
> ║   • 3 people: Mogens Winther, J.S. Bach, Johann W. von Goethe    ║
> ║   • 1 project: Galactic Roadmap (Mystic Mercury)                 ║
> ║   • Architecture patterns: Event-driven, CQRS, Domain Services   ║
> ║                                                                  ║
> ║ KEY INSIGHTS EXTRACTED:                                          ║
> ║   • Data Layer serves as single source of truth                  ║
> ║   • Kafka-based event streaming architecture                     ║
> ║   • Flight Admin modernization dependency                        ║
> ║                                                                  ║
> ║ PRESERVATION CHECK: ✓ Complete                                   ║
> ╚══════════════════════════════════════════════════════════════════╝
```

*Now Chris can pretend he read a 15-page architecture document. The assistant extracted the important bits and cross-referenced them with existing projects and people and stored all information were needed. Mogens would be so proud.*

### Example 3: Connect the Dots Across Your Chaos


```
Who was involved in that A/B test thing from yesterday again? And what did we decide?
```

```
The great powerful world and universe optimizer project is currently in active A/B testing.

**Team:**
- Marvin Minsky (Team Lead, core team)
- Claude Shannon (Genius, core team)
- Christopher Lemke (Provides the coffee and cleans up)

**Current Status:**
- Status: active_ab_testing
- Related tickets: FML-1927, FML-1916, FML-1982

**A/B Tests:**
- Test if the current model is better than the previous one.

**Recent Activity:**
- Marvin Minsky showed the new model to the team and presented his path to world domination.
- Claude Shannon came to the conclusion that Anthropic probably names their models after him.
- Christopher Lemke spilled all the coffee over the important calculations
- The final decision was made by Marvin Minsky: we need continue with the A/B test but also adjust the
  parameters of the universe-simulator.
- Progress notes: project_management/universe_optimizer/progress_notes.md
```

*The assistant connected project status, team assignments, ticket references, person notes, and A/B test documentation — all from separate files. Chris would've needed 47 browser tabs and still gotten it wrong.*

---

## Prerequisites

- **macOS**
- **Homebrew** (will be installed during setup if not present)
- **Conda/Miniconda** (for Python environment management)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/invia-flights/open_assistant.git
cd open_assistant

# 2. Run the interactive setup
make setup

# 3. Configure credentials (see Post-Setup Configuration below)

# 4. Start the assistant
open_assistant  # or just: oa
```

The `make setup` command will guide you through:
1. Installing Homebrew (if needed)
2. Installing dependencies from Brewfile
3. Setting up pre-commit hooks
4. Creating the conda environment
5. Configuring shell aliases
6. Optional: Installing the reminder daemon
7. Optional: [GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login)
8. Optional: [opencode authentication](https://opencode.ai/docs/cli/#login)

---

## Personalize Your Workspace

After setup, customize the workspace to match your role and team structure:

### Role Overview (AGENTS.md)

Open `AGENTS.md` and update the **Role Overview** section:
```markdown
| Field | Description | Example |
|-------|-------------|---------|
| **Position** | Your job title | e.g., IT Team Lead - Machine Learning & AI Team |
| **Reports to** | Your manager | e.g., Director IT (Jane Smith) |
| **Team** | Your team composition | e.g., ML Engineers / Data Scientists |
```

### Key Relationships (communication/AGENTS.md)

Open `communication/AGENTS.md` and update the **Key Relationships** table with the stakeholders you work with:
```markdown
| Stakeholder | Communication Focus |
|-------------|---------------------|
| Jane Smith (Director IT) | Strategy alignment, team resources, escalations |
| John Doe (Product Manager) | Feature priorities, roadmap planning |
| Sarah Miller (Data Engineering Lead) | Data pipelines, cross-team dependencies |
```
This helps the AI assistant understand your organizational context and provide more relevant suggestions.

---

## Post-Setup Configuration

To save space in the context window all MCP servers are deactivated. Navigate to `.opencode.jsonc` and set `"enabled": true` for the MCP servers you want to use.

### API Credentials (.env file)

For full functionality, you'll need API tokens for various services. Create a `.env` file in the project root:

> **Important**: This file is NOT part of the repository template and must be created manually. It should NEVER be committed to git.

```env
ATLASSIAN_URL=https://invia.atlassian.net
ATLASSIAN_USERNAME=your-email@invia.de
ATLASSIAN_API_TOKEN=ATATT...
ATLASSIAN_CLOUD=true
TEMPO_API_TOKEN=...

AMPLITUDE_EXPERIMENT_TOKEN=ampex...
CONTEXT7_API_KEY=...
```

| Variable | Required For | How to Obtain |
|----------|--------------|---------------|
| `ATLASSIAN_URL` | JIRA/Confluence integration | Your Atlassian instance URL |
| `ATLASSIAN_USERNAME` | JIRA/Confluence integration | Your Atlassian email |
| `ATLASSIAN_API_TOKEN` | JIRA/Confluence integration | [Create API Token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `TEMPO_API_TOKEN` | Tempo timesheet integration | Tempo settings > API Integration |
| `AMPLITUDE_EXPERIMENT_TOKEN` | Amplitude experiments | Amplitude settings > Projects > Management API Key |
| `CONTEXT7_API_KEY` | Enhanced library documentation | See below |

### Context7 Account (Highly Recommended)

[Context7](https://context7.com/) provides up-to-date documentation for third-party libraries, which is especially important for the `claude-code` wrapper agent when working with external packages.

1. Create a free account at https://context7.com/
2. Generate an API key from your dashboard
3. Add the key to your `.env` file as `CONTEXT7_API_KEY`

### AWS Integration (Optional)

If you have an AWS account and want to use AWS-related features (CloudWatch, Cost Explorer, SageMaker), enable the AWS MCP servers:

1. Open `opencode.jsonc`
2. Navigate to the `mcp` section
3. Set `"enabled": true` for:
   - `awslabs.cloudwatch-mcp-server`
   - `awslabs.cost-explorer-mcp-server`
   - `awslabs.sagemaker-ai-mcp-server`
4. Ensure you're authenticated with AWS SSO (`aws sso login`)

---

## Makefile Reference

Run `make help` for a complete list of available targets.

### Setup Targets

| Target | Description |
|--------|-------------|
| `make setup` | Interactive guided setup (start here!) |
| `make check-homebrew` | Check/install Homebrew |
| `make brew` | Install dependencies from Brewfile |
| `make pre-commit` | Install pre-commit Git hooks |
| `make conda` | Create conda environment from lock file |
| `make activate` | Create activation script & configure shell aliases |
| `make auth` | Authenticate with opencode |
| `make gh-login` | Authenticate with GitHub CLI |

### Reminder Daemon Targets

| Target | Description |
|--------|-------------|
| `make install-reminder-daemon` | Install background notification service |
| `make uninstall-reminder-daemon` | Remove notification service |
| `make reminder-status` | Check daemon status & send test notification |
| `make reminder-test` | Send test notification only |

### Cleanup Targets

| Target | Description |
|--------|-------------|
| `make clean` | Remove conda environment only |
| `make uninstall` | Remove everything installed by setup |

---

## Slash Commands

Invoke commands with `/command-name` in the opencode interface. They are made to speed up common tasks. [Read more](https://opencode.ai/docs/commands/#create-command-files) on how to create more custom commands that fit your needs.

| Command | Description |
|---------|-------------|
| `/calendar` | 📅 View and manage calendar events with visual calendar display |
| `/experiment-report` | 🧪 Download Amplitude experiment data and generate a markdown report |
| `/improve-prompt` | 📝 Improve a prompt using Claude's official best practices |
| `/improve-ticket` | 🎫 Enhance a JIRA ticket with an AI-generated implementation guide |
| `/ingest` | 📄 This is the most important command. Use it to automatically add data to your knowledge base. Extract and store information from text, files, or URLs into the knowledge base |
| `/project-progress` | 📃 Analyze a GitHub project and generate contributor reports |
| `/sagemaker-report` | 📊 Generate a deep-dive report on SageMaker endpoints with Plotly visualizations |
| `/smart-commit` | 🧑‍💻 Analyze uncommitted changes and create a conventional commit using git |
| `/tempo-hours` | 🕒 Fetch Tempo timesheet hours for team members and compare against expected patterns |
| `/todo-executer` | 💼 Analyze a TODO list and generate a detailed execution manual |
| `/weekly-status-report` | 🗓️ Generate a weekly status report for GitHub repositories |

---

## Agents

You can use the tab-key to navigate through the list of agents:
- `Assistant` a general agent for helping you with your organizational tasks like projects, meetings, tickets, calendar events, etc.
- `Build` a general agent best for building simple new commands, tools, etc.
- `Plan` a specialized agent best for planning complex tasks.
- `claude-code` a wrapper for Claude Code CLI for all complex software development tasks.

Specialized AI agents 🤖 available for complex tasks.

| Agent | Description |
|-------|-------------|
| `claude-code` | Wrapper for Claude Code CLI for all software development tasks. Enhances prompts, gathers context, and executes `claude` CLI commands. |
| `claude-code-worker` | Worker subagent for parallel Claude Code sessions. Use for multiple independent tasks simultaneously. |
| `ingest-processor` | Processes extraction results from `ingest.py`. Handles JIRA enrichment, entity disambiguation, and cross-reference updates. |
| `project-analyzer` | Deep analyzer for data science and ML projects. Performs 7-dimension maturity scoring, contributor analysis, and risk assessment. |
| `prompt-improver` | Expert prompt engineer that improves prompts using Claude's official best practices. |
| `ticket-improver` | Generates LLM-optimized implementation guides for JIRA tickets with technical context and code snippets. |
| `todo-analyzer-executer` | Analyzes TODO lists and creates detailed, actionable execution manuals. |

---

## Custom Tools

Custom tools available to agents via the opencode plugin system.

| Tool | Description |
|------|-------------|
| `amplitude_experiments` | Search, inspect, and evaluate Amplitude experiments (EU). Includes experiment search, detail retrieval, user evaluation, and chart CSV export. |
| `atlassian` | JIRA (read + limited write) and Confluence (read-only) access. Get issues, search with JQL, gather context, update descriptions, add comments, and search Confluence. |
| `calendar` | Calendar event management. List events with natural language dates, create/update/delete events, with automatic meeting file creation. |
| `experiment_report` | Generate Amplitude experiment reports with configuration, variants, timeline, and deployments. Auto-saves to project folders. |
| `sagemaker_infra` | Generate AWS ML infrastructure reports tracing API Gateway → Lambda → SageMaker. Includes autoscaling policies and orphaned resource detection. |

---

## Project Structure

```
open_assistant/
├── .opencode/                  # opencode configuration
│   ├── agent/                  # Custom agent definitions
│   │   └── cc_subagents/       # Subagents for parallel execution
│   ├── command/                # Slash command definitions
│   ├── tool/                   # Custom tool implementations (TypeScript)
│   ├── data/                   # Runtime data (known entities, etc.)
│   └── plugin                  # Plugin configuration
├── assets/                     # Static assets
│   └── images/                 # Images for documentation
├── calendar/                   # Calendar event storage
│   └── events/                 # Individual event files (YAML frontmatter + markdown)
├── communication/              # People and meeting management
│   ├── meetings/               # Multi-person meeting notes
│   │   └── global_meetings/    # Organization-wide meetings
│   └── people/                 # Per-person profiles, notes, and references
├── docs/                       # Documentation
├── idea_development/           # Innovation pipeline and POCs
├── indices/                    # Hierarchical index system
│   ├── root.yaml               # Entry point - load first
│   ├── people.yaml             # Person registry
│   ├── projects.yaml           # Project registry
│   ├── tickets.yaml            # Ticket prefix mappings
│   └── ...                     # Other domain indices
├── project_management/         # Active project tracking
├── reports/                    # Generated reports
│   ├── aws_infra/              # AWS infrastructure reports
│   ├── sagemaker/              # SageMaker endpoint reports
│   └── status_updates/         # Weekly status reports
├── scripts/                    # Python automation scripts
│   ├── claude_code_helper/     # Helpers for Claude Code agent
│   └── launchagent/            # macOS LaunchAgent templates
├── sessions/                   # Saved chat sessions
├── team_development/           # Team growth and performance
├── templates/                  # Document templates
├── tickets/                    # External ticket tracking (JIRA)
├── todos/                      # Personal action items
│   └── list/                   # Individual TODO files
├── AGENTS.md                   # Main agent instructions
├── Brewfile                    # Homebrew dependencies
├── conda-lock.yml              # Locked Python environment
├── environment.yml             # Conda environment specification
├── Makefile                    # Setup and maintenance commands
├── opencode.jsonc              # opencode configuration
└── pyproject.toml              # Python project configuration
```

### Index System

The repository uses a hierarchical index system for token-efficient navigation:

1. **Load `indices/root.yaml` first** - Contains routing rules
2. **Load domain index as needed** - `people.yaml`, `projects.yaml`, `tickets.yaml`, etc.
3. **Read actual files** - After finding paths in indices

This approach minimizes token usage compared to loading all information upfront.

---

## Configuration

### opencode.jsonc

The main opencode configuration file contains:

- **Plugins** - Authentication plugins (OpenAI, Gemini)
- **Agent definitions** - `report_assistant` and `assistant` modes
- **MCP servers** - External tool integrations

### Available MCP Servers

| MCP Server | Description | Default State |
|------------|-------------|---------------|
| `github` | GitHub Copilot MCP for Git operations | Disabled* |
| `context7` | Third-party library documentation | Disabled** |
| `git` | Local Git operations via mcp-server-git | Enabled |
| `awslabs.cloudwatch-mcp-server` | CloudWatch logs and metrics | Disabled* |
| `awslabs.cost-explorer-mcp-server` | AWS cost analysis | Disabled*** |
| `awslabs.sagemaker-ai-mcp-server` | SageMaker management | Disabled*** |

*Enable it if you have authenticated with GitHub CLI (`gh auth login`).
*Enable it if you have added a `CONTEXT7_API_KEY` to your `.env` file.
***Enable AWS MCPs by setting `"enabled": true` in `opencode.jsonc` after configuring AWS credentials.

---

## Learn More

- **opencode Documentation**: https://opencode.ai/docs
- **opencode GitHub**: https://github.com/sst/opencode
- **Context7**: https://context7.com/

---

## Now Go Forth and Be Productive

You've made it this far. You've installed the tools. You've read the docs. There's nothing left standing between you and peak productivity — except maybe that browser tab with Reddit still open.

Remember:
- Don't work harder, work smarter (or at least let the AI work harder for you)
- Expect more from yourself, but also forgive yourself when you still forget things
- The best time to organize your life was years ago. The second best time is right after you close this README.

*Now stop reading documentation and go pretend you have everything under control.*
