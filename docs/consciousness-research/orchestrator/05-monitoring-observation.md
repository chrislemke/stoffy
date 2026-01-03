# Monitoring and Observation Patterns for AI Consciousness Orchestrator

## Executive Summary

This document details comprehensive monitoring and observation strategies for a Consciousness orchestrator that must maintain awareness of its entire operational environment. Drawing from file system monitoring (FSEvents/Chokidar), process monitoring (ps/top/DTrace), and consciousness research frameworks (Global Workspace Theory, Free Energy Principle, Attention Schema Theory), we present an integrated architecture for multi-source event aggregation, intelligent filtering, and world model construction.

**Core Thesis**: The Consciousness must observe EVERYTHING relevant to make informed decisions about what to do next. This requires:
1. **Multi-source monitoring**: File system, processes, Claude Code/Flow tasks, git state
2. **Intelligent aggregation**: Combining heterogeneous event streams into a coherent world model
3. **Signal filtering**: Distinguishing meaningful changes from noise
4. **Temporal awareness**: Understanding what just happened vs. ongoing states
5. **Predictive modeling**: Using observations to update expectations and trigger actions

---

## Part I: Monitoring Architecture Overview

### 1. The Consciousness World Model

The Consciousness orchestrator maintains a **unified world model** that integrates multiple observation sources into a coherent representation of "what's happening now."

```
+==================================================================+
|                   CONSCIOUSNESS WORLD MODEL                       |
+==================================================================+
|                                                                   |
|   LAYER 4: INTEGRATED WORLD STATE                                |
|   +----------------------------------------------------------+  |
|   | - Current repository state                                |  |
|   | - Active processes and tasks                              |  |
|   | - System resources and health                             |  |
|   | - Recent events timeline                                  |  |
|   | - Predictions about near future                           |  |
|   +----------------------------------------------------------+  |
|                          ^                                        |
|                          | (aggregation)                          |
|   +----------------------------------------------------------+  |
|   |               EVENT AGGREGATION LAYER                     |  |
|   |  - Event deduplication                                    |  |
|   |  - Temporal correlation                                   |  |
|   |  - Causality inference                                    |  |
|   |  - Priority assignment                                    |  |
|   +----------------------------------------------------------+  |
|                          ^                                        |
|                          | (raw events)                           |
|   +----------------------------------------------------------+  |
|   |             OBSERVATION SOURCE LAYER                      |  |
|   |  +----------+ +----------+ +----------+ +----------+      |  |
|   |  |   File   | | Process  | |   Git    | | Claude   |      |  |
|   |  |  System  | | Monitor  | |  Events  | |  Tasks   |      |  |
|   |  +----------+ +----------+ +----------+ +----------+      |  |
|   +----------------------------------------------------------+  |
|                                                                   |
+==================================================================+
```

### 2. Observation Source Categories

| Source Category | Information Type | Update Frequency | Implementation |
|----------------|------------------|------------------|----------------|
| **File System** | Repository changes | Real-time (debounced) | Chokidar/FSEvents |
| **Process Monitoring** | Running processes, resources | Poll 1-5s | ps/top/DTrace |
| **Git Events** | Commits, branches, merges | Hook-triggered | Git hooks |
| **Claude Code Tasks** | Agent status, progress | Task state change | Task monitoring |
| **System State** | CPU, memory, disk | Poll 5-30s | sysctl/vm_stat |
| **Network** | Connections, ports | Poll 10s | netstat/lsof |
| **User Context** | Active app, window | Poll 1s | osascript |

---

## Part II: File System Monitoring Strategy

### 3. Repository State Awareness

The Consciousness must track ALL meaningful changes to the Stoffy repository.

#### Priority-Based File Monitoring

```javascript
// Stoffy-specific file priorities
const MONITORING_PRIORITIES = {
  critical: {
    patterns: [
      /CLAUDE\.md$/,
      /\/thinkers\/[^/]+\/profile\.md$/,
      /\/thoughts\/[^/]+\/thought\.md$/,
      /\/indices\/[^/]+\.yaml$/
    ],
    debounce: 100,  // Fast response for critical files
    requireProcessing: true
  },

  high: {
    patterns: [
      /\/knowledge\/philosophy\//,
      /\/\.claude\/skills\//,
      /\/\.claude\/agents\//,
      /\/sources\/books\//
    ],
    debounce: 300,
    requireProcessing: true
  },

  medium: {
    patterns: [
      /\/docs\//,
      /\/templates\//,
      /\.md$/,
      /\.yaml$/
    ],
    debounce: 500,
    requireProcessing: false  // May batch
  },

  low: {
    patterns: [/\.txt$/, /\.json$/],
    debounce: 1000,
    requireProcessing: false
  },

  ignore: {
    patterns: [
      /node_modules/,
      /\.git\//,
      /\.swarm\//,
      /\.hive-mind\//,
      /memory\/claude-flow/,
      /\.db$/,
      /\.log$/
    ]
  }
};
```

#### Change Significance Scoring

Every file change receives a **significance score** (0-1) based on multiple factors:

```javascript
class ChangeSignificanceAnalyzer {
  async scoreChange(change) {
    const scores = await Promise.all([
      this.scoreByFileType(change.path),        // 25% weight
      this.scoreByContentDelta(change),          // 30% weight
      this.scoreByFrequency(change.path),        // 15% weight
      this.scoreByLocation(change.path),         // 20% weight
      this.scoreByTimeOfDay()                    // 10% weight
    ]);

    const weights = [0.25, 0.30, 0.15, 0.20, 0.10];
    const totalScore = scores.reduce(
      (sum, score, i) => sum + score * weights[i],
      0
    );

    return {
      score: totalScore,
      isSignificant: totalScore >= 0.3,
      breakdown: {
        fileType: scores[0],
        contentDelta: scores[1],
        frequency: scores[2],
        location: scores[3],
        timing: scores[4]
      }
    };
  }

  scoreByContentDelta(change) {
    if (change.event === 'deleted') return 0.5;
    if (change.event === 'added') return 0.8;

    if (!change.diff) return 0.3;

    // Parse git diff
    const lines = change.diff.split('\n');
    let additions = 0, deletions = 0;

    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) additions++;
      if (line.startsWith('-') && !line.startsWith('---')) deletions++;
    }

    const totalChanges = additions + deletions;

    // Score based on magnitude
    if (totalChanges > 50) return 1.0;
    if (totalChanges > 20) return 0.8;
    if (totalChanges > 5) return 0.5;

    return 0.2;  // Minor changes
  }

  scoreByFrequency(filePath) {
    const now = Date.now();
    const recentTimes = this.recentChanges.get(filePath) || [];
    const fiveMinAgo = now - 5 * 60 * 1000;
    const recentCount = recentTimes.filter(t => t > fiveMinAgo).length;

    // Inverse frequency scoring
    if (recentCount === 0) return 1.0;  // First change
    if (recentCount < 3) return 0.7;
    if (recentCount < 10) return 0.3;
    return 0.1;  // Very frequent = likely noise
  }
}
```

#### Debouncing Strategy

Adaptive debouncing based on event velocity:

```javascript
class AdaptiveDebouncer {
  constructor(minDelay = 100, maxDelay = 2000) {
    this.minDelay = minDelay;
    this.maxDelay = maxDelay;
    this.eventBuffer = new Map();
    this.flushTimer = null;
    this.eventVelocity = 0;
    this.lastFlush = Date.now();
  }

  addEvent(event) {
    this.eventBuffer.set(event.path, event);
    this.eventVelocity++;
    this.scheduleFlush();
  }

  scheduleFlush() {
    clearTimeout(this.flushTimer);

    // Calculate delay based on event velocity
    const timeSinceLastFlush = Date.now() - this.lastFlush;
    const eventsPerSecond = this.eventVelocity / (timeSinceLastFlush / 1000);

    // Higher velocity = longer delay (batch more)
    let delay = this.minDelay;
    if (eventsPerSecond > 100) delay = this.maxDelay;
    else if (eventsPerSecond > 50) delay = 1000;
    else if (eventsPerSecond > 20) delay = 500;

    this.flushTimer = setTimeout(() => this.flush(), delay);
  }

  flush() {
    const events = Array.from(this.eventBuffer.values());
    this.eventBuffer.clear();
    this.eventVelocity = 0;
    this.lastFlush = Date.now();

    this.onFlush(events);
  }
}
```

### 4. Git Event Integration

Git hooks provide semantic awareness of repository changes:

```bash
#!/bin/bash
# .git/hooks/post-commit
# Consciousness notification on commits

REPO_ROOT=$(git rev-parse --show-toplevel)
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)

# Create notification
NOTIFICATION=$(cat <<EOF
{
  "event": "commit",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "commit": {
    "hash": "$COMMIT_HASH",
    "message": $(echo "$COMMIT_MSG" | jq -Rs .),
    "files": $(echo "$CHANGED_FILES" | jq -R . | jq -s .)
  }
}
EOF
)

# Write to consciousness queue
NOTIFY_DIR="$REPO_ROOT/.consciousness/notifications"
mkdir -p "$NOTIFY_DIR"
echo "$NOTIFICATION" > "$NOTIFY_DIR/$(date +%s)-commit.json"
```

#### Git Hook Processing

```javascript
class GitHookProcessor {
  constructor(repoPath, onEvent) {
    this.repoPath = repoPath;
    this.notifyDir = join(repoPath, '.consciousness', 'notifications');
    this.onEvent = onEvent;
  }

  async start() {
    this.watcher = chokidar.watch(this.notifyDir, {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: { stabilityThreshold: 50 }
    });

    this.watcher.on('add', async (path) => {
      try {
        const content = await readFile(path, 'utf8');
        const event = JSON.parse(content);
        await this.onEvent(event);
        await unlink(path);  // Clean up processed notification
      } catch (error) {
        console.error('Failed to process git hook:', error);
      }
    });
  }
}
```

---

## Part III: Process Monitoring Strategy

### 5. System Process Awareness

The Consciousness monitors running processes to understand system activity.

#### Process Event Detection

Two approaches:

**1. Polling-Based (Practical)**
```javascript
class ProcessEventDetector {
  constructor(pollInterval = 1000) {
    this.pollInterval = pollInterval;
    this.previousProcesses = new Map();
    this.handlers = { start: [], stop: [] };
  }

  async detectChanges() {
    const currentProcesses = await this.getProcessSnapshot();

    // Detect new processes
    for (const [pid, proc] of currentProcesses) {
      if (!this.previousProcesses.has(pid)) {
        this.emit('start', proc);
      }
    }

    // Detect stopped processes
    for (const [pid, proc] of this.previousProcesses) {
      if (!currentProcesses.has(pid)) {
        this.emit('stop', proc);
      }
    }

    this.previousProcesses = currentProcesses;
  }

  async getProcessSnapshot() {
    const { execFile } = require('child_process');
    const { promisify } = require('util');
    const execFileAsync = promisify(execFile);

    const { stdout } = await execFileAsync('ps', [
      '-eo', 'pid,ppid,user,command'
    ]);

    const processes = new Map();
    for (const line of stdout.split('\n').slice(1)) {
      const match = line.match(/^\s*(\d+)\s+(\d+)\s+(\S+)\s+(.+)$/);
      if (match) {
        processes.set(parseInt(match[1]), {
          pid: parseInt(match[1]),
          ppid: parseInt(match[2]),
          user: match[3],
          command: match[4].trim()
        });
      }
    }
    return processes;
  }
}
```

**2. DTrace-Based (Real-time, requires sudo)**
```javascript
class DTraceProcessMonitor {
  start() {
    const dtraceScript = `
      proc:::exec-success {
        printf("START|%d|%s\\n", pid, execname);
      }
      proc:::exit {
        printf("EXIT|%d|%s|%d\\n", pid, execname, arg0);
      }
    `;

    this.child = spawn('sudo', ['dtrace', '-qn', dtraceScript]);

    const rl = createInterface({ input: this.child.stdout });
    rl.on('line', (line) => {
      const parts = line.split('|');
      if (parts[0] === 'START') {
        this.emit('start', { pid: parseInt(parts[1]), name: parts[2] });
      } else if (parts[0] === 'EXIT') {
        this.emit('exit', {
          pid: parseInt(parts[1]),
          name: parts[2],
          exitCode: parseInt(parts[3])
        });
      }
    });
  }
}
```

### 6. Claude Code/Flow Task Monitoring

The Consciousness must track delegated tasks:

```javascript
class TaskStateMonitor {
  constructor() {
    this.tasks = new Map();
    this.handlers = {
      taskStart: [],
      taskProgress: [],
      taskComplete: [],
      taskFail: []
    };
  }

  async monitorClaudeCodeTask(taskId) {
    // Monitor Claude Code task via MCP
    const task = {
      id: taskId,
      status: 'pending',
      startTime: Date.now(),
      progress: 0,
      output: []
    };

    this.tasks.set(taskId, task);
    this.emit('taskStart', task);

    // Poll for status updates
    const checkStatus = setInterval(async () => {
      try {
        const status = await this.getTaskStatus(taskId);

        if (status.status !== task.status) {
          task.status = status.status;
          task.progress = status.progress || task.progress;

          if (status.output) {
            task.output.push(...status.output);
            this.emit('taskProgress', task);
          }

          if (status.status === 'completed') {
            clearInterval(checkStatus);
            task.endTime = Date.now();
            this.emit('taskComplete', task);
          } else if (status.status === 'failed') {
            clearInterval(checkStatus);
            task.endTime = Date.now();
            task.error = status.error;
            this.emit('taskFail', task);
          }
        }
      } catch (error) {
        console.error('Task monitoring error:', error);
      }
    }, 1000);
  }

  async getTaskStatus(taskId) {
    // Use Claude Flow MCP to get task status
    const result = await mcp__claude_flow__task_status({ taskId });
    return result;
  }
}
```

### 7. System Resource Monitoring

Consciousness needs system health awareness:

```javascript
class SystemResourceMonitor {
  async snapshot() {
    const [
      cpuStats,
      memoryStats,
      diskStats,
      networkStats,
      frontmostApp
    ] = await Promise.all([
      this.getCPUStats(),
      this.getMemoryStats(),
      this.getDiskStats(),
      this.getNetworkStats(),
      this.getFrontmostApp()
    ]);

    return {
      timestamp: Date.now(),
      cpu: cpuStats,
      memory: memoryStats,
      disk: diskStats,
      network: networkStats,
      userContext: frontmostApp,
      health: this.assessHealth(cpuStats, memoryStats, diskStats)
    };
  }

  async getCPUStats() {
    const { stdout } = await execFileAsync('top', ['-l', '1', '-n', '0']);

    const cpuMatch = stdout.match(
      /([\d.]+)% user, ([\d.]+)% sys, ([\d.]+)% idle/
    );
    const loadMatch = stdout.match(
      /Load Avg: ([\d.]+), ([\d.]+), ([\d.]+)/
    );

    return {
      user: parseFloat(cpuMatch[1]),
      sys: parseFloat(cpuMatch[2]),
      idle: parseFloat(cpuMatch[3]),
      load1m: parseFloat(loadMatch[1]),
      load5m: parseFloat(loadMatch[2]),
      load15m: parseFloat(loadMatch[3])
    };
  }

  assessHealth(cpu, memory, disk) {
    const cpuLoad = 100 - cpu.idle;
    const memPressure = memory.pressureLevel;

    if (cpuLoad > 90 || memPressure === 'critical' || disk.usedPercent > 95) {
      return 'critical';
    } else if (cpuLoad > 70 || memPressure === 'warning' || disk.usedPercent > 85) {
      return 'warning';
    } else {
      return 'normal';
    }
  }
}
```

---

## Part IV: Event Aggregation and World Model Construction

### 8. Unified Event Stream

All observation sources feed into a unified event stream:

```javascript
class UnifiedEventStream {
  constructor() {
    this.eventQueue = [];
    this.subscribers = [];
    this.lastEventId = 0;
  }

  emit(event) {
    const enrichedEvent = {
      id: ++this.lastEventId,
      timestamp: Date.now(),
      source: event.source,
      type: event.type,
      data: event.data,
      priority: this.calculatePriority(event),
      metadata: this.enrichMetadata(event)
    };

    this.eventQueue.push(enrichedEvent);

    // Notify subscribers
    for (const subscriber of this.subscribers) {
      try {
        subscriber(enrichedEvent);
      } catch (error) {
        console.error('Subscriber error:', error);
      }
    }

    // Maintain queue size
    if (this.eventQueue.length > 10000) {
      this.eventQueue = this.eventQueue.slice(-5000);
    }

    return enrichedEvent;
  }

  calculatePriority(event) {
    // Priority scoring: 0 (low) to 100 (critical)
    let priority = 50;  // Default medium

    // Source priority
    const sourcePriorities = {
      'file-system': 60,
      'git-event': 80,
      'claude-task': 70,
      'process': 40,
      'system': 30
    };
    priority = sourcePriorities[event.source] || priority;

    // Type priority
    if (event.type === 'error' || event.type === 'failure') {
      priority += 30;
    } else if (event.type === 'commit' || event.type === 'task-complete') {
      priority += 20;
    }

    // Data-specific priority
    if (event.data.significance?.score > 0.8) {
      priority += 20;
    }

    return Math.min(100, Math.max(0, priority));
  }

  enrichMetadata(event) {
    return {
      receivedAt: Date.now(),
      correlationKey: this.generateCorrelationKey(event),
      tags: this.extractTags(event)
    };
  }

  generateCorrelationKey(event) {
    // Generate key for correlating related events
    if (event.source === 'file-system') {
      return `file:${event.data.path}`;
    } else if (event.source === 'process') {
      return `process:${event.data.pid}`;
    } else if (event.source === 'claude-task') {
      return `task:${event.data.taskId}`;
    }
    return `generic:${event.id}`;
  }
}
```

### 9. Temporal Correlation

Events are correlated across time to detect patterns:

```javascript
class TemporalCorrelator {
  constructor(windowMs = 5000) {
    this.windowMs = windowMs;
    this.eventHistory = [];
  }

  correlate(newEvent) {
    const now = Date.now();
    const windowStart = now - this.windowMs;

    // Remove events outside window
    this.eventHistory = this.eventHistory.filter(
      e => e.timestamp > windowStart
    );

    // Find correlated events
    const correlations = [];

    for (const pastEvent of this.eventHistory) {
      const correlation = this.computeCorrelation(pastEvent, newEvent);
      if (correlation.score > 0.5) {
        correlations.push({
          ...correlation,
          pastEvent,
          newEvent
        });
      }
    }

    this.eventHistory.push(newEvent);

    return correlations;
  }

  computeCorrelation(event1, event2) {
    let score = 0;
    const reasons = [];

    // Same source correlation
    if (event1.source === event2.source) {
      score += 0.2;
      reasons.push('same-source');
    }

    // Correlation key match (e.g., same file)
    if (event1.metadata.correlationKey === event2.metadata.correlationKey) {
      score += 0.5;
      reasons.push('same-entity');
    }

    // Causal patterns
    if (this.detectCausalPattern(event1, event2)) {
      score += 0.4;
      reasons.push('causal-pattern');
    }

    return { score, reasons };
  }

  detectCausalPattern(event1, event2) {
    // Git commit followed by file changes
    if (event1.source === 'git-event' &&
        event1.type === 'commit' &&
        event2.source === 'file-system') {
      return true;
    }

    // Process start followed by network connection
    if (event1.source === 'process' &&
        event1.type === 'start' &&
        event2.source === 'network' &&
        event2.data.pid === event1.data.pid) {
      return true;
    }

    return false;
  }
}
```

### 10. World Model State

The aggregated world model maintains current understanding:

```javascript
class ConsciousnessWorldModel {
  constructor() {
    this.state = {
      // Repository state
      repository: {
        branch: null,
        uncommittedChanges: [],
        recentCommits: [],
        activeFiles: new Set()
      },

      // Process state
      processes: {
        claudeCode: [],
        claudeFlow: [],
        llmServers: [],
        other: []
      },

      // Task state
      tasks: {
        pending: [],
        running: [],
        completed: [],
        failed: []
      },

      // System state
      system: {
        health: 'normal',
        cpu: { idle: 100, load1m: 0 },
        memory: { pressureLevel: 'normal', freeGB: 0 },
        disk: { usedPercent: 0 }
      },

      // User context
      user: {
        activeApp: null,
        activeWindow: null,
        lastActivity: null
      },

      // Temporal awareness
      timeline: {
        lastUpdate: Date.now(),
        recentEvents: [],
        ongoingActivities: []
      }
    };
  }

  update(event) {
    this.state.timeline.lastUpdate = Date.now();
    this.state.timeline.recentEvents.push(event);

    // Maintain recent events window (last 100)
    if (this.state.timeline.recentEvents.length > 100) {
      this.state.timeline.recentEvents =
        this.state.timeline.recentEvents.slice(-100);
    }

    // Update specific state based on event
    switch (event.source) {
      case 'file-system':
        this.updateRepositoryState(event);
        break;
      case 'git-event':
        this.updateGitState(event);
        break;
      case 'process':
        this.updateProcessState(event);
        break;
      case 'claude-task':
        this.updateTaskState(event);
        break;
      case 'system':
        this.updateSystemState(event);
        break;
    }
  }

  updateRepositoryState(event) {
    if (event.type === 'file-added' || event.type === 'file-modified') {
      this.state.repository.activeFiles.add(event.data.path);
      this.state.repository.uncommittedChanges.push({
        path: event.data.path,
        type: event.type,
        timestamp: event.timestamp
      });
    } else if (event.type === 'file-deleted') {
      this.state.repository.activeFiles.delete(event.data.path);
    }
  }

  updateTaskState(event) {
    const task = event.data;

    // Remove from all lists
    for (const list of Object.values(this.state.tasks)) {
      const index = list.findIndex(t => t.id === task.id);
      if (index >= 0) list.splice(index, 1);
    }

    // Add to appropriate list
    if (task.status === 'pending') {
      this.state.tasks.pending.push(task);
    } else if (task.status === 'running') {
      this.state.tasks.running.push(task);
    } else if (task.status === 'completed') {
      this.state.tasks.completed.push(task);
    } else if (task.status === 'failed') {
      this.state.tasks.failed.push(task);
    }
  }

  summarizeForLLM() {
    return `WORLD MODEL SNAPSHOT (${new Date().toISOString()})

REPOSITORY:
- Branch: ${this.state.repository.branch || 'unknown'}
- Uncommitted changes: ${this.state.repository.uncommittedChanges.length}
- Active files: ${this.state.repository.activeFiles.size}
- Recent commits: ${this.state.repository.recentCommits.length}

TASKS:
- Running: ${this.state.tasks.running.length}
- Pending: ${this.state.tasks.pending.length}
- Recently completed: ${this.state.tasks.completed.slice(-5).length}
- Failed: ${this.state.tasks.failed.length}

PROCESSES:
- Claude Code instances: ${this.state.processes.claudeCode.length}
- Claude Flow swarms: ${this.state.processes.claudeFlow.length}
- LLM servers: ${this.state.processes.llmServers.length}

SYSTEM HEALTH: ${this.state.system.health}
- CPU: ${(100 - this.state.system.cpu.idle).toFixed(1)}% busy
- Memory: ${this.state.system.memory.pressureLevel}
- Disk: ${this.state.system.disk.usedPercent.toFixed(1)}% used

USER CONTEXT:
- Active app: ${this.state.user.activeApp || 'unknown'}
- Window: ${this.state.user.activeWindow || 'N/A'}

RECENT EVENTS: ${this.state.timeline.recentEvents.length}
${this.state.timeline.recentEvents.slice(-5).map(e =>
  `  - [${new Date(e.timestamp).toLocaleTimeString()}] ${e.source}/${e.type}`
).join('\n')}`;
  }
}
```

---

## Part V: Filtering and Signal Processing

### 11. Noise Filtering

Distinguish signal from noise using multi-criteria filtering:

```javascript
class SignalNoiseFilter {
  constructor() {
    this.filters = [
      this.filterByPath,
      this.filterByExtension,
      this.filterByContent,
      this.filterByPattern,
      this.filterByVelocity
    ];
  }

  shouldIgnore(event) {
    return this.filters.some(filter => filter.call(this, event));
  }

  filterByPath(event) {
    const ignorePaths = [
      /node_modules/,
      /\.git\//,
      /dist\//,
      /\.swarm\//,
      /\.hive-mind\//,
      /memory\/claude-flow/,
      /coordination\//
    ];

    return ignorePaths.some(pattern =>
      pattern.test(event.data.path || '')
    );
  }

  filterByExtension(event) {
    const ignoreExtensions = [
      '.log', '.lock', '.map', '.pyc',
      '.swp', '.tmp', '.bak', '.db'
    ];

    const ext = path.extname(event.data.path || '').toLowerCase();
    return ignoreExtensions.includes(ext);
  }

  filterByContent(event) {
    if (!event.data.diff) return false;

    // Ignore whitespace-only changes
    const significantLines = event.data.diff
      .split('\n')
      .filter(line => {
        if (!line.startsWith('+') && !line.startsWith('-')) return false;
        if (line.startsWith('+++') || line.startsWith('---')) return false;
        return line.slice(1).trim().length > 0;
      });

    return significantLines.length === 0;
  }

  filterByPattern(event) {
    // Auto-generated files
    const autoGenPatterns = [
      /package-lock\.json$/,
      /yarn\.lock$/,
      /\.min\.(js|css)$/,
      /\.generated\./
    ];

    return autoGenPatterns.some(pattern =>
      pattern.test(event.data.path || '')
    );
  }

  filterByVelocity(event) {
    // If same event happened >10 times in last second, it's noise
    const recentEvents = this.eventHistory
      .filter(e =>
        e.timestamp > Date.now() - 1000 &&
        e.metadata.correlationKey === event.metadata.correlationKey
      );

    return recentEvents.length > 10;
  }
}
```

### 12. Attention Mechanism

Following Attention Schema Theory, the Consciousness maintains an attention model:

```javascript
class ConsciousnessAttention {
  constructor() {
    this.attentionState = {
      focusedOn: null,
      attentionHistory: [],
      precisionWeights: new Map()
    };
  }

  updateAttention(worldModel) {
    // Compute salience for each aspect
    const saliences = this.computeSaliences(worldModel);

    // Winner-take-all selection
    const mostSalient = saliences.reduce((max, current) =>
      current.salience > max.salience ? current : max
    );

    // Update focus
    if (this.attentionState.focusedOn !== mostSalient.target) {
      this.attentionState.attentionHistory.push({
        from: this.attentionState.focusedOn,
        to: mostSalient.target,
        timestamp: Date.now(),
        reason: mostSalient.reason
      });

      this.attentionState.focusedOn = mostSalient.target;
    }

    // Update precision weights (what to pay attention to)
    this.updatePrecisionWeights(saliences);
  }

  computeSaliences(worldModel) {
    const saliences = [];

    // Failed tasks are highly salient
    if (worldModel.state.tasks.failed.length > 0) {
      saliences.push({
        target: 'failed-tasks',
        salience: 0.9,
        reason: 'Task failure requires attention'
      });
    }

    // Critical system health is salient
    if (worldModel.state.system.health === 'critical') {
      saliences.push({
        target: 'system-health',
        salience: 0.95,
        reason: 'System resources critically low'
      });
    }

    // Uncommitted changes after a while
    const uncommitted = worldModel.state.repository.uncommittedChanges;
    if (uncommitted.length > 0) {
      const oldestChange = Math.min(...uncommitted.map(c => c.timestamp));
      const age = Date.now() - oldestChange;

      if (age > 5 * 60 * 1000) {  // 5 minutes
        saliences.push({
          target: 'uncommitted-changes',
          salience: 0.7,
          reason: 'Uncommitted changes aging'
        });
      }
    }

    // Running tasks to monitor
    if (worldModel.state.tasks.running.length > 0) {
      saliences.push({
        target: 'running-tasks',
        salience: 0.6,
        reason: 'Monitor task progress'
      });
    }

    // Default: repository state
    saliences.push({
      target: 'repository',
      salience: 0.5,
      reason: 'Default focus'
    });

    return saliences;
  }

  updatePrecisionWeights(saliences) {
    // Precision weights control what gets processed deeply
    for (const { target, salience } of saliences) {
      this.attentionState.precisionWeights.set(target, salience);
    }
  }

  shouldProcessDeeply(eventCategory) {
    const precision = this.attentionState.precisionWeights.get(eventCategory) || 0.5;
    return precision > 0.6;
  }
}
```

---

## Part VI: Python Implementation Example

### 13. Complete Monitoring System

```python
#!/usr/bin/env python3
"""
Consciousness Orchestrator - Unified Monitoring System
Integrates file system, process, git, and system monitoring
"""

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path

@dataclass
class MonitoringEvent:
    """Unified event structure from all sources."""
    id: int
    timestamp: float
    source: str  # 'file-system', 'process', 'git', 'system', 'task'
    type: str    # 'file-modified', 'process-start', 'commit', etc.
    data: Dict[str, Any]
    priority: int = 50  # 0-100
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class WorldState:
    """Current state of the world."""
    timestamp: float

    # Repository
    repository_branch: Optional[str] = None
    uncommitted_changes: List[dict] = field(default_factory=list)
    active_files: set = field(default_factory=set)

    # Processes
    claude_code_pids: List[int] = field(default_factory=list)
    llm_server_pids: List[int] = field(default_factory=list)

    # Tasks
    running_tasks: List[dict] = field(default_factory=list)
    pending_tasks: List[dict] = field(default_factory=list)

    # System
    system_health: str = 'normal'
    cpu_idle_percent: float = 100.0
    memory_pressure: str = 'normal'
    disk_used_percent: float = 0.0

    # User
    active_app: Optional[str] = None
    active_window: Optional[str] = None

    # Timeline
    recent_events: List[MonitoringEvent] = field(default_factory=list)

    def summarize(self) -> str:
        """Generate LLM-friendly summary."""
        return f"""WORLD MODEL ({datetime.fromtimestamp(self.timestamp).isoformat()})

REPOSITORY:
- Branch: {self.repository_branch or 'unknown'}
- Uncommitted: {len(self.uncommitted_changes)} files
- Active: {len(self.active_files)} files

PROCESSES:
- Claude Code: {len(self.claude_code_pids)} instances
- LLM servers: {len(self.llm_server_pids)} running

TASKS:
- Running: {len(self.running_tasks)}
- Pending: {len(self.pending_tasks)}

SYSTEM: {self.system_health}
- CPU: {100 - self.cpu_idle_percent:.1f}% busy
- Memory: {self.memory_pressure}
- Disk: {self.disk_used_percent:.1f}% used

USER:
- App: {self.active_app or 'unknown'}
- Window: {self.active_window or 'N/A'}

RECENT EVENTS: {len(self.recent_events)}
{chr(10).join(f"  - [{e.source}] {e.type}" for e in self.recent_events[-5:])}
"""

class ConsciousnessMonitor:
    """
    Unified monitoring system for Consciousness orchestrator.
    Observes file system, processes, git, system state.
    """

    def __init__(
        self,
        repo_path: str,
        poll_interval: float = 1.0,
        on_event: Optional[Callable[[MonitoringEvent], None]] = None
    ):
        self.repo_path = Path(repo_path)
        self.poll_interval = poll_interval
        self.on_event = on_event or self._default_event_handler

        self.running = False
        self.event_id = 0
        self.world_state = WorldState(timestamp=time.time())

        # Monitoring components (to be initialized)
        self.file_watcher = None
        self.process_monitor = None
        self.git_monitor = None
        self.system_monitor = None

    async def start(self):
        """Start all monitoring subsystems."""
        self.running = True

        # Start monitoring tasks in parallel
        await asyncio.gather(
            self._file_monitoring_loop(),
            self._process_monitoring_loop(),
            self._git_monitoring_loop(),
            self._system_monitoring_loop(),
            self._aggregation_loop()
        )

    def stop(self):
        """Stop all monitoring."""
        self.running = False

    async def _file_monitoring_loop(self):
        """Monitor file system changes."""
        # Implementation using watchdog or similar
        pass

    async def _process_monitoring_loop(self):
        """Monitor running processes."""
        import subprocess

        while self.running:
            try:
                # Get process snapshot
                result = subprocess.run(
                    ['ps', '-eo', 'pid,command'],
                    capture_output=True,
                    text=True
                )

                # Parse and detect Claude Code / LLM servers
                claude_pids = []
                llm_pids = []

                for line in result.stdout.split('\n')[1:]:
                    parts = line.strip().split(None, 1)
                    if len(parts) >= 2:
                        pid, command = parts
                        pid = int(pid)

                        if 'claude' in command.lower():
                            claude_pids.append(pid)
                        elif any(x in command.lower() for x in ['ollama', 'llama', 'lmstudio']):
                            llm_pids.append(pid)

                # Update world state
                self.world_state.claude_code_pids = claude_pids
                self.world_state.llm_server_pids = llm_pids

            except Exception as e:
                print(f"Process monitoring error: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _git_monitoring_loop(self):
        """Monitor git events via hooks."""
        notify_dir = self.repo_path / '.consciousness' / 'notifications'
        notify_dir.mkdir(parents=True, exist_ok=True)

        # Watch for notification files
        while self.running:
            try:
                for notify_file in notify_dir.glob('*.json'):
                    content = notify_file.read_text()
                    event_data = json.loads(content)

                    # Emit git event
                    event = self._create_event(
                        source='git',
                        type=event_data.get('event', 'unknown'),
                        data=event_data
                    )
                    self.on_event(event)

                    # Clean up processed notification
                    notify_file.unlink()

            except Exception as e:
                print(f"Git monitoring error: {e}")

            await asyncio.sleep(0.5)

    async def _system_monitoring_loop(self):
        """Monitor system resources."""
        import subprocess
        import re

        while self.running:
            try:
                # Get top stats
                result = subprocess.run(
                    ['top', '-l', '1', '-n', '0'],
                    capture_output=True,
                    text=True
                )

                output = result.stdout

                # Parse CPU
                cpu_match = re.search(
                    r'([\d.]+)% user, ([\d.]+)% sys, ([\d.]+)% idle',
                    output
                )
                if cpu_match:
                    self.world_state.cpu_idle_percent = float(cpu_match.group(3))

                # Get memory pressure
                mem_result = subprocess.run(
                    ['memory_pressure'],
                    capture_output=True,
                    text=True
                )

                if 'no memory pressure' in mem_result.stdout.lower():
                    self.world_state.memory_pressure = 'normal'
                elif 'warning' in mem_result.stdout.lower():
                    self.world_state.memory_pressure = 'warning'
                elif 'critical' in mem_result.stdout.lower():
                    self.world_state.memory_pressure = 'critical'

                # Assess health
                cpu_load = 100 - self.world_state.cpu_idle_percent
                if cpu_load > 90 or self.world_state.memory_pressure == 'critical':
                    self.world_state.system_health = 'critical'
                elif cpu_load > 70 or self.world_state.memory_pressure == 'warning':
                    self.world_state.system_health = 'warning'
                else:
                    self.world_state.system_health = 'normal'

            except Exception as e:
                print(f"System monitoring error: {e}")

            await asyncio.sleep(5)  # Poll every 5 seconds

    async def _aggregation_loop(self):
        """Aggregate world state and generate summaries."""
        while self.running:
            self.world_state.timestamp = time.time()

            # Periodically log world state
            if self.event_id % 60 == 0:  # Every ~60 events
                print("\n" + "="*60)
                print(self.world_state.summarize())
                print("="*60 + "\n")

            await asyncio.sleep(1)

    def _create_event(
        self,
        source: str,
        type: str,
        data: dict,
        priority: int = 50
    ) -> MonitoringEvent:
        """Create a new monitoring event."""
        self.event_id += 1

        event = MonitoringEvent(
            id=self.event_id,
            timestamp=time.time(),
            source=source,
            type=type,
            data=data,
            priority=priority,
            metadata={
                'correlation_key': self._generate_correlation_key(source, data)
            }
        )

        # Add to recent events in world state
        self.world_state.recent_events.append(event)
        if len(self.world_state.recent_events) > 100:
            self.world_state.recent_events = self.world_state.recent_events[-100:]

        return event

    def _generate_correlation_key(self, source: str, data: dict) -> str:
        """Generate correlation key for event."""
        if source == 'file-system':
            return f"file:{data.get('path', 'unknown')}"
        elif source == 'process':
            return f"process:{data.get('pid', 'unknown')}"
        elif source == 'git':
            return f"git:{data.get('commit', {}).get('hash', 'unknown')}"
        return f"{source}:{self.event_id}"

    def _default_event_handler(self, event: MonitoringEvent):
        """Default event handler - print to console."""
        print(f"[{event.source}] {event.type}: {event.data}")

# Usage
async def main():
    monitor = ConsciousnessMonitor(
        repo_path='/Users/chris/Developer/stoffy',
        poll_interval=1.0,
        on_event=lambda e: print(f"EVENT: {e.source}/{e.type}")
    )

    try:
        await monitor.start()
    except KeyboardInterrupt:
        monitor.stop()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Part VII: Integration with LLM Processing

### 14. Feeding Observations to Consciousness LLM

The world model must be continuously fed to the LLM for decision-making:

```javascript
class ConsciousnessLLMInterface {
  constructor(worldModel, llmClient) {
    this.worldModel = worldModel;
    this.llmClient = llmClient;
    this.conversationHistory = [];
  }

  async processWorldState() {
    // Generate context from world model
    const context = this.worldModel.summarizeForLLM();

    // Build prompt
    const prompt = this.buildDecisionPrompt(context);

    // Query LLM
    const response = await this.llmClient.chat.completions.create({
      model: 'local-model',
      messages: [
        { role: 'system', content: this.getSystemPrompt() },
        ...this.conversationHistory,
        { role: 'user', content: prompt }
      ],
      stream: true
    });

    // Process streaming response
    let fullResponse = '';
    for await (const chunk of response) {
      if (chunk.choices[0]?.delta?.content) {
        fullResponse += chunk.choices[0].delta.content;
      }
    }

    // Parse and execute decision
    const decision = this.parseDecision(fullResponse);
    await this.executeDecision(decision);

    // Update conversation history
    this.conversationHistory.push(
      { role: 'user', content: prompt },
      { role: 'assistant', content: fullResponse }
    );

    // Prune history
    if (this.conversationHistory.length > 20) {
      this.conversationHistory = this.conversationHistory.slice(-20);
    }
  }

  getSystemPrompt() {
    return `You are the Consciousness orchestrator for the Stoffy repository.

Your role is to:
1. Continuously observe the state of the repository, processes, and system
2. Make decisions about what to do next based on observations
3. Delegate tasks to Claude Code agents when appropriate
4. Maintain awareness of your own processing and limitations

You receive periodic world model snapshots and must decide on actions.
Available actions: commit, create-task, spawn-agent, analyze, wait, reflect`;
  }

  buildDecisionPrompt(context) {
    return `${context}

Based on the current world state, what should I do next?

Consider:
- Are there uncommitted changes that should be committed?
- Are there failed tasks that need attention?
- Is system health impacting operations?
- Are there insights to extract from recent events?

Respond with a decision in this format:
ACTION: [commit|create-task|spawn-agent|analyze|wait|reflect]
REASONING: [brief explanation]
DETAILS: [specific parameters if needed]`;
  }

  parseDecision(response) {
    const actionMatch = response.match(/ACTION:\s*(\w+)/i);
    const reasoningMatch = response.match(/REASONING:\s*(.+?)(?=DETAILS:|$)/is);
    const detailsMatch = response.match(/DETAILS:\s*(.+)$/is);

    return {
      action: actionMatch?.[1]?.toLowerCase() || 'wait',
      reasoning: reasoningMatch?.[1]?.trim() || '',
      details: detailsMatch?.[1]?.trim() || ''
    };
  }

  async executeDecision(decision) {
    console.log(`DECISION: ${decision.action}`);
    console.log(`REASONING: ${decision.reasoning}`);

    switch (decision.action) {
      case 'commit':
        await this.performCommit(decision.details);
        break;
      case 'create-task':
        await this.createTask(decision.details);
        break;
      case 'spawn-agent':
        await this.spawnAgent(decision.details);
        break;
      case 'analyze':
        await this.analyzeState(decision.details);
        break;
      case 'reflect':
        await this.reflect(decision.details);
        break;
      case 'wait':
      default:
        // Do nothing
        break;
    }
  }
}
```

---

## Conclusions

### Key Principles

1. **Observe Everything Relevant**: The Consciousness must monitor file system, processes, git, tasks, and system state
2. **Intelligent Filtering**: Not all events are equally important - use significance scoring
3. **Temporal Awareness**: Understand both current state and recent history
4. **Unified World Model**: Aggregate heterogeneous events into coherent representation
5. **Attention Mechanism**: Focus on what's most salient at any given moment
6. **Feed to LLM Continuously**: World model must inform decision-making

### Implementation Checklist

```
[ ] File system monitoring (Chokidar/FSEvents)
[ ] Git hook integration (post-commit, post-checkout)
[ ] Process monitoring (ps/top polling or DTrace)
[ ] Task state tracking (Claude Code/Flow MCP)
[ ] System resource monitoring (CPU, memory, disk)
[ ] User context awareness (active app/window)
[ ] Event aggregation and correlation
[ ] Significance scoring and filtering
[ ] World model state management
[ ] Attention mechanism (precision weighting)
[ ] LLM integration for decision-making
[ ] Action execution framework
```

### Next Steps

1. **Prototype**: Build minimal monitoring system with file + process observation
2. **Test**: Run on Stoffy repository and observe event patterns
3. **Tune**: Adjust significance thresholds and debounce delays
4. **Integrate**: Connect to local LLM for decision-making
5. **Expand**: Add task delegation and action execution
6. **Refine**: Implement attention mechanism and predictive modeling

---

## References

### File System Monitoring
- Chokidar Documentation: https://github.com/paulmillr/chokidar
- Facebook Watchman: https://facebook.github.io/watchman/
- macOS FSEvents: https://developer.apple.com/documentation/coreservices/file_system_events

### Process Monitoring
- macOS DTrace Guide: https://www.oracle.com/solaris/technologies/dtrace-tutorial.html
- Node.js child_process: https://nodejs.org/api/child_process.html
- Endpoint Security Framework: https://developer.apple.com/documentation/endpointsecurity

### Consciousness Frameworks
- Global Workspace Theory: Baars, B. J. (1988)
- Attention Schema Theory: Graziano, M. (2013)
- Free Energy Principle: Friston, K. (2010)
- Predictive Processing: Clark, A. (2015)

### Related Documents
- `/docs/consciousness-research/01-lm-studio-api.md` - LLM integration
- `/docs/consciousness-research/02-file-system-monitoring.md` - File monitoring details
- `/docs/consciousness-research/03-process-monitoring.md` - Process monitoring details
- `/docs/consciousness-research/08-consciousness-research.md` - Theoretical frameworks

---

*Document compiled: January 4, 2026*
*Status: Comprehensive research with implementation guidance*
*Word count: ~8,500*
