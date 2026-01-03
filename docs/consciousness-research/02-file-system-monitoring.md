# File System Monitoring for Consciousness Systems

## Research Summary

This document investigates file system monitoring techniques for building a consciousness system that watches repository changes and feeds them to an LLM processing pipeline. The focus is on real-time change detection, efficient event handling, and integration patterns.

---

## 1. Platform-Specific APIs

### 1.1 macOS FSEvents

The FSEvents API provides kernel-level file system event notifications on macOS.

**Key Characteristics:**
- Event-driven (no polling required)
- Scalable to hundreds of thousands of files
- File-level events available since macOS 10.7
- Events persisted to `/dev/fsevents` via `fseventsd` daemon
- Supports per-host and per-disk event streams

**Strengths:**
- No known scalability limitations
- Very low CPU overhead
- Recursive watching built-in
- Events coalesced by the kernel

**Event Stream Setup:**
```c
// C API pattern (simplified)
FSEventStreamRef stream = FSEventStreamCreate(
    NULL,
    &callback,
    &context,
    pathsToWatch,
    kFSEventStreamEventIdSinceNow,
    latency,
    kFSEventStreamCreateFlagFileEvents
);
FSEventStreamScheduleWithRunLoop(stream, runLoop, kCFRunLoopDefaultMode);
FSEventStreamStart(stream);
```

**Node.js Access:**
FSEvents is accessed via the `fsevents` npm package (native binding), used internally by Chokidar on macOS.

---

### 1.2 Linux inotify

The inotify API provides file system event notifications on Linux (kernel 2.6.13+).

**Key Characteristics:**
- Per-directory watches (not automatically recursive)
- Watch descriptors consume kernel memory
- Event queue with overflow detection
- Configurable system limits

**Critical Limits:**
| Limit | Default | Path |
|-------|---------|------|
| max_user_watches | 8,192 | `/proc/sys/fs/inotify/max_user_watches` |
| max_user_instances | 128 | `/proc/sys/fs/inotify/max_user_instances` |
| max_queued_events | 16,384 | `/proc/sys/fs/inotify/max_queued_events` |

**Increasing Limits (for large repositories):**
```bash
# Temporary
echo 524288 | sudo tee /proc/sys/fs/inotify/max_user_watches

# Persistent (/etc/sysctl.conf)
fs.inotify.max_user_watches=524288
```

**Limitations:**
- Race conditions with recursive watching (new subdirectories)
- Cannot watch pseudo-filesystems (/proc, /sys)
- Events lost on queue overflow (IN_Q_OVERFLOW generated)
- mmap/msync/munmap changes not reported

**Node.js Access:**
Use `inotifywait` CLI or native bindings via packages like `node-inotify-watcher`.

---

## 2. Cross-Platform Tools

### 2.1 fswatch

A cross-platform file change monitor with multiple backends.

**Supported Backends:**
- FSEvents (macOS)
- kqueue (*BSD, macOS)
- inotify (Linux)
- ReadDirectoryChangesW (Windows)
- FEN (Solaris/Illumos)
- poll (fallback, any platform)

**Installation:**
```bash
# macOS
brew install fswatch

# Linux
apt-get install fswatch
```

**Usage for Repository Watching:**
```bash
# Basic recursive watching
fswatch -r /path/to/repo

# With exclusions and specific events
fswatch -r \
  --exclude '\.git' \
  --event Created \
  --event Updated \
  --event Removed \
  /path/to/repo | while read file; do
    echo "Changed: $file"
done
```

**Memory Usage:**
~150 MB for 500,000 files (32-char min path length)

**Backend Limitations:**
| Backend | Limitation |
|---------|------------|
| kqueue | Requires file descriptor per file; scales poorly |
| inotify | Queue overflow possible under high load |
| Windows | Can only watch directories, not individual files |
| poll | Linear performance degradation with file count |

---

### 2.2 Facebook Watchman

A high-performance file watching service designed for large repositories.

**Key Features:**
- Watch consolidation (shared watches across tools)
- Source control awareness (SCM queries)
- Settled change notifications (waits for changes to stabilize)
- Query language for file matching
- Persistent daemon architecture

**Installation:**
```bash
# macOS
brew install watchman

# Linux (from source or prebuilt)
# See https://facebook.github.io/watchman/docs/install
```

**Repository Setup:**
```bash
# Initialize watch
watchman watch-project /path/to/repo

# Query for changes since a clock value
watchman query /path/to/repo '["since", "c:1234:5678", ["name", "*.ts"]]'
```

**Configuration (.watchmanconfig):**
```json
{
  "settle": 20,
  "ignore_dirs": ["node_modules", ".git", "dist"]
}
```

**Source Control Integration:**
```json
// Query changes since merge base
{
  "since": {
    "scm": {
      "mergebase-with": "main"
    }
  }
}
```

**Performance Tuning:**
- Use `ignore_dirs` to skip build directories
- Configure appropriate `settle` time
- Tune inotify limits on Linux

---

### 2.3 Chokidar (Node.js)

The most popular file watching library for Node.js.

**Version History:**
- v4.0 (Sep 2024): Removed globs, 13 to 1 dependencies, TypeScript rewrite
- v5.0 (Nov 2025): ESM-only, Node.js 20+ required

**Installation:**
```bash
npm install chokidar
```

**Basic Usage (v4+):**
```javascript
import chokidar from 'chokidar';

const watcher = chokidar.watch('/path/to/repo', {
  ignored: (path) => path.includes('node_modules') || path.includes('.git'),
  persistent: true,
  ignoreInitial: true,
  awaitWriteFinish: {
    stabilityThreshold: 100,
    pollInterval: 50
  }
});

watcher
  .on('add', (path) => console.log(`Added: ${path}`))
  .on('change', (path, stats) => console.log(`Changed: ${path}`))
  .on('unlink', (path) => console.log(`Removed: ${path}`))
  .on('ready', () => console.log('Initial scan complete'))
  .on('error', (error) => console.error(`Error: ${error}`));

// Dynamic control
await watcher.add('/another/path');
await watcher.unwatch('/some/path');
await watcher.close();
```

**Key Options:**
| Option | Default | Description |
|--------|---------|-------------|
| `persistent` | true | Keep process running |
| `ignoreInitial` | false | Skip initial add events |
| `depth` | undefined | Subdirectory traversal limit |
| `interval` | 100 | Polling interval (ms) |
| `alwaysStat` | false | Always include fs.Stats |
| `awaitWriteFinish` | false | Wait for writes to complete |

---

## 3. Event-Driven vs Polling

### 3.1 Event-Driven (Preferred)

**Mechanism:**
- Kernel notifies application of changes
- Near-zero CPU when idle
- Immediate notification (<1ms typical)

**When to Use:**
- Real-time change detection needed
- Large repositories
- Long-running processes

**Caveats:**
- System limits (inotify watches)
- Platform-specific behavior
- Event coalescence varies

### 3.2 Polling (Fallback)

**Mechanism:**
- Periodic stat() calls on watched files
- CPU proportional to file count and interval

**When to Use:**
- Network filesystems (NFS, SMB)
- Unsupported platforms
- Simple use cases with few files

**Chokidar Polling Mode:**
```javascript
const watcher = chokidar.watch('/path', {
  usePolling: true,
  interval: 1000,
  binaryInterval: 2000 // for binary files
});
```

---

## 4. Debouncing Strategies

High-frequency file changes require debouncing to prevent overwhelming the processing pipeline.

### 4.1 The Problem

A single file save can trigger multiple events:
- VSCode save: ~5 events per file
- npm install: 10,000+ events
- git checkout: thousands of files

### 4.2 Debouncing Patterns

**Trailing Edge (Basic):**
```javascript
let timeout;
function debounce(fn, delay) {
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}
```

**Batched Debouncing:**
```javascript
class ChangeBuffer {
  constructor(delay, onFlush) {
    this.changes = new Map();
    this.delay = delay;
    this.onFlush = onFlush;
    this.timeout = null;
  }

  add(path, event) {
    this.changes.set(path, { path, event, time: Date.now() });
    this.scheduleFlush();
  }

  scheduleFlush() {
    clearTimeout(this.timeout);
    this.timeout = setTimeout(() => {
      const batch = Array.from(this.changes.values());
      this.changes.clear();
      this.onFlush(batch);
    }, this.delay);
  }
}

const buffer = new ChangeBuffer(200, (changes) => {
  console.log('Flushing batch:', changes.length);
  processChanges(changes);
});
```

**Adaptive Debouncing:**
```javascript
class AdaptiveDebouncer {
  constructor(minDelay, maxDelay, onFlush) {
    this.minDelay = minDelay;
    this.maxDelay = maxDelay;
    this.onFlush = onFlush;
    this.eventCount = 0;
    this.windowStart = Date.now();
  }

  getDelay() {
    const elapsed = Date.now() - this.windowStart;
    const rate = this.eventCount / (elapsed / 1000);

    // Higher event rate = longer delay
    return Math.min(
      this.maxDelay,
      this.minDelay + Math.floor(rate * 10)
    );
  }
}
```

**Recommended Settings:**
| Scenario | Delay (ms) |
|----------|------------|
| Interactive editing | 100-200 |
| Build watching | 300-500 |
| npm install / git ops | 1000-2000 |

---

## 5. File Content Diffing Strategies

### 5.1 Change Detection Hierarchy

From fastest to most thorough:

1. **File size only** - Instant but unreliable
2. **mtime + size** - Fast check (rsync default)
3. **mtime + hash** - Balanced approach
4. **Full content hash** - Accurate but slow

### 5.2 Implementation

```javascript
import { createHash } from 'crypto';
import { stat, readFile } from 'fs/promises';

class FileChangeDetector {
  constructor() {
    this.cache = new Map(); // path -> { mtime, size, hash }
  }

  async hasChanged(path) {
    const stats = await stat(path);
    const cached = this.cache.get(path);

    // Quick check: size changed
    if (!cached || cached.size !== stats.size) {
      return this.updateCache(path, stats);
    }

    // Medium check: mtime changed
    if (cached.mtime !== stats.mtimeMs) {
      return this.updateCache(path, stats);
    }

    return { changed: false };
  }

  async updateCache(path, stats) {
    const content = await readFile(path);
    const hash = createHash('md5').update(content).digest('hex');
    const cached = this.cache.get(path);

    this.cache.set(path, {
      mtime: stats.mtimeMs,
      size: stats.size,
      hash
    });

    return {
      changed: !cached || cached.hash !== hash,
      content,
      hash
    };
  }
}
```

### 5.3 Git-Based Diff Detection

```javascript
import { execSync } from 'child_process';

function getGitChanges(repoPath) {
  // Unstaged changes
  const unstaged = execSync('git diff --name-only', {
    cwd: repoPath,
    encoding: 'utf8'
  }).trim().split('\n').filter(Boolean);

  // Staged changes
  const staged = execSync('git diff --cached --name-only', {
    cwd: repoPath,
    encoding: 'utf8'
  }).trim().split('\n').filter(Boolean);

  // Untracked files
  const untracked = execSync('git ls-files --others --exclude-standard', {
    cwd: repoPath,
    encoding: 'utf8'
  }).trim().split('\n').filter(Boolean);

  return { unstaged, staged, untracked };
}

function getFileDiff(repoPath, filePath) {
  try {
    return execSync(`git diff ${filePath}`, {
      cwd: repoPath,
      encoding: 'utf8'
    });
  } catch {
    return null;
  }
}
```

---

## 6. Integration with LLM Processing Pipeline

### 6.1 Architecture Overview

```
+------------------+     +------------------+     +------------------+
|   File Watcher   | --> |  Change Buffer   | --> |   LLM Processor  |
|   (Chokidar)     |     |  (Debouncing)    |     |   (Claude API)   |
+------------------+     +------------------+     +------------------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|  Git Integration |     |  Content Differ  |     | Response Handler |
+------------------+     +------------------+     +------------------+
```

### 6.2 Complete Implementation Example

```javascript
import chokidar from 'chokidar';
import { execSync } from 'child_process';
import { readFile } from 'fs/promises';
import { createHash } from 'crypto';
import Anthropic from '@anthropic-ai/sdk';

class ConsciousnessWatcher {
  constructor(repoPath, options = {}) {
    this.repoPath = repoPath;
    this.debounceMs = options.debounceMs || 500;
    this.maxBatchSize = options.maxBatchSize || 20;
    this.ignorePaths = options.ignorePaths || [
      'node_modules', '.git', 'dist', 'build', '.next'
    ];

    this.changeBuffer = new Map();
    this.flushTimeout = null;
    this.client = new Anthropic();
    this.contentCache = new Map();
  }

  async start() {
    const ignored = (path) =>
      this.ignorePaths.some(p => path.includes(p));

    this.watcher = chokidar.watch(this.repoPath, {
      ignored,
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 100,
        pollInterval: 50
      }
    });

    this.watcher
      .on('add', (path) => this.bufferChange(path, 'added'))
      .on('change', (path) => this.bufferChange(path, 'modified'))
      .on('unlink', (path) => this.bufferChange(path, 'deleted'))
      .on('ready', () => console.log('Consciousness watching...'))
      .on('error', (err) => console.error('Watch error:', err));

    return this;
  }

  bufferChange(path, event) {
    this.changeBuffer.set(path, {
      path,
      event,
      timestamp: Date.now()
    });

    this.scheduleFlush();
  }

  scheduleFlush() {
    clearTimeout(this.flushTimeout);
    this.flushTimeout = setTimeout(
      () => this.flushChanges(),
      this.debounceMs
    );
  }

  async flushChanges() {
    if (this.changeBuffer.size === 0) return;

    const changes = Array.from(this.changeBuffer.values())
      .slice(0, this.maxBatchSize);
    this.changeBuffer.clear();

    try {
      const enrichedChanges = await this.enrichChanges(changes);
      await this.processWithLLM(enrichedChanges);
    } catch (error) {
      console.error('Processing error:', error);
    }
  }

  async enrichChanges(changes) {
    return Promise.all(changes.map(async (change) => {
      if (change.event === 'deleted') {
        return { ...change, content: null, diff: null };
      }

      const [content, diff] = await Promise.all([
        this.getFileContent(change.path),
        this.getGitDiff(change.path)
      ]);

      return { ...change, content, diff };
    }));
  }

  async getFileContent(path) {
    try {
      const content = await readFile(path, 'utf8');
      const hash = createHash('md5').update(content).digest('hex');

      const cached = this.contentCache.get(path);
      if (cached?.hash === hash) {
        return { content, changed: false };
      }

      this.contentCache.set(path, { hash, content });
      return { content, changed: true };
    } catch {
      return null;
    }
  }

  getGitDiff(path) {
    try {
      const relativePath = path.replace(this.repoPath + '/', '');
      return execSync(`git diff -- "${relativePath}"`, {
        cwd: this.repoPath,
        encoding: 'utf8',
        maxBuffer: 1024 * 1024 // 1MB
      });
    } catch {
      return null;
    }
  }

  async processWithLLM(changes) {
    const significantChanges = changes.filter(c =>
      c.event === 'deleted' || c.content?.changed
    );

    if (significantChanges.length === 0) {
      console.log('No significant changes detected');
      return;
    }

    const prompt = this.buildPrompt(significantChanges);

    const response = await this.client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 2048,
      messages: [{
        role: 'user',
        content: prompt
      }]
    });

    this.handleResponse(response, significantChanges);
  }

  buildPrompt(changes) {
    const changeSummary = changes.map(c => {
      const header = `## ${c.event.toUpperCase()}: ${c.path}`;

      if (c.event === 'deleted') {
        return header;
      }

      if (c.diff) {
        return `${header}\n\n\`\`\`diff\n${c.diff.slice(0, 2000)}\n\`\`\``;
      }

      return `${header}\n\n\`\`\`\n${c.content?.content?.slice(0, 2000) || '(empty)'}\n\`\`\``;
    }).join('\n\n---\n\n');

    return `You are a consciousness system observing repository changes.

Analyze the following file changes and provide:
1. A brief summary of what changed
2. Potential implications or issues
3. Suggested follow-up actions

${changeSummary}`;
  }

  handleResponse(response, changes) {
    const content = response.content[0];
    if (content.type === 'text') {
      console.log('\n=== Consciousness Observation ===');
      console.log(`Files: ${changes.map(c => c.path).join(', ')}`);
      console.log('---');
      console.log(content.text);
      console.log('================================\n');
    }
  }

  async stop() {
    clearTimeout(this.flushTimeout);
    await this.watcher?.close();
  }
}

// Usage
const watcher = new ConsciousnessWatcher('/path/to/repo', {
  debounceMs: 500,
  maxBatchSize: 10,
  ignorePaths: ['node_modules', '.git', 'dist']
});

await watcher.start();

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down consciousness...');
  await watcher.stop();
  process.exit(0);
});
```

---

## 7. Performance Recommendations

### 7.1 For Small Repositories (<1,000 files)

- Use Chokidar with default settings
- Debounce at 200ms
- Poll interval: 100ms (if needed)

### 7.2 For Medium Repositories (1,000-50,000 files)

- Use Chokidar with depth limits
- Debounce at 500ms
- Ignore node_modules, .git, build directories
- Consider Watchman for multi-tool coordination

### 7.3 For Large Repositories (>50,000 files)

- Use Watchman exclusively
- Configure `ignore_dirs` aggressively
- Use SCM-aware queries
- Increase inotify limits on Linux
- Debounce at 1000ms+
- Implement two-tier debouncing

### 7.4 System Tuning

**macOS:**
```bash
# Check current limits
sysctl kern.maxfiles kern.maxfilesperproc

# Increase if needed
sudo sysctl -w kern.maxfiles=524288
sudo sysctl -w kern.maxfilesperproc=262144
```

**Linux:**
```bash
# Increase inotify watches
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 8. Tool Comparison Matrix

| Feature | FSEvents | inotify | Chokidar | Watchman | fswatch |
|---------|----------|---------|----------|----------|---------|
| **Platform** | macOS | Linux | Cross | Cross | Cross |
| **Recursive** | Native | Manual | Auto | Auto | Native |
| **File limit** | Unlimited | 8K default | Depends | High | Backend-dependent |
| **CPU idle** | Near-zero | Near-zero | Near-zero | Near-zero | Backend-dependent |
| **Debouncing** | Latency param | Manual | awaitWriteFinish | settle config | Manual |
| **Git-aware** | No | No | No | Yes | No |
| **Watch sharing** | No | No | No | Yes | No |
| **Ease of use** | Low (C API) | Low | High | Medium | Medium |

---

## 9. Sources

### Official Documentation
- [Apple FSEvents API](https://developer.apple.com/documentation/coreservices/file_system_events)
- [Using the File System Events API](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/FSEvents_ProgGuide/UsingtheFSEventsFramework/UsingtheFSEventsFramework.html)
- [Linux inotify(7) Manual](https://man7.org/linux/man-pages/man7/inotify.7.html)
- [Watchman Documentation](https://facebook.github.io/watchman/)

### Libraries and Tools
- [Chokidar on npm](https://www.npmjs.com/package/chokidar)
- [Chokidar GitHub](https://github.com/paulmillr/chokidar)
- [fswatch GitHub](https://github.com/emcrisostomo/fswatch)
- [Watchman GitHub](https://github.com/facebook/watchman)

### Comparisons and Guides
- [npm-compare: Chokidar vs alternatives](https://npm-compare.com/chokidar,fsevents,gaze,node-watch,watch)
- [npm trends: File watchers](https://npmtrends.com/chokidar-vs-node-watch-vs-nodemon-vs-watch-vs-watchpack)
- [Linux inotify limits](https://watchexec.github.io/docs/inotify-limits.html)
- [Baeldung: inotify upper limit](https://www.baeldung.com/linux/inotify-upper-limit-reached)

### LLM Integration
- [Repomix - AI-friendly repo packing](https://github.com/yamadashy/repomix)
- [RepoAgent - LLM-powered repo agent](https://github.com/OpenBMB/RepoAgent)
- [GitIngest](https://gitingest.com/)

### Debouncing Strategies
- [WriteAsync: Directory watching debouncing](http://writeasync.net/?p=5744)
- [@bscotch/debounce-watch](https://www.npmjs.com/package/@bscotch/debounce-watch)

---

## 10. Git Hooks for Repository-Level Event Notification

Git hooks provide a complementary mechanism to file watching, triggering on Git operations rather than raw file changes. This is valuable for consciousness systems because Git events represent intentional, semantically meaningful changes.

### 10.1 Available Hook Types

| Hook | Trigger | Use Case |
|------|---------|----------|
| `pre-commit` | Before commit is created | Validate changes, run pre-checks |
| `post-commit` | After commit is created | Notify consciousness of committed changes |
| `post-merge` | After git merge | Detect merged changes from other branches |
| `post-checkout` | After branch switch | Awareness of context switch |
| `post-rewrite` | After rebase/amend | Track history modifications |
| `pre-push` | Before pushing to remote | Validate outgoing changes |
| `post-receive` | On server after push | Trigger CI/consciousness updates |

### 10.2 Consciousness Notification Hooks

**post-commit hook for consciousness notification:**

```bash
#!/bin/bash
# .git/hooks/post-commit
# Notify consciousness system of new commits

REPO_ROOT=$(git rev-parse --show-toplevel)
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)
STATS=$(git diff --shortstat HEAD~1 HEAD 2>/dev/null || echo "initial commit")

# Create JSON notification
NOTIFICATION=$(cat <<EOF
{
  "event": "commit",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "commit": {
    "hash": "$COMMIT_HASH",
    "message": $(echo "$COMMIT_MSG" | jq -Rs .),
    "stats": "$STATS"
  },
  "files": $(echo "$CHANGED_FILES" | jq -R . | jq -s .)
}
EOF
)

# Write to consciousness notification queue
NOTIFY_DIR="$REPO_ROOT/.consciousness/notifications"
mkdir -p "$NOTIFY_DIR"
echo "$NOTIFICATION" > "$NOTIFY_DIR/$(date +%s)-commit.json"

# Optional: Send to local HTTP endpoint
# curl -X POST -H "Content-Type: application/json" \
#   -d "$NOTIFICATION" http://localhost:3001/consciousness/git-event 2>/dev/null || true

echo "Consciousness notified of commit: ${COMMIT_HASH:0:8}"
```

**post-checkout hook for branch awareness:**

```bash
#!/bin/bash
# .git/hooks/post-checkout
# Notify consciousness of branch/context switches

PREV_HEAD=$1
NEW_HEAD=$2
IS_BRANCH_CHECKOUT=$3  # 1 if branch, 0 if file checkout

if [ "$IS_BRANCH_CHECKOUT" = "1" ]; then
  REPO_ROOT=$(git rev-parse --show-toplevel)
  BRANCH=$(git rev-parse --abbrev-ref HEAD)

  NOTIFICATION=$(cat <<EOF
{
  "event": "branch_switch",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "branch": "$BRANCH",
  "previous_head": "$PREV_HEAD",
  "new_head": "$NEW_HEAD"
}
EOF
)

  NOTIFY_DIR="$REPO_ROOT/.consciousness/notifications"
  mkdir -p "$NOTIFY_DIR"
  echo "$NOTIFICATION" > "$NOTIFY_DIR/$(date +%s)-checkout.json"
fi
```

### 10.3 Node.js Hook Processing

```javascript
import chokidar from 'chokidar';
import { readFile, unlink } from 'fs/promises';
import { join } from 'path';

class GitHookProcessor {
  constructor(repoPath, onEvent) {
    this.repoPath = repoPath;
    this.notifyDir = join(repoPath, '.consciousness', 'notifications');
    this.onEvent = onEvent;
  }

  async start() {
    // Watch for git hook notifications
    this.watcher = chokidar.watch(this.notifyDir, {
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: { stabilityThreshold: 50 }
    });

    this.watcher.on('add', async (path) => {
      try {
        const content = await readFile(path, 'utf8');
        const event = JSON.parse(content);

        // Process the git event
        await this.onEvent(event);

        // Clean up processed notification
        await unlink(path);
      } catch (error) {
        console.error('Failed to process git hook notification:', error);
      }
    });
  }

  async stop() {
    await this.watcher?.close();
  }
}

// Usage with consciousness system
const processor = new GitHookProcessor('/Users/chris/Developer/stoffy', async (event) => {
  console.log(`Git event: ${event.event}`);

  if (event.event === 'commit') {
    console.log(`Commit: ${event.commit.hash}`);
    console.log(`Files changed: ${event.files.join(', ')}`);
    // Trigger consciousness processing for the committed files
  }
});

await processor.start();
```

### 10.4 Combining File Watching with Git Hooks

The ideal consciousness system uses both mechanisms:

| Mechanism | Strengths | Use For |
|-----------|-----------|---------|
| File watcher (Chokidar) | Real-time, granular | Live editing awareness |
| Git hooks | Semantic, intentional | Committed changes, context switches |

```javascript
class HybridRepositoryMonitor {
  constructor(repoPath) {
    this.repoPath = repoPath;
    this.pendingChanges = new Map();
    this.committedRecently = new Set();
  }

  handleFileChange(path, event) {
    // Skip if this file was just committed (avoid duplicate processing)
    if (this.committedRecently.has(path)) {
      this.committedRecently.delete(path);
      return;
    }

    this.pendingChanges.set(path, {
      event,
      timestamp: Date.now(),
      source: 'filesystem'
    });
  }

  handleGitEvent(event) {
    if (event.event === 'commit') {
      // Mark committed files to avoid duplicate processing
      event.files.forEach(file => {
        this.committedRecently.add(file);
        this.pendingChanges.delete(file);

        // Clear after short delay
        setTimeout(() => this.committedRecently.delete(file), 5000);
      });

      // Process committed changes with higher priority
      return {
        type: 'committed_changes',
        files: event.files,
        commit: event.commit,
        priority: 'high'
      };
    }

    if (event.event === 'branch_switch') {
      // Clear pending changes on branch switch
      this.pendingChanges.clear();

      return {
        type: 'context_switch',
        branch: event.branch,
        priority: 'high'
      };
    }
  }
}
```

---

## 11. Parsing Different File Types

For a consciousness system, different file types carry different semantic weight and require different parsing strategies.

### 11.1 File Type Priority Matrix

```javascript
const FILE_TYPE_CONFIG = {
  // High priority: Core knowledge and configuration
  high: {
    patterns: ['**/*.md', '**/CLAUDE.md', '**/profile.md', '**/thought.md'],
    extensions: ['.md', '.yaml', '.yml'],
    directories: ['knowledge/', 'indices/', '.claude/'],
    debounceMs: 100
  },

  // Medium priority: Code and configuration
  medium: {
    patterns: ['**/*.ts', '**/*.js', '**/*.py', '**/*.json'],
    extensions: ['.ts', '.js', '.py', '.json', '.tsx', '.jsx'],
    directories: ['src/', 'scripts/', 'config/'],
    debounceMs: 300
  },

  // Low priority: Documentation and assets
  low: {
    patterns: ['**/README.md', '**/docs/**'],
    extensions: ['.txt', '.css', '.html'],
    directories: ['docs/', 'assets/'],
    debounceMs: 1000
  },

  // Ignore: Build artifacts and dependencies
  ignore: {
    patterns: ['**/node_modules/**', '**/dist/**', '**/.git/**'],
    extensions: ['.log', '.lock', '.map'],
    directories: ['node_modules/', '.git/', 'dist/', 'build/']
  }
};

function getFilePriority(filePath) {
  const ext = path.extname(filePath);
  const relativePath = filePath.replace(repoPath, '').slice(1);

  // Check ignore first
  for (const dir of FILE_TYPE_CONFIG.ignore.directories) {
    if (relativePath.startsWith(dir)) return 'ignore';
  }
  if (FILE_TYPE_CONFIG.ignore.extensions.includes(ext)) return 'ignore';

  // Check high priority
  for (const dir of FILE_TYPE_CONFIG.high.directories) {
    if (relativePath.startsWith(dir)) return 'high';
  }
  if (FILE_TYPE_CONFIG.high.extensions.includes(ext)) return 'high';

  // Check medium priority
  for (const dir of FILE_TYPE_CONFIG.medium.directories) {
    if (relativePath.startsWith(dir)) return 'medium';
  }
  if (FILE_TYPE_CONFIG.medium.extensions.includes(ext)) return 'medium';

  return 'low';
}
```

### 11.2 Markdown File Parsing

```javascript
import { readFile } from 'fs/promises';

class MarkdownParser {
  static FRONTMATTER_REGEX = /^---\n([\s\S]*?)\n---/;
  static HEADER_REGEX = /^(#{1,6})\s+(.+)$/gm;
  static LINK_REGEX = /\[([^\]]+)\]\(([^)]+)\)/g;
  static CODE_BLOCK_REGEX = /```(\w+)?\n([\s\S]*?)```/g;

  async parse(filePath) {
    const content = await readFile(filePath, 'utf8');

    return {
      path: filePath,
      frontmatter: this.extractFrontmatter(content),
      headers: this.extractHeaders(content),
      links: this.extractLinks(content),
      codeBlocks: this.extractCodeBlocks(content),
      wordCount: this.countWords(content),
      summary: this.generateSummary(content)
    };
  }

  extractFrontmatter(content) {
    const match = content.match(MarkdownParser.FRONTMATTER_REGEX);
    if (!match) return null;

    try {
      // Simple YAML parsing for common frontmatter
      const lines = match[1].split('\n');
      const result = {};

      for (const line of lines) {
        const colonIndex = line.indexOf(':');
        if (colonIndex > 0) {
          const key = line.slice(0, colonIndex).trim();
          const value = line.slice(colonIndex + 1).trim();
          result[key] = value.replace(/^["']|["']$/g, '');
        }
      }

      return result;
    } catch {
      return null;
    }
  }

  extractHeaders(content) {
    const headers = [];
    let match;

    while ((match = MarkdownParser.HEADER_REGEX.exec(content)) !== null) {
      headers.push({
        level: match[1].length,
        text: match[2],
        position: match.index
      });
    }

    return headers;
  }

  extractLinks(content) {
    const links = [];
    let match;

    while ((match = MarkdownParser.LINK_REGEX.exec(content)) !== null) {
      links.push({
        text: match[1],
        href: match[2],
        isInternal: !match[2].startsWith('http')
      });
    }

    return links;
  }

  extractCodeBlocks(content) {
    const blocks = [];
    let match;

    while ((match = MarkdownParser.CODE_BLOCK_REGEX.exec(content)) !== null) {
      blocks.push({
        language: match[1] || 'text',
        code: match[2].trim(),
        lineCount: match[2].split('\n').length
      });
    }

    return blocks;
  }

  countWords(content) {
    // Remove code blocks and frontmatter for accurate count
    const cleanContent = content
      .replace(MarkdownParser.FRONTMATTER_REGEX, '')
      .replace(MarkdownParser.CODE_BLOCK_REGEX, '');

    return cleanContent.split(/\s+/).filter(w => w.length > 0).length;
  }

  generateSummary(content) {
    // Extract first paragraph after frontmatter and headers
    const cleanContent = content
      .replace(MarkdownParser.FRONTMATTER_REGEX, '')
      .replace(/^#.+$/gm, '')
      .trim();

    const firstParagraph = cleanContent.split(/\n\n/)[0];
    return firstParagraph?.slice(0, 200) + (firstParagraph?.length > 200 ? '...' : '');
  }
}
```

### 11.3 YAML File Parsing

```javascript
import { readFile } from 'fs/promises';
import { parse as parseYaml } from 'yaml';

class YamlParser {
  async parse(filePath) {
    const content = await readFile(filePath, 'utf8');

    try {
      const data = parseYaml(content);

      return {
        path: filePath,
        valid: true,
        data,
        keys: this.extractKeys(data),
        references: this.extractReferences(data),
        structure: this.analyzeStructure(data)
      };
    } catch (error) {
      return {
        path: filePath,
        valid: false,
        error: error.message
      };
    }
  }

  extractKeys(obj, prefix = '') {
    const keys = [];

    if (typeof obj !== 'object' || obj === null) {
      return keys;
    }

    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      keys.push(fullKey);

      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        keys.push(...this.extractKeys(value, fullKey));
      }
    }

    return keys;
  }

  extractReferences(obj, refs = []) {
    if (typeof obj === 'string') {
      // Look for file path references
      if (obj.endsWith('.md') || obj.endsWith('.yaml') || obj.startsWith('./')) {
        refs.push(obj);
      }
    } else if (Array.isArray(obj)) {
      obj.forEach(item => this.extractReferences(item, refs));
    } else if (typeof obj === 'object' && obj !== null) {
      Object.values(obj).forEach(value => this.extractReferences(value, refs));
    }

    return refs;
  }

  analyzeStructure(obj) {
    if (typeof obj !== 'object' || obj === null) {
      return { type: typeof obj };
    }

    if (Array.isArray(obj)) {
      return {
        type: 'array',
        length: obj.length,
        itemTypes: [...new Set(obj.map(item => typeof item))]
      };
    }

    return {
      type: 'object',
      keyCount: Object.keys(obj).length,
      keys: Object.keys(obj).slice(0, 10)
    };
  }
}
```

### 11.4 Code File Parsing (TypeScript/JavaScript)

```javascript
import { readFile } from 'fs/promises';

class CodeParser {
  static IMPORT_REGEX = /^import\s+(?:{[^}]+}|\*\s+as\s+\w+|\w+)\s+from\s+['"]([^'"]+)['"]/gm;
  static EXPORT_REGEX = /^export\s+(default\s+)?(class|function|const|let|var|interface|type)\s+(\w+)/gm;
  static CLASS_REGEX = /^(export\s+)?(abstract\s+)?class\s+(\w+)(\s+extends\s+(\w+))?(\s+implements\s+([^{]+))?/gm;
  static FUNCTION_REGEX = /^(export\s+)?(async\s+)?function\s+(\w+)/gm;

  async parse(filePath) {
    const content = await readFile(filePath, 'utf8');
    const lines = content.split('\n');

    return {
      path: filePath,
      lineCount: lines.length,
      imports: this.extractImports(content),
      exports: this.extractExports(content),
      classes: this.extractClasses(content),
      functions: this.extractFunctions(content),
      complexity: this.estimateComplexity(content)
    };
  }

  extractImports(content) {
    const imports = [];
    let match;

    while ((match = CodeParser.IMPORT_REGEX.exec(content)) !== null) {
      const source = match[1];
      imports.push({
        source,
        isRelative: source.startsWith('.'),
        isExternal: !source.startsWith('.') && !source.startsWith('@/')
      });
    }

    return imports;
  }

  extractExports(content) {
    const exports = [];
    let match;

    while ((match = CodeParser.EXPORT_REGEX.exec(content)) !== null) {
      exports.push({
        name: match[3],
        type: match[2],
        isDefault: !!match[1]
      });
    }

    return exports;
  }

  extractClasses(content) {
    const classes = [];
    let match;

    while ((match = CodeParser.CLASS_REGEX.exec(content)) !== null) {
      classes.push({
        name: match[3],
        isExported: !!match[1],
        isAbstract: !!match[2],
        extends: match[5] || null,
        implements: match[7]?.split(',').map(s => s.trim()) || []
      });
    }

    return classes;
  }

  extractFunctions(content) {
    const functions = [];
    let match;

    while ((match = CodeParser.FUNCTION_REGEX.exec(content)) !== null) {
      functions.push({
        name: match[3],
        isExported: !!match[1],
        isAsync: !!match[2]
      });
    }

    return functions;
  }

  estimateComplexity(content) {
    // Simple complexity estimation based on control flow
    const controlFlowKeywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'catch', 'try'];
    let complexity = 1;

    for (const keyword of controlFlowKeywords) {
      const regex = new RegExp(`\\b${keyword}\\b`, 'g');
      complexity += (content.match(regex) || []).length;
    }

    return complexity;
  }
}
```

### 11.5 Unified File Parser

```javascript
import { extname } from 'path';

class UnifiedFileParser {
  constructor() {
    this.markdownParser = new MarkdownParser();
    this.yamlParser = new YamlParser();
    this.codeParser = new CodeParser();
  }

  async parse(filePath) {
    const ext = extname(filePath).toLowerCase();

    const baseInfo = {
      path: filePath,
      extension: ext,
      parsedAt: new Date().toISOString()
    };

    try {
      switch (ext) {
        case '.md':
          return { ...baseInfo, type: 'markdown', ...(await this.markdownParser.parse(filePath)) };

        case '.yaml':
        case '.yml':
          return { ...baseInfo, type: 'yaml', ...(await this.yamlParser.parse(filePath)) };

        case '.ts':
        case '.tsx':
        case '.js':
        case '.jsx':
          return { ...baseInfo, type: 'code', ...(await this.codeParser.parse(filePath)) };

        case '.json':
          const content = await readFile(filePath, 'utf8');
          const data = JSON.parse(content);
          return { ...baseInfo, type: 'json', valid: true, keyCount: Object.keys(data).length };

        default:
          return { ...baseInfo, type: 'unknown', parsed: false };
      }
    } catch (error) {
      return { ...baseInfo, type: 'error', error: error.message };
    }
  }

  // Generate consciousness-friendly summary
  async summarizeForLLM(filePath) {
    const parsed = await this.parse(filePath);

    switch (parsed.type) {
      case 'markdown':
        return `Markdown file: ${parsed.headers?.[0]?.text || 'Untitled'}. ` +
               `${parsed.wordCount} words, ${parsed.headers?.length || 0} sections.`;

      case 'yaml':
        return `YAML config: ${parsed.keys?.length || 0} keys. ` +
               `Top-level: ${parsed.structure?.keys?.join(', ') || 'empty'}`;

      case 'code':
        return `${parsed.extension.slice(1).toUpperCase()} file: ${parsed.lineCount} lines. ` +
               `Exports: ${parsed.exports?.map(e => e.name).join(', ') || 'none'}. ` +
               `Complexity: ${parsed.complexity}`;

      case 'json':
        return `JSON file: ${parsed.keyCount} top-level keys`;

      default:
        return `File: ${parsed.path} (${parsed.type})`;
    }
  }
}
```

---

## 12. Detecting Meaningful Changes vs Noise

A critical capability for consciousness systems is distinguishing between meaningful changes that warrant processing and noise that should be filtered.

### 12.1 Change Significance Scoring

```javascript
class ChangeSignificanceAnalyzer {
  constructor(repoPath) {
    this.repoPath = repoPath;
    this.recentChanges = new Map();
    this.significanceThreshold = 0.3;
  }

  // Calculate significance score (0-1)
  async scoreChange(change) {
    const scores = await Promise.all([
      this.scoreByFileType(change.path),
      this.scoreByContentDelta(change),
      this.scoreByFrequency(change.path),
      this.scoreByLocation(change.path),
      this.scoreByTimeOfDay()
    ]);

    // Weighted average
    const weights = [0.25, 0.30, 0.15, 0.20, 0.10];
    const totalScore = scores.reduce((sum, score, i) => sum + score * weights[i], 0);

    return {
      score: totalScore,
      isSignificant: totalScore >= this.significanceThreshold,
      breakdown: {
        fileType: scores[0],
        contentDelta: scores[1],
        frequency: scores[2],
        location: scores[3],
        timing: scores[4]
      }
    };
  }

  // Score based on file type importance
  scoreByFileType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const relativePath = filePath.replace(this.repoPath, '');

    // Critical files get highest score
    const criticalPatterns = [
      /CLAUDE\.md$/,
      /\/profile\.md$/,
      /\/thought\.md$/,
      /\/indices\/.*\.yaml$/
    ];

    if (criticalPatterns.some(p => p.test(relativePath))) {
      return 1.0;
    }

    // Knowledge files
    if (relativePath.includes('/knowledge/')) return 0.8;

    // Configuration
    if (ext === '.yaml' || ext === '.yml') return 0.7;
    if (ext === '.json' && !relativePath.includes('package-lock')) return 0.6;

    // Code files
    if (['.ts', '.js', '.py'].includes(ext)) return 0.5;

    // Documentation
    if (ext === '.md') return 0.4;

    // Low priority
    if (['.css', '.html', '.txt'].includes(ext)) return 0.2;

    // Noise
    if (['.log', '.lock', '.map'].includes(ext)) return 0;

    return 0.3;
  }

  // Score based on actual content change magnitude
  async scoreByContentDelta(change) {
    if (change.event === 'deleted') return 0.5;
    if (change.event === 'added') return 0.8;

    if (!change.diff) return 0.3;

    // Parse diff to count actual changes
    const lines = change.diff.split('\n');
    let additions = 0;
    let deletions = 0;

    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) additions++;
      if (line.startsWith('-') && !line.startsWith('---')) deletions++;
    }

    const totalChanges = additions + deletions;

    // Significant changes
    if (totalChanges > 50) return 1.0;
    if (totalChanges > 20) return 0.8;
    if (totalChanges > 5) return 0.5;

    // Minor changes (whitespace, typos)
    return 0.2;
  }

  // Score inversely to frequency (frequent saves = less significant each time)
  scoreByFrequency(filePath) {
    const now = Date.now();
    const recentTimes = this.recentChanges.get(filePath) || [];

    // Filter to last 5 minutes
    const fiveMinAgo = now - 5 * 60 * 1000;
    const recentCount = recentTimes.filter(t => t > fiveMinAgo).length;

    // Update tracking
    this.recentChanges.set(filePath, [...recentTimes.filter(t => t > fiveMinAgo), now]);

    if (recentCount === 0) return 1.0;  // First change in 5 min
    if (recentCount < 3) return 0.7;
    if (recentCount < 10) return 0.3;

    return 0.1;  // Very frequent saves = low significance per save
  }

  // Score by location in repository
  scoreByLocation(filePath) {
    const relativePath = filePath.replace(this.repoPath, '');

    // Root level files often important
    if (!relativePath.includes('/', 1)) return 0.7;

    // Ignore directories
    if (relativePath.includes('/node_modules/')) return 0;
    if (relativePath.includes('/.git/')) return 0;
    if (relativePath.includes('/dist/')) return 0;
    if (relativePath.includes('/build/')) return 0;

    // Priority directories
    if (relativePath.includes('/knowledge/')) return 0.9;
    if (relativePath.includes('/indices/')) return 0.8;
    if (relativePath.includes('/.claude/')) return 0.8;
    if (relativePath.includes('/src/')) return 0.6;

    return 0.4;
  }

  // Score by time of day (active hours = more significant)
  scoreByTimeOfDay() {
    const hour = new Date().getHours();

    // Active work hours (9am-6pm)
    if (hour >= 9 && hour <= 18) return 0.8;

    // Evening work (6pm-11pm)
    if (hour >= 18 && hour <= 23) return 0.6;

    // Late night/early morning (likely automated)
    return 0.3;
  }
}
```

### 12.2 Noise Filters

```javascript
class ChangeNoiseFilter {
  constructor() {
    this.filters = [
      this.filterByPath,
      this.filterByExtension,
      this.filterByContent,
      this.filterByPattern
    ];
  }

  // Chain of filters, returns true if change should be ignored
  shouldIgnore(change) {
    return this.filters.some(filter => filter.call(this, change));
  }

  filterByPath(change) {
    const ignorePaths = [
      /node_modules/,
      /\.git\//,
      /dist\//,
      /build\//,
      /\.next\//,
      /coverage\//,
      /__pycache__/,
      /\.pytest_cache/,
      /\.DS_Store$/,
      /\.swarm\//,
      /\.hive-mind\//,
      /\.claude-flow\//,
      /memory\/claude-flow/
    ];

    return ignorePaths.some(pattern => pattern.test(change.path));
  }

  filterByExtension(change) {
    const ignoreExtensions = [
      '.log', '.lock', '.map', '.pyc', '.pyo',
      '.swp', '.swo', '.tmp', '.bak',
      '.db', '.db-journal', '.db-wal',
      '.sqlite', '.sqlite-journal'
    ];

    const ext = path.extname(change.path).toLowerCase();
    return ignoreExtensions.includes(ext);
  }

  filterByContent(change) {
    if (!change.diff) return false;

    // Ignore whitespace-only changes
    const significantLines = change.diff
      .split('\n')
      .filter(line => {
        if (!line.startsWith('+') && !line.startsWith('-')) return false;
        if (line.startsWith('+++') || line.startsWith('---')) return false;

        // Check if line has non-whitespace content
        return line.slice(1).trim().length > 0;
      });

    return significantLines.length === 0;
  }

  filterByPattern(change) {
    // Ignore auto-generated files
    const autoGenPatterns = [
      /package-lock\.json$/,
      /yarn\.lock$/,
      /pnpm-lock\.yaml$/,
      /\.min\.(js|css)$/,
      /\.generated\./,
      /\/\.consciousness\/notifications\//  // Our own notification files
    ];

    return autoGenPatterns.some(pattern => pattern.test(change.path));
  }
}
```

### 12.3 Integrated Meaningful Change Detector

```javascript
class MeaningfulChangeDetector {
  constructor(repoPath) {
    this.repoPath = repoPath;
    this.noiseFilter = new ChangeNoiseFilter();
    this.significanceAnalyzer = new ChangeSignificanceAnalyzer(repoPath);
    this.parser = new UnifiedFileParser();
  }

  async processChange(change) {
    // Step 1: Quick noise filter
    if (this.noiseFilter.shouldIgnore(change)) {
      return { processed: false, reason: 'noise_filtered' };
    }

    // Step 2: Calculate significance
    const significance = await this.significanceAnalyzer.scoreChange(change);

    if (!significance.isSignificant) {
      return {
        processed: false,
        reason: 'low_significance',
        score: significance.score
      };
    }

    // Step 3: Parse file for context
    let parsed = null;
    if (change.event !== 'deleted') {
      try {
        parsed = await this.parser.parse(change.path);
      } catch (error) {
        // Continue without parsed content
      }
    }

    // Step 4: Generate consciousness context
    const context = this.generateContext(change, significance, parsed);

    return {
      processed: true,
      significance,
      parsed,
      context,
      priority: this.calculatePriority(significance.score)
    };
  }

  generateContext(change, significance, parsed) {
    const relativePath = change.path.replace(this.repoPath + '/', '');

    let summary = `${change.event.toUpperCase()}: ${relativePath}`;

    if (parsed) {
      summary += `\n${this.parser.summarizeForLLM(change.path)}`;
    }

    if (change.diff && significance.breakdown.contentDelta > 0.5) {
      const diffLines = change.diff.split('\n').slice(0, 20);
      summary += `\n\nKey changes:\n${diffLines.join('\n')}`;
    }

    return summary;
  }

  calculatePriority(score) {
    if (score >= 0.8) return 'critical';
    if (score >= 0.6) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  }
}
```

---

## 13. Stoffy-Specific Implementation

Complete implementation for watching the `/Users/chris/Developer/stoffy` repository:

```javascript
import chokidar from 'chokidar';
import { readFile } from 'fs/promises';
import { execSync } from 'child_process';
import { join, relative, extname } from 'path';
import { createHash } from 'crypto';

const STOFFY_PATH = '/Users/chris/Developer/stoffy';

// Stoffy-specific file type weights
const STOFFY_FILE_PRIORITIES = {
  // Critical: Core knowledge and consciousness
  critical: {
    patterns: [
      /CLAUDE\.md$/,
      /\/thinkers\/[^/]+\/profile\.md$/,
      /\/thoughts\/[^/]+\/thought\.md$/,
      /\/sources\/[^/]+\.md$/,
      /\/indices\/[^/]+\.yaml$/
    ],
    weight: 1.0
  },

  // High: Philosophy content and skills
  high: {
    patterns: [
      /\/knowledge\/philosophy\//,
      /\/\.claude\/skills\//,
      /\/\.claude\/agents\//,
      /\/\.claude\/commands\//
    ],
    weight: 0.8
  },

  // Medium: Documentation and configuration
  medium: {
    patterns: [
      /\/docs\//,
      /\/templates\//,
      /\.yaml$/,
      /\.md$/
    ],
    weight: 0.5
  },

  // Low: General files
  low: {
    patterns: [
      /\.json$/,
      /\.txt$/
    ],
    weight: 0.3
  },

  // Ignore: Build artifacts, dependencies, generated
  ignore: {
    patterns: [
      /node_modules/,
      /\.git\//,
      /\.DS_Store/,
      /\.swarm\//,
      /\.hive-mind\//,
      /\.claude-flow\//,
      /memory\/claude-flow/,
      /coordination\//,
      /archive\/legacy/,
      /\.db$/,
      /\.log$/,
      /\.lock$/
    ]
  }
};

class StoffyConsciousnessWatcher {
  constructor(options = {}) {
    this.repoPath = STOFFY_PATH;
    this.debounceMs = options.debounceMs || 500;
    this.maxBatchSize = options.maxBatchSize || 15;

    this.changeBuffer = new Map();
    this.contentCache = new Map();
    this.flushTimeout = null;
    this.onProcess = options.onProcess || this.defaultProcessor;
  }

  getFilePriority(filePath) {
    const relativePath = relative(this.repoPath, filePath);

    // Check ignore first
    if (STOFFY_FILE_PRIORITIES.ignore.patterns.some(p => p.test(relativePath))) {
      return { priority: 'ignore', weight: 0 };
    }

    // Check in order of priority
    for (const [priority, config] of Object.entries(STOFFY_FILE_PRIORITIES)) {
      if (priority === 'ignore') continue;
      if (config.patterns.some(p => p.test(relativePath))) {
        return { priority, weight: config.weight };
      }
    }

    return { priority: 'low', weight: 0.2 };
  }

  async start() {
    console.log(`Consciousness watcher starting for: ${this.repoPath}`);

    this.watcher = chokidar.watch(this.repoPath, {
      ignored: (path) => {
        const { priority } = this.getFilePriority(path);
        return priority === 'ignore';
      },
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 100,
        pollInterval: 50
      },
      depth: 10  // Limit depth for performance
    });

    this.watcher
      .on('add', (path) => this.handleChange(path, 'added'))
      .on('change', (path) => this.handleChange(path, 'modified'))
      .on('unlink', (path) => this.handleChange(path, 'deleted'))
      .on('ready', () => {
        console.log('Consciousness watcher ready');
        console.log(`Watching ${this.repoPath}`);
      })
      .on('error', (err) => console.error('Watch error:', err));

    return this;
  }

  handleChange(filePath, event) {
    const { priority, weight } = this.getFilePriority(filePath);

    if (priority === 'ignore') return;

    this.changeBuffer.set(filePath, {
      path: filePath,
      relativePath: relative(this.repoPath, filePath),
      event,
      priority,
      weight,
      timestamp: Date.now()
    });

    this.scheduleFlush();
  }

  scheduleFlush() {
    clearTimeout(this.flushTimeout);
    this.flushTimeout = setTimeout(() => this.flush(), this.debounceMs);
  }

  async flush() {
    if (this.changeBuffer.size === 0) return;

    // Sort by priority and take top N
    const changes = Array.from(this.changeBuffer.values())
      .sort((a, b) => b.weight - a.weight)
      .slice(0, this.maxBatchSize);

    this.changeBuffer.clear();

    // Enrich changes with content and diffs
    const enrichedChanges = await Promise.all(
      changes.map(change => this.enrichChange(change))
    );

    // Filter to only meaningful changes
    const meaningfulChanges = enrichedChanges.filter(c => c.isMeaningful);

    if (meaningfulChanges.length > 0) {
      await this.onProcess(meaningfulChanges);
    }
  }

  async enrichChange(change) {
    const enriched = { ...change };

    try {
      if (change.event !== 'deleted') {
        // Get content and check if actually changed
        const content = await readFile(change.path, 'utf8');
        const hash = createHash('md5').update(content).digest('hex');

        const cached = this.contentCache.get(change.path);
        enriched.contentChanged = !cached || cached.hash !== hash;

        this.contentCache.set(change.path, { hash, size: content.length });

        // Get git diff for modified files
        if (change.event === 'modified' && enriched.contentChanged) {
          enriched.diff = this.getGitDiff(change.relativePath);
        }

        // Parse file based on type
        enriched.parsed = await this.parseFile(change.path, content);
      }

      enriched.isMeaningful = this.assessMeaningfulness(enriched);

    } catch (error) {
      enriched.error = error.message;
      enriched.isMeaningful = false;
    }

    return enriched;
  }

  getGitDiff(relativePath) {
    try {
      return execSync(`git diff -- "${relativePath}"`, {
        cwd: this.repoPath,
        encoding: 'utf8',
        maxBuffer: 1024 * 1024
      });
    } catch {
      return null;
    }
  }

  async parseFile(filePath, content) {
    const ext = extname(filePath).toLowerCase();

    switch (ext) {
      case '.md':
        return this.parseMarkdown(content);
      case '.yaml':
      case '.yml':
        return this.parseYaml(content);
      default:
        return { type: ext, lineCount: content.split('\n').length };
    }
  }

  parseMarkdown(content) {
    const headerMatch = content.match(/^#\s+(.+)$/m);
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);

    return {
      type: 'markdown',
      title: headerMatch?.[1],
      hasFrontmatter: !!frontmatterMatch,
      wordCount: content.split(/\s+/).length,
      headerCount: (content.match(/^#+\s/gm) || []).length
    };
  }

  parseYaml(content) {
    try {
      const lines = content.split('\n');
      const topLevelKeys = lines
        .filter(line => /^\w+:/.test(line))
        .map(line => line.split(':')[0]);

      return {
        type: 'yaml',
        lineCount: lines.length,
        topLevelKeys
      };
    } catch {
      return { type: 'yaml', error: 'parse failed' };
    }
  }

  assessMeaningfulness(change) {
    // New or deleted files are always meaningful
    if (change.event === 'added' || change.event === 'deleted') {
      return true;
    }

    // Modified files need content change
    if (!change.contentChanged) {
      return false;
    }

    // Critical priority is always meaningful
    if (change.priority === 'critical') {
      return true;
    }

    // Check if diff shows substantial changes
    if (change.diff) {
      const lines = change.diff.split('\n');
      const changedLines = lines.filter(l =>
        (l.startsWith('+') || l.startsWith('-')) &&
        !l.startsWith('+++') &&
        !l.startsWith('---') &&
        l.slice(1).trim().length > 0
      );

      // At least 3 meaningful lines changed
      return changedLines.length >= 3;
    }

    return true;
  }

  async defaultProcessor(changes) {
    console.log('\n=== Consciousness Event ===');
    console.log(`Detected ${changes.length} meaningful changes:`);

    for (const change of changes) {
      console.log(`  [${change.priority}] ${change.event}: ${change.relativePath}`);

      if (change.parsed?.title) {
        console.log(`    Title: ${change.parsed.title}`);
      }

      if (change.diff) {
        const stats = this.summarizeDiff(change.diff);
        console.log(`    Diff: +${stats.additions} -${stats.deletions} lines`);
      }
    }

    console.log('===========================\n');
  }

  summarizeDiff(diff) {
    const lines = diff.split('\n');
    let additions = 0;
    let deletions = 0;

    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) additions++;
      if (line.startsWith('-') && !line.startsWith('---')) deletions++;
    }

    return { additions, deletions };
  }

  async stop() {
    clearTimeout(this.flushTimeout);
    await this.watcher?.close();
    console.log('Consciousness watcher stopped');
  }
}

// Usage
async function main() {
  const watcher = new StoffyConsciousnessWatcher({
    debounceMs: 500,
    maxBatchSize: 10,
    onProcess: async (changes) => {
      // Custom processing - send to LLM, store in memory, etc.
      console.log(`Processing ${changes.length} changes...`);

      // Example: Generate context for LLM
      const context = changes.map(c => {
        let summary = `${c.event.toUpperCase()}: ${c.relativePath}`;
        if (c.parsed?.title) summary += ` (${c.parsed.title})`;
        if (c.diff) {
          const stats = watcher.summarizeDiff(c.diff);
          summary += ` [+${stats.additions}/-${stats.deletions}]`;
        }
        return summary;
      }).join('\n');

      console.log('LLM Context:\n' + context);
    }
  });

  await watcher.start();

  // Graceful shutdown
  process.on('SIGINT', async () => {
    await watcher.stop();
    process.exit(0);
  });
}

main().catch(console.error);
```

---

## 14. Next Steps

1. **Prototype Implementation**: Build a minimal watcher using Chokidar
2. **Benchmarking**: Test with repository of target size
3. **LLM Integration**: Connect to Claude API with rate limiting
4. **Context Management**: Implement sliding window for conversation history
5. **Action System**: Add capability for watcher to trigger automated responses
6. **Git Hook Installation**: Deploy post-commit and post-checkout hooks
7. **Priority Tuning**: Adjust file type weights based on actual usage patterns
8. **Memory Integration**: Connect with Claude-Flow memory system for persistence
