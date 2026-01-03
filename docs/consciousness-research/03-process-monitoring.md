# Process Monitoring for AI Consciousness Layer

## Overview

This document details system and process monitoring techniques on macOS that can feed contextual data into an AI consciousness layer. The goal is to provide rich environmental awareness to enhance LLM reasoning with real-time system state.

---

## 1. macOS-Specific Process Monitoring

### 1.1 The `ps` Command

The `ps` command provides process status information. macOS uses BSD-style options (not GNU).

**Basic Process Listing:**
```bash
# All processes with full details
ps aux

# Custom format with specific fields
ps -eo pid,ppid,user,%cpu,%mem,stat,start,time,command

# Hierarchical view (process tree)
ps -axjf

# Specific process by PID
ps -p 1234 -o pid,ppid,%cpu,%mem,rss,vsz,state,comm

# Processes for current user
ps -u $(whoami)

# Find processes by name
ps aux | grep -E "claude|ollama|node"

# Process ancestry (parent chain)
ps -o pid,ppid,comm -p $(ps -o ppid= -p 1234)
```

**Key Fields:**
- `pid` - Process ID
- `ppid` - Parent Process ID
- `pgid` - Process Group ID
- `sid` - Session ID
- `%cpu` - CPU usage percentage
- `%mem` - Memory usage percentage
- `rss` - Resident Set Size (actual memory in KB)
- `vsz` - Virtual Size (total virtual memory)
- `stat` - Process state (R=running, S=sleeping, Z=zombie, T=stopped)
- `start` - Start time
- `time` - Cumulative CPU time
- `command` - Full command line
- `nice` - Nice value (scheduling priority)
- `tty` - Controlling terminal

**Python Integration:**
```python
import subprocess
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessInfo:
    pid: int
    ppid: int
    user: str
    cpu: float
    mem: float
    rss_kb: int
    state: str
    command: str
    nice: int = 0
    pgid: int = 0

def get_process_info(pattern: str = None) -> list[ProcessInfo]:
    """Get process information, optionally filtered by pattern."""
    cmd = ["ps", "-eo", "pid,ppid,pgid,user,%cpu,%mem,rss,nice,state,command"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    processes = []
    for line in result.stdout.strip().split('\n')[1:]:  # Skip header
        parts = line.split(None, 9)  # Split into max 10 parts
        if len(parts) >= 10:
            proc = ProcessInfo(
                pid=int(parts[0]),
                ppid=int(parts[1]),
                pgid=int(parts[2]),
                user=parts[3],
                cpu=float(parts[4]),
                mem=float(parts[5]),
                rss_kb=int(parts[6]),
                nice=int(parts[7]),
                state=parts[8],
                command=parts[9]
            )
            if pattern is None or re.search(pattern, proc.command, re.I):
                processes.append(proc)

    return sorted(processes, key=lambda x: x.cpu, reverse=True)

def get_process_tree() -> dict[int, list[int]]:
    """Build a process tree mapping parent PIDs to child PIDs."""
    processes = get_process_info()
    tree = {}
    for proc in processes:
        if proc.ppid not in tree:
            tree[proc.ppid] = []
        tree[proc.ppid].append(proc.pid)
    return tree

def get_process_ancestry(pid: int) -> list[int]:
    """Get the ancestry chain of a process (up to init)."""
    ancestry = [pid]
    current = pid

    while current > 1:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(current)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            break
        ppid = int(result.stdout.strip())
        ancestry.append(ppid)
        current = ppid

    return ancestry

# Example: Get LLM-related processes
llm_procs = get_process_info(r'ollama|llama|mlx|lmstudio|claude')
```

### 1.2 The `top` Command

macOS `top` provides real-time process monitoring with different options than Linux.

**Non-Interactive Mode:**
```bash
# One snapshot, sorted by CPU, top 20 processes
top -l 1 -n 20 -o cpu

# Specific columns with stats
top -l 1 -stats pid,command,cpu,mem,pstate,time

# Continuous sampling (3 iterations, 2 second interval)
top -l 3 -s 2

# Sort by memory usage
top -l 1 -n 20 -o mem

# Include threads
top -l 1 -n 20 -stats pid,command,cpu,th
```

**Output Parsing:**
```python
import subprocess
import re
from dataclasses import dataclass

@dataclass
class SystemStats:
    load_1m: float
    load_5m: float
    load_15m: float
    cpu_user: float
    cpu_sys: float
    cpu_idle: float
    mem_used: str
    mem_unused: str
    processes_total: int
    processes_running: int
    processes_sleeping: int

def get_top_snapshot() -> SystemStats:
    """Get system stats from top command."""
    result = subprocess.run(
        ["top", "-l", "1", "-n", "10"],
        capture_output=True, text=True
    )

    lines = result.stdout.split('\n')
    stats = {
        'load_1m': 0.0, 'load_5m': 0.0, 'load_15m': 0.0,
        'cpu_user': 0.0, 'cpu_sys': 0.0, 'cpu_idle': 100.0,
        'mem_used': '0M', 'mem_unused': '0M',
        'processes_total': 0, 'processes_running': 0, 'processes_sleeping': 0
    }

    for line in lines[:15]:  # Header lines
        if 'Processes:' in line:
            match = re.search(r'(\d+) total, (\d+) running, (\d+) sleeping', line)
            if match:
                stats['processes_total'] = int(match.group(1))
                stats['processes_running'] = int(match.group(2))
                stats['processes_sleeping'] = int(match.group(3))

        elif 'Load Avg' in line:
            match = re.search(r'Load Avg: ([\d.]+), ([\d.]+), ([\d.]+)', line)
            if match:
                stats['load_1m'] = float(match.group(1))
                stats['load_5m'] = float(match.group(2))
                stats['load_15m'] = float(match.group(3))

        elif 'CPU usage' in line:
            match = re.search(r'([\d.]+)% user, ([\d.]+)% sys, ([\d.]+)% idle', line)
            if match:
                stats['cpu_user'] = float(match.group(1))
                stats['cpu_sys'] = float(match.group(2))
                stats['cpu_idle'] = float(match.group(3))

        elif 'PhysMem' in line:
            match = re.search(r'(\d+[GMK]?) used.*?(\d+[GMK]?) unused', line)
            if match:
                stats['mem_used'] = match.group(1)
                stats['mem_unused'] = match.group(2)

    return SystemStats(**stats)
```

### 1.3 LaunchD and launchctl

LaunchD is macOS's init and service manager (replaces init, cron, inetd).

**Service Listing:**
```bash
# List all services for current user
launchctl list

# List with PID and status
launchctl list | head -20

# Get specific service info
launchctl print gui/$(id -u)/com.apple.Finder

# System-wide services (requires sudo)
sudo launchctl list

# List all domains
launchctl print system
launchctl print gui/$(id -u)
launchctl print user/$(id -u)

# Check if a service is disabled
launchctl print-disabled gui/$(id -u)

# Detailed service information
launchctl print gui/$(id -u)/com.apple.Safari
```

**Key Service States:**
- `0` - Service ran successfully or is running
- Non-zero - Exit code or error state
- `-` - Service not currently running

**Service Domains:**
| Domain | Description |
|--------|-------------|
| `system/` | System-wide daemons |
| `gui/<uid>/` | Per-user GUI agents |
| `user/<uid>/` | Per-user agents (non-GUI) |
| `login/<asid>/` | Login session services |
| `pid/<pid>/` | Per-process services |

**Python Service Monitor:**
```python
import subprocess
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class LaunchDService:
    pid: Optional[int]
    status: Optional[int]
    label: str
    domain: str = "user"

def get_launchd_services(domain: str = "user") -> list[LaunchDService]:
    """Get launchd services and their status."""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True, text=True
    )

    services = []
    for line in result.stdout.strip().split('\n')[1:]:  # Skip header
        parts = line.split('\t')
        if len(parts) >= 3:
            services.append(LaunchDService(
                pid=int(parts[0]) if parts[0] != '-' else None,
                status=int(parts[1]) if parts[1] != '-' else None,
                label=parts[2],
                domain=domain
            ))

    return services

def is_service_running(label: str) -> bool:
    """Check if a specific launchd service is running."""
    result = subprocess.run(
        ["launchctl", "list", label],
        capture_output=True, text=True
    )
    return result.returncode == 0

def get_service_info(label: str) -> dict:
    """Get detailed information about a launchd service."""
    uid = os.getuid()
    result = subprocess.run(
        ["launchctl", "print", f"gui/{uid}/{label}"],
        capture_output=True, text=True
    )

    info = {'label': label, 'raw': result.stdout}

    # Parse key fields
    for line in result.stdout.split('\n'):
        if 'state =' in line.lower():
            info['state'] = line.split('=')[1].strip()
        elif 'pid =' in line.lower():
            try:
                info['pid'] = int(line.split('=')[1].strip())
            except ValueError:
                pass

    return info

def list_running_agents() -> list[str]:
    """Get list of currently running user agents."""
    services = get_launchd_services()
    return [s.label for s in services if s.pid is not None]
```

### 1.4 lsof - List Open Files

`lsof` is essential for understanding what files and network connections processes are using.

**File Descriptor Monitoring:**
```bash
# Open files for a process
lsof -p 1234

# Open files by command name
lsof -c node

# Network connections for a process
lsof -i -a -p 1234

# Specific file access
lsof /path/to/file

# All network connections
lsof -i

# TCP connections only
lsof -iTCP

# Listening ports
lsof -iTCP -sTCP:LISTEN

# Connections to specific port
lsof -i :8080

# Files in a directory
lsof +D /path/to/dir

# Open files by user
lsof -u $(whoami)

# Exclude kernel tasks (faster)
lsof -K
```

**Python Integration:**
```python
import subprocess
import re
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class OpenFile:
    command: str
    pid: int
    user: str
    fd: str
    type: str
    device: Optional[str]
    size: Optional[int]
    node: Optional[str]
    name: str

def get_open_files(pid: int) -> list[OpenFile]:
    """Get open files for a process."""
    result = subprocess.run(
        ["lsof", "-p", str(pid), "-F", "pcuftsn"],
        capture_output=True, text=True
    )

    files = []
    current = {}

    for line in result.stdout.split('\n'):
        if not line:
            continue
        field = line[0]
        value = line[1:]

        if field == 'p':
            current['pid'] = int(value)
        elif field == 'c':
            current['command'] = value
        elif field == 'u':
            current['user'] = value
        elif field == 'f':
            # New file descriptor starts
            if 'fd' in current and 'name' in current:
                files.append(OpenFile(**current))
            current['fd'] = value
        elif field == 't':
            current['type'] = value
        elif field == 's':
            current['size'] = int(value) if value.isdigit() else None
        elif field == 'n':
            current['name'] = value
            current.setdefault('device', None)
            current.setdefault('node', None)

    if 'fd' in current and 'name' in current:
        files.append(OpenFile(**current))

    return files

@dataclass
class NetworkConnection:
    command: str
    pid: int
    user: str
    fd: str
    type: str  # IPv4, IPv6
    protocol: str  # TCP, UDP
    local_addr: str
    remote_addr: Optional[str]
    state: str  # LISTEN, ESTABLISHED, etc.

def get_network_connections(pid: int = None) -> list[NetworkConnection]:
    """Get network connections, optionally for specific PID."""
    cmd = ["lsof", "-i", "-n", "-P"]
    if pid:
        cmd.extend(["-a", "-p", str(pid)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    connections = []
    for line in result.stdout.split('\n')[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 9:
            name = parts[8] if len(parts) > 8 else ""

            # Parse address:port format
            local_addr = ""
            remote_addr = None
            state = ""

            if "->" in name:
                local, remote = name.split("->")
                local_addr = local
                remote_addr = remote
            else:
                local_addr = name

            if len(parts) > 9:
                state = parts[9].strip("()")

            connections.append(NetworkConnection(
                command=parts[0],
                pid=int(parts[1]),
                user=parts[2],
                fd=parts[3],
                type=parts[4],
                protocol=parts[7] if len(parts) > 7 else "unknown",
                local_addr=local_addr,
                remote_addr=remote_addr,
                state=state
            ))

    return connections

def get_listening_ports() -> list[tuple[int, str, int]]:
    """Get all listening TCP ports with process info."""
    result = subprocess.run(
        ["lsof", "-iTCP", "-sTCP:LISTEN", "-n", "-P"],
        capture_output=True, text=True
    )

    ports = []
    for line in result.stdout.split('\n')[1:]:
        parts = line.split()
        if len(parts) >= 9:
            name = parts[8]
            # Extract port from address:port format
            match = re.search(r':(\d+)$', name)
            if match:
                port = int(match.group(1))
                ports.append((port, parts[0], int(parts[1])))

    return sorted(ports)
```

### 1.5 sysctl API for System Information

`sysctl` provides kernel state and hardware information.

**Hardware Information:**
```bash
# CPU cores
sysctl hw.ncpu hw.physicalcpu hw.logicalcpu

# Memory
sysctl hw.memsize  # Total memory in bytes

# OS version
sysctl kern.osversion kern.osrelease kern.version

# All hardware info
sysctl hw

# Process limits
sysctl kern.maxproc kern.maxprocperuid

# Hostname
sysctl kern.hostname

# Boot time
sysctl kern.boottime

# CPU type and features
sysctl machdep.cpu.brand_string
sysctl machdep.cpu.features
```

**Python Integration:**
```python
import subprocess
import struct
from datetime import datetime

def sysctl_get(key: str) -> str:
    """Get a sysctl value."""
    result = subprocess.run(
        ["sysctl", "-n", key],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def get_system_info() -> dict:
    """Get comprehensive system information via sysctl."""
    info = {
        'cpu_cores': int(sysctl_get('hw.ncpu')),
        'physical_cpus': int(sysctl_get('hw.physicalcpu')),
        'logical_cpus': int(sysctl_get('hw.logicalcpu')),
        'memory_bytes': int(sysctl_get('hw.memsize')),
        'memory_gb': int(sysctl_get('hw.memsize')) / (1024**3),
        'os_version': sysctl_get('kern.osversion'),
        'os_release': sysctl_get('kern.osrelease'),
        'hostname': sysctl_get('kern.hostname'),
        'max_processes': int(sysctl_get('kern.maxproc')),
    }

    # Parse boot time
    boottime = sysctl_get('kern.boottime')
    # Format: { sec = 1234567890, usec = 123456 } Thu Jan  1 00:00:00 2025
    match = re.search(r'sec = (\d+)', boottime)
    if match:
        info['boot_time'] = datetime.fromtimestamp(int(match.group(1)))
        info['uptime_seconds'] = (datetime.now() - info['boot_time']).total_seconds()

    # CPU brand if available
    try:
        info['cpu_brand'] = sysctl_get('machdep.cpu.brand_string')
    except:
        info['cpu_brand'] = 'Unknown'

    return info

def get_process_limits() -> dict:
    """Get system-wide process limits."""
    return {
        'max_processes': int(sysctl_get('kern.maxproc')),
        'max_proc_per_uid': int(sysctl_get('kern.maxprocperuid')),
        'max_files': int(sysctl_get('kern.maxfiles')),
        'max_files_per_proc': int(sysctl_get('kern.maxfilesperproc')),
    }
```

---

## 2. Node.js Process and child_process Modules

### 2.1 Process Module Basics

The Node.js `process` module provides information about the current Node.js process.

**Process Information:**
```javascript
// Basic process info
console.log({
    pid: process.pid,
    ppid: process.ppid,
    title: process.title,
    platform: process.platform,
    arch: process.arch,
    version: process.version,
    execPath: process.execPath,
    cwd: process.cwd(),
    uptime: process.uptime(),
});

// Resource usage
console.log({
    memoryUsage: process.memoryUsage(),
    // Returns: { rss, heapTotal, heapUsed, external, arrayBuffers }
    cpuUsage: process.cpuUsage(),
    // Returns: { user, system } in microseconds
});

// Environment
console.log(process.env);
console.log(process.argv);

// Exit handling
process.on('exit', (code) => {
    console.log(`Process exiting with code: ${code}`);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled rejection:', reason);
});

// Signals
process.on('SIGTERM', () => {
    console.log('Received SIGTERM');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('Received SIGINT');
    process.exit(0);
});
```

### 2.2 Child Process Spawning

**spawn() - Best for long-running processes with streaming I/O:**
```javascript
import { spawn } from 'child_process';

class ProcessMonitor {
    constructor() {
        this.processes = new Map();
    }

    spawn(command, args = [], options = {}) {
        const child = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe'],
            ...options
        });

        const processInfo = {
            pid: child.pid,
            command,
            args,
            startTime: Date.now(),
            stdout: [],
            stderr: [],
            exitCode: null,
            signal: null,
        };

        // Capture stdout
        child.stdout.on('data', (data) => {
            const text = data.toString();
            processInfo.stdout.push({
                timestamp: Date.now(),
                data: text
            });
            this.onOutput(processInfo.pid, 'stdout', text);
        });

        // Capture stderr
        child.stderr.on('data', (data) => {
            const text = data.toString();
            processInfo.stderr.push({
                timestamp: Date.now(),
                data: text
            });
            this.onOutput(processInfo.pid, 'stderr', text);
        });

        // Handle close
        child.on('close', (code, signal) => {
            processInfo.exitCode = code;
            processInfo.signal = signal;
            processInfo.endTime = Date.now();
            this.onExit(processInfo.pid, code, signal);
        });

        // Handle errors
        child.on('error', (err) => {
            this.onError(processInfo.pid, err);
        });

        this.processes.set(child.pid, {
            child,
            info: processInfo
        });

        return child;
    }

    // Override these methods for custom handling
    onOutput(pid, stream, data) {
        console.log(`[${pid}][${stream}] ${data.trim()}`);
    }

    onExit(pid, code, signal) {
        console.log(`[${pid}] Exited with code=${code}, signal=${signal}`);
    }

    onError(pid, error) {
        console.error(`[${pid}] Error:`, error);
    }

    // Write to stdin of a process
    write(pid, data) {
        const proc = this.processes.get(pid);
        if (proc?.child?.stdin) {
            proc.child.stdin.write(data);
        }
    }

    // Get process info
    getInfo(pid) {
        return this.processes.get(pid)?.info;
    }

    // Kill a process
    kill(pid, signal = 'SIGTERM') {
        const proc = this.processes.get(pid);
        if (proc?.child) {
            proc.child.kill(signal);
        }
    }
}

// Usage
const monitor = new ProcessMonitor();

// Spawn a long-running process
const child = monitor.spawn('node', ['server.js']);

// Write to its stdin
monitor.write(child.pid, 'some input\n');

// Later, check its output
const info = monitor.getInfo(child.pid);
console.log('Captured stdout:', info.stdout);
```

**exec() - For simple commands with buffered output:**
```javascript
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function runCommand(command) {
    try {
        const { stdout, stderr } = await execAsync(command, {
            maxBuffer: 10 * 1024 * 1024, // 10MB
            timeout: 30000, // 30 seconds
        });
        return { stdout, stderr, success: true };
    } catch (error) {
        return {
            stdout: error.stdout || '',
            stderr: error.stderr || error.message,
            success: false,
            code: error.code
        };
    }
}

// Usage
const result = await runCommand('ps aux | head -10');
console.log(result.stdout);
```

**execFile() - For running executables directly (safer):**
```javascript
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

async function getProcessList() {
    const { stdout } = await execFileAsync('ps', [
        '-eo', 'pid,ppid,user,%cpu,%mem,command'
    ]);

    return stdout.split('\n').slice(1).filter(Boolean).map(line => {
        const parts = line.trim().split(/\s+/);
        return {
            pid: parseInt(parts[0]),
            ppid: parseInt(parts[1]),
            user: parts[2],
            cpu: parseFloat(parts[3]),
            mem: parseFloat(parts[4]),
            command: parts.slice(5).join(' ')
        };
    });
}
```

**fork() - For Node.js child processes with IPC:**
```javascript
// parent.js
import { fork } from 'child_process';

const child = fork('./worker.js', [], {
    stdio: ['pipe', 'pipe', 'pipe', 'ipc']
});

// Send message to child
child.send({ type: 'task', data: 'analyze this' });

// Receive messages from child
child.on('message', (msg) => {
    console.log('Received from child:', msg);
});

// worker.js
process.on('message', (msg) => {
    console.log('Received from parent:', msg);

    // Do work...

    process.send({ type: 'result', data: 'analysis complete' });
});
```

### 2.3 Advanced I/O Capture

**Real-time line-by-line processing:**
```javascript
import { spawn } from 'child_process';
import { createInterface } from 'readline';

class LineBufferedProcess {
    constructor(command, args = []) {
        this.child = spawn(command, args, {
            stdio: ['pipe', 'pipe', 'pipe']
        });

        this.stdoutLines = [];
        this.stderrLines = [];

        // Create readline interfaces for line-by-line processing
        this.stdoutReader = createInterface({
            input: this.child.stdout,
            crlfDelay: Infinity
        });

        this.stderrReader = createInterface({
            input: this.child.stderr,
            crlfDelay: Infinity
        });

        this.stdoutReader.on('line', (line) => {
            this.stdoutLines.push({ time: Date.now(), line });
            this.onLine('stdout', line);
        });

        this.stderrReader.on('line', (line) => {
            this.stderrLines.push({ time: Date.now(), line });
            this.onLine('stderr', line);
        });
    }

    onLine(stream, line) {
        // Override in subclass or assign callback
    }

    async waitForPattern(pattern, timeout = 30000) {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                reject(new Error(`Pattern not found: ${pattern}`));
            }, timeout);

            const checkLine = (stream, line) => {
                if (pattern.test(line)) {
                    clearTimeout(timer);
                    resolve({ stream, line });
                }
            };

            this.onLine = checkLine;
        });
    }
}

// Usage
const proc = new LineBufferedProcess('tail', ['-f', '/var/log/system.log']);
proc.onLine = (stream, line) => {
    if (line.includes('error')) {
        console.log('Error detected:', line);
    }
};
```

**Capturing with timeout and limits:**
```javascript
import { spawn } from 'child_process';

function captureProcess(command, args, options = {}) {
    const {
        timeout = 60000,
        maxOutput = 10 * 1024 * 1024, // 10MB
        onData = null
    } = options;

    return new Promise((resolve, reject) => {
        const child = spawn(command, args);

        let stdout = '';
        let stderr = '';
        let killed = false;

        const timer = setTimeout(() => {
            killed = true;
            child.kill('SIGKILL');
            reject(new Error('Process timeout'));
        }, timeout);

        child.stdout.on('data', (data) => {
            if (stdout.length + data.length <= maxOutput) {
                stdout += data.toString();
                onData?.('stdout', data.toString());
            }
        });

        child.stderr.on('data', (data) => {
            if (stderr.length + data.length <= maxOutput) {
                stderr += data.toString();
                onData?.('stderr', data.toString());
            }
        });

        child.on('close', (code, signal) => {
            clearTimeout(timer);
            if (!killed) {
                resolve({ stdout, stderr, code, signal });
            }
        });

        child.on('error', (err) => {
            clearTimeout(timer);
            reject(err);
        });
    });
}
```

### 2.4 PTY (Pseudo-Terminal) for Full Terminal Emulation

For capturing output from programs that detect TTY (like npm, git with colors):

```javascript
// Requires: npm install node-pty
import * as pty from 'node-pty';

class PTYProcess {
    constructor(command, args = [], options = {}) {
        this.output = [];

        this.pty = pty.spawn(command, args, {
            name: 'xterm-256color',
            cols: options.cols || 120,
            rows: options.rows || 30,
            cwd: options.cwd || process.cwd(),
            env: { ...process.env, ...options.env }
        });

        this.pty.onData((data) => {
            this.output.push({
                time: Date.now(),
                data
            });
            this.onData?.(data);
        });

        this.pty.onExit(({ exitCode, signal }) => {
            this.onExit?.(exitCode, signal);
        });
    }

    write(data) {
        this.pty.write(data);
    }

    resize(cols, rows) {
        this.pty.resize(cols, rows);
    }

    kill(signal = 'SIGTERM') {
        this.pty.kill(signal);
    }

    getOutput() {
        // Strip ANSI codes for plain text
        const ansiRegex = /\x1b\[[0-9;]*m/g;
        return this.output.map(o => o.data).join('').replace(ansiRegex, '');
    }
}

// Usage - captures colored output from npm
const npm = new PTYProcess('npm', ['install']);
npm.onData = (data) => {
    process.stdout.write(data); // Show colored output
};
npm.onExit = (code) => {
    console.log('npm exited with:', code);
};
```

---

## 3. Detecting Process Start/Stop Events

### 3.1 Polling-Based Detection

**Process snapshot comparison:**
```javascript
class ProcessEventDetector {
    constructor(pollInterval = 1000) {
        this.pollInterval = pollInterval;
        this.previousProcesses = new Map();
        this.running = false;
        this.handlers = {
            start: [],
            stop: [],
            change: []
        };
    }

    async getProcessSnapshot() {
        const { execFile } = await import('child_process');
        const { promisify } = await import('util');
        const execFileAsync = promisify(execFile);

        const { stdout } = await execFileAsync('ps', [
            '-eo', 'pid,ppid,user,lstart,command'
        ]);

        const processes = new Map();
        for (const line of stdout.split('\n').slice(1)) {
            const match = line.match(/^\s*(\d+)\s+(\d+)\s+(\S+)\s+(.{24})\s+(.+)$/);
            if (match) {
                const [, pid, ppid, user, lstart, command] = match;
                processes.set(parseInt(pid), {
                    pid: parseInt(pid),
                    ppid: parseInt(ppid),
                    user,
                    startTime: new Date(lstart),
                    command: command.trim()
                });
            }
        }
        return processes;
    }

    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
    }

    emit(event, data) {
        for (const handler of this.handlers[event] || []) {
            handler(data);
        }
    }

    async detectChanges() {
        const currentProcesses = await this.getProcessSnapshot();

        // Detect new processes (started)
        for (const [pid, proc] of currentProcesses) {
            if (!this.previousProcesses.has(pid)) {
                this.emit('start', proc);
            }
        }

        // Detect removed processes (stopped)
        for (const [pid, proc] of this.previousProcesses) {
            if (!currentProcesses.has(pid)) {
                this.emit('stop', proc);
            }
        }

        this.previousProcesses = currentProcesses;
    }

    async start() {
        this.running = true;
        // Initial snapshot
        this.previousProcesses = await this.getProcessSnapshot();

        while (this.running) {
            await new Promise(r => setTimeout(r, this.pollInterval));
            try {
                await this.detectChanges();
            } catch (err) {
                console.error('Detection error:', err);
            }
        }
    }

    stop() {
        this.running = false;
    }
}

// Usage
const detector = new ProcessEventDetector(500); // Check every 500ms

detector.on('start', (proc) => {
    console.log(`STARTED: [${proc.pid}] ${proc.command}`);
});

detector.on('stop', (proc) => {
    console.log(`STOPPED: [${proc.pid}] ${proc.command}`);
});

detector.start();
```

### 3.2 DTrace-Based Detection (macOS)

DTrace provides real-time kernel-level process monitoring without polling.

**DTrace one-liners:**
```bash
# Monitor all process starts
sudo dtrace -n 'proc:::exec-success { printf("%d %s", pid, execname); }'

# Monitor process exits
sudo dtrace -n 'proc:::exit { printf("%d %s exited with %d", pid, execname, arg0); }'

# Monitor specific command starts
sudo dtrace -n 'proc:::exec-success /execname == "node"/ { printf("Node.js started: pid=%d", pid); }'

# Full process lifecycle
sudo dtrace -n '
proc:::exec-success { printf("START %d %s\n", pid, execname); }
proc:::exit { printf("EXIT %d %s %d\n", pid, execname, arg0); }
'
```

**DTrace script for comprehensive monitoring:**
```d
#!/usr/sbin/dtrace -s
/* process_monitor.d - Run with: sudo dtrace -s process_monitor.d */

#pragma D option quiet
#pragma D option switchrate=10hz

dtrace:::BEGIN
{
    printf("Monitoring process events...\n");
    printf("%-6s %-6s %-16s %-8s %s\n",
           "PID", "PPID", "USER", "EVENT", "COMMAND");
}

proc:::exec-success
{
    printf("%-6d %-6d %-16s %-8s %s\n",
           pid, ppid, execname, "START", copyinstr(curpsinfo->pr_psargs));
}

proc:::exit
{
    printf("%-6d %-6d %-16s %-8s exit_code=%d\n",
           pid, ppid, execname, "EXIT", arg0);
}

proc:::signal-send
/args[1]->si_signo == 9 || args[1]->si_signo == 15/
{
    printf("%-6d %-6d %-16s %-8s signal=%d to pid=%d\n",
           pid, ppid, execname, "SIGNAL",
           args[1]->si_signo, args[1]->si_pid);
}
```

**Node.js wrapper for DTrace:**
```javascript
import { spawn } from 'child_process';
import { createInterface } from 'readline';

class DTraceProcessMonitor {
    constructor() {
        this.handlers = { start: [], exit: [], signal: [] };
    }

    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
    }

    start() {
        // Requires sudo privileges
        const dtraceScript = `
            proc:::exec-success {
                printf("START|%d|%d|%s|%s\\n",
                    pid, ppid, execname,
                    copyinstr(curpsinfo->pr_psargs));
            }
            proc:::exit {
                printf("EXIT|%d|%d|%s|%d\\n",
                    pid, ppid, execname, arg0);
            }
        `;

        this.child = spawn('sudo', ['dtrace', '-qn', dtraceScript], {
            stdio: ['ignore', 'pipe', 'pipe']
        });

        const rl = createInterface({ input: this.child.stdout });

        rl.on('line', (line) => {
            const parts = line.split('|');
            if (parts[0] === 'START') {
                for (const h of this.handlers.start) {
                    h({
                        pid: parseInt(parts[1]),
                        ppid: parseInt(parts[2]),
                        execname: parts[3],
                        args: parts[4]
                    });
                }
            } else if (parts[0] === 'EXIT') {
                for (const h of this.handlers.exit) {
                    h({
                        pid: parseInt(parts[1]),
                        ppid: parseInt(parts[2]),
                        execname: parts[3],
                        exitCode: parseInt(parts[4])
                    });
                }
            }
        });

        this.child.stderr.on('data', (data) => {
            console.error('DTrace error:', data.toString());
        });
    }

    stop() {
        this.child?.kill();
    }
}

// Usage (requires sudo)
const monitor = new DTraceProcessMonitor();

monitor.on('start', (proc) => {
    console.log(`Process started: ${proc.execname} (${proc.pid})`);
});

monitor.on('exit', (proc) => {
    console.log(`Process exited: ${proc.execname} (${proc.pid}) code=${proc.exitCode}`);
});

monitor.start();
```

### 3.3 Endpoint Security Framework (ESF)

macOS Endpoint Security Framework provides system-level process monitoring for apps with proper entitlements.

```swift
// Swift implementation (requires EndpointSecurity entitlement)
import EndpointSecurity

class ProcessMonitor {
    var client: OpaquePointer?

    func start() {
        var client: OpaquePointer?

        let result = es_new_client(&client) { (client, message) in
            switch message.pointee.event_type {
            case ES_EVENT_TYPE_NOTIFY_EXEC:
                let process = message.pointee.event.exec.target.pointee
                let pid = audit_token_to_pid(process.audit_token)
                let path = String(cString: process.executable.pointee.path.data)
                print("Process started: \(pid) - \(path)")

            case ES_EVENT_TYPE_NOTIFY_EXIT:
                let pid = audit_token_to_pid(message.pointee.process.pointee.audit_token)
                print("Process exited: \(pid)")

            default:
                break
            }
        }

        guard result == ES_NEW_CLIENT_RESULT_SUCCESS else {
            print("Failed to create ES client")
            return
        }

        self.client = client

        // Subscribe to process events
        es_subscribe(client!, [ES_EVENT_TYPE_NOTIFY_EXEC, ES_EVENT_TYPE_NOTIFY_EXIT])
    }
}
```

---

## 4. Capturing stdin/stdout of Running Processes

### 4.1 Limitations on macOS

**Important:** Capturing stdin/stdout of already-running processes that you didn't spawn is highly restricted on macOS:

1. **No `/proc/PID/fd` filesystem** (unlike Linux)
2. **SIP (System Integrity Protection)** blocks most debugging
3. **Sandboxing** prevents cross-process access
4. **TCC (Transparency, Consent, Control)** requires user permission

### 4.2 DTrace for I/O Tracing

```bash
# Trace all write() syscalls for a specific PID
sudo dtrace -n 'syscall::write:entry /pid == 1234/ {
    printf("%s", copyinstr(arg1, arg2 < 1024 ? arg2 : 1024));
}'

# Trace read/write for a command by name
sudo dtrace -n '
syscall::write:entry /execname == "node"/ {
    self->buf = arg1;
    self->len = arg2;
}
syscall::write:return /execname == "node" && self->buf/ {
    printf("WRITE[%d]: %s", arg0,
           copyinstr(self->buf, self->len < 256 ? self->len : 256));
    self->buf = 0;
}'
```

**DTrace I/O monitoring script:**
```d
#!/usr/sbin/dtrace -s
/* io_trace.d - Trace process I/O */

#pragma D option quiet

syscall::write:entry
/execname == $$1/
{
    self->fd = arg0;
    self->buf = arg1;
    self->len = arg2;
}

syscall::write:return
/self->buf && (self->fd == 1 || self->fd == 2)/
{
    /* Only stdout (1) and stderr (2) */
    printf("[%s][fd=%d] %s\n",
           self->fd == 1 ? "stdout" : "stderr",
           self->fd,
           copyinstr(self->buf, self->len < 512 ? self->len : 512));
    self->buf = 0;
}
```

### 4.3 lldb for Process Attachment (Development Only)

```bash
# Attach to process and capture write() calls
lldb -p 1234 << 'EOF'
breakpoint set -n write -C "expr (void)printf(\"write(%d, %s, %zu)\n\", $arg1, (char*)$arg2, $arg3)" --auto-continue
continue
EOF
```

### 4.4 Log Capture Approach

Instead of capturing process I/O directly, monitor log files:

```javascript
import { watch } from 'fs';
import { createReadStream } from 'fs';
import { createInterface } from 'readline';

class LogFollower {
    constructor(logPath) {
        this.logPath = logPath;
        this.position = 0;
    }

    async start(callback) {
        // Get initial file size
        const { stat } = await import('fs/promises');
        const stats = await stat(this.logPath);
        this.position = stats.size;

        // Watch for changes
        this.watcher = watch(this.logPath, async (eventType) => {
            if (eventType === 'change') {
                await this.readNewContent(callback);
            }
        });
    }

    async readNewContent(callback) {
        const { stat } = await import('fs/promises');
        const stats = await stat(this.logPath);

        if (stats.size > this.position) {
            const stream = createReadStream(this.logPath, {
                start: this.position,
                end: stats.size - 1
            });

            const rl = createInterface({ input: stream });

            for await (const line of rl) {
                callback(line);
            }

            this.position = stats.size;
        }
    }

    stop() {
        this.watcher?.close();
    }
}

// Usage - monitor application logs
const follower = new LogFollower('/var/log/myapp.log');
follower.start((line) => {
    console.log('New log:', line);
});
```

---

## 5. Resource Usage Monitoring

### 5.1 CPU and Memory (vm_stat)

**Memory Statistics:**
```bash
# Detailed memory stats
vm_stat

# Parse for actual usage
vm_stat | awk '/Pages free/ {free=$3} /Pages active/ {active=$3} END {print active, free}'
```

**Python Memory Monitor:**
```python
import subprocess
import re

def get_memory_stats() -> dict:
    """Get memory statistics from vm_stat."""
    result = subprocess.run(
        ["vm_stat"],
        capture_output=True, text=True
    )

    stats = {}
    page_size = 16384  # Default for Apple Silicon (check with vm_stat output)

    # Parse page size from first line
    match = re.search(r'page size of (\d+) bytes', result.stdout)
    if match:
        page_size = int(match.group(1))

    patterns = {
        'pages_free': r'Pages free:\s+(\d+)',
        'pages_active': r'Pages active:\s+(\d+)',
        'pages_inactive': r'Pages inactive:\s+(\d+)',
        'pages_wired': r'Pages wired down:\s+(\d+)',
        'pages_compressed': r'Pages stored in compressor:\s+(\d+)',
        'pages_speculative': r'Pages speculative:\s+(\d+)',
        'pageins': r'Pageins:\s+(\d+)',
        'pageouts': r'Pageouts:\s+(\d+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, result.stdout)
        if match:
            pages = int(match.group(1).replace('.', ''))
            stats[key] = pages
            stats[key.replace('pages_', 'bytes_')] = pages * page_size

    # Calculate totals
    total_pages = sum(stats.get(k, 0) for k in ['pages_free', 'pages_active',
                                                  'pages_inactive', 'pages_wired'])
    stats['total_bytes'] = total_pages * page_size
    stats['used_bytes'] = (stats.get('pages_active', 0) +
                           stats.get('pages_wired', 0)) * page_size
    stats['page_size'] = page_size

    return stats

def get_memory_pressure() -> str:
    """Get current memory pressure level."""
    result = subprocess.run(
        ["memory_pressure"],
        capture_output=True, text=True
    )

    output = result.stdout.lower()
    if 'no memory pressure' in output:
        return 'normal'
    elif 'warning' in output:
        return 'warning'
    elif 'critical' in output:
        return 'critical'

    return 'unknown'
```

### 5.2 Per-Process Resource Monitoring

```python
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessResourceUsage:
    pid: int
    cpu_percent: float
    mem_percent: float
    rss_bytes: int
    vsz_bytes: int
    threads: int
    open_files: int
    timestamp: float

def get_process_resources(pid: int) -> Optional[ProcessResourceUsage]:
    """Get detailed resource usage for a specific process."""
    try:
        # Get basic stats from ps
        result = subprocess.run(
            ["ps", "-o", "%cpu,%mem,rss,vsz,", "-p", str(pid)],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return None

        parts = lines[1].split()
        if len(parts) < 4:
            return None

        # Get thread count
        thread_result = subprocess.run(
            ["ps", "-M", "-p", str(pid)],
            capture_output=True, text=True
        )
        thread_count = len(thread_result.stdout.strip().split('\n')) - 1

        # Get open file count
        lsof_result = subprocess.run(
            ["lsof", "-p", str(pid)],
            capture_output=True, text=True
        )
        open_files = len(lsof_result.stdout.strip().split('\n')) - 1

        return ProcessResourceUsage(
            pid=pid,
            cpu_percent=float(parts[0]),
            mem_percent=float(parts[1]),
            rss_bytes=int(parts[2]) * 1024,  # KB to bytes
            vsz_bytes=int(parts[3]) * 1024,
            threads=max(1, thread_count),
            open_files=max(0, open_files),
            timestamp=time.time()
        )
    except Exception as e:
        print(f"Error getting process resources: {e}")
        return None

class ProcessResourceTracker:
    """Track resource usage over time for a process."""

    def __init__(self, pid: int, interval: float = 1.0):
        self.pid = pid
        self.interval = interval
        self.history = []
        self.running = False

    def sample(self) -> Optional[ProcessResourceUsage]:
        usage = get_process_resources(self.pid)
        if usage:
            self.history.append(usage)
            # Keep last 1000 samples
            if len(self.history) > 1000:
                self.history = self.history[-1000:]
        return usage

    def get_averages(self, last_n: int = 60) -> dict:
        """Get average resource usage over last N samples."""
        samples = self.history[-last_n:]
        if not samples:
            return {}

        return {
            'avg_cpu': sum(s.cpu_percent for s in samples) / len(samples),
            'avg_mem': sum(s.mem_percent for s in samples) / len(samples),
            'max_cpu': max(s.cpu_percent for s in samples),
            'max_mem': max(s.mem_percent for s in samples),
            'avg_threads': sum(s.threads for s in samples) / len(samples),
            'avg_files': sum(s.open_files for s in samples) / len(samples),
        }

    async def start(self):
        """Start continuous monitoring."""
        import asyncio
        self.running = True
        while self.running:
            self.sample()
            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False
```

### 5.3 Disk I/O (iostat)

```bash
# Basic disk I/O stats
iostat -c 3

# Detailed with KB/s
iostat -d -K

# Continuous monitoring
iostat -w 2
```

**Disk Space:**
```bash
# Human-readable disk usage
df -h

# Specific filesystem
df -h /

# Inodes
df -i
```

**Python Disk Monitor:**
```python
import subprocess
import re

def get_disk_usage() -> list[dict]:
    """Get disk usage for all mounted filesystems."""
    result = subprocess.run(
        ["df", "-h"],
        capture_output=True, text=True
    )

    disks = []
    for line in result.stdout.split('\n')[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 6:
            disks.append({
                'filesystem': parts[0],
                'size': parts[1],
                'used': parts[2],
                'available': parts[3],
                'capacity': parts[4],
                'mount': parts[5]
            })

    return disks

def get_iostat() -> dict:
    """Get I/O statistics."""
    result = subprocess.run(
        ["iostat", "-c", "1"],
        capture_output=True, text=True
    )

    stats = {}
    for line in result.stdout.split('\n'):
        # Parse disk line (disk0)
        match = re.search(r'(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)', line)
        if match:
            stats['kb_per_transfer'] = float(match.group(1))
            stats['transfers'] = int(match.group(2))
            stats['mb_per_sec'] = float(match.group(3))
            break

    return stats
```

### 5.4 GPU Utilization

**System Profiler:**
```bash
# GPU information
system_profiler SPDisplaysDataType

# Compact format
system_profiler SPDisplaysDataType -json
```

**Metal GPU Activity (powermetrics - requires sudo):**
```bash
# GPU power and frequency (requires sudo)
sudo powermetrics --samplers gpu_power -i 1000 -n 1

# Comprehensive power info
sudo powermetrics --samplers all -i 1000 -n 1
```

**Python GPU Monitor:**
```python
import subprocess
import json

def get_gpu_info() -> dict:
    """Get GPU information from system profiler."""
    result = subprocess.run(
        ["system_profiler", "SPDisplaysDataType", "-json"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        data = json.loads(result.stdout)
        displays = data.get('SPDisplaysDataType', [])

        if displays:
            gpu = displays[0]
            return {
                'name': gpu.get('sppci_model', 'Unknown'),
                'vendor': gpu.get('sppci_vendor', 'Unknown'),
                'cores': gpu.get('sppci_cores', 'Unknown'),
                'metal_support': gpu.get('sppci_metal', 'Unknown'),
                'vram': gpu.get('sppci_vram', 'Unknown'),
            }

    return {}
```

---

## 6. Security Considerations and Permissions

### 6.1 macOS Permission Levels

| Capability | Permission Required | How to Grant |
|------------|---------------------|--------------|
| Basic process list (`ps`) | None | Default |
| Own process files (`lsof -p self`) | None | Default |
| Other users' processes | None (limited info) | Default |
| System process details | Admin or root | `sudo` |
| DTrace monitoring | Root | `sudo` |
| Accessibility (window info) | TCC | System Preferences > Privacy |
| Full Disk Access | TCC | System Preferences > Privacy |
| Endpoint Security | Entitlement | Apple Developer signing |
| Kernel debugging | Disabled by SIP | `csrutil disable` (not recommended) |

### 6.2 TCC (Transparency, Consent, and Control)

```bash
# Check current TCC permissions for an app
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db \
    "SELECT * FROM access WHERE service = 'kTCCServiceAccessibility';"

# Reset TCC permissions (requires restart)
tccutil reset All
```

**Requesting permissions programmatically (Swift):**
```swift
import ApplicationServices

// Check accessibility permission
func checkAccessibility() -> Bool {
    let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue(): true] as CFDictionary
    return AXIsProcessTrustedWithOptions(options)
}
```

### 6.3 SIP (System Integrity Protection)

```bash
# Check SIP status
csrutil status

# SIP protects:
# - /System
# - /usr (except /usr/local)
# - /bin, /sbin
# - Apple-signed apps

# To modify protected processes, SIP must be disabled (NOT RECOMMENDED)
# Boot to Recovery Mode (Cmd+R) and run: csrutil disable
```

### 6.4 Sandbox Restrictions

```bash
# Check if a process is sandboxed
codesign -d --entitlements :- /path/to/app 2>&1 | grep sandbox

# Sandboxed apps cannot:
# - Access files outside their container without permission
# - Use certain system APIs
# - Attach to other processes
```

### 6.5 Security Best Practices for Process Monitoring

```python
import os
import subprocess

class SecureProcessMonitor:
    """Process monitor with security considerations."""

    def __init__(self):
        self.uid = os.getuid()
        self.is_root = self.uid == 0

    def get_accessible_processes(self) -> list[dict]:
        """Get only processes we're allowed to monitor."""
        processes = []

        # Get our own processes
        result = subprocess.run(
            ["ps", "-u", str(self.uid), "-o", "pid,command"],
            capture_output=True, text=True
        )

        for line in result.stdout.strip().split('\n')[1:]:
            parts = line.split(None, 1)
            if len(parts) >= 2:
                processes.append({
                    'pid': int(parts[0]),
                    'command': parts[1],
                    'owned': True
                })

        return processes

    def can_monitor_pid(self, pid: int) -> bool:
        """Check if we can monitor a specific PID."""
        if self.is_root:
            return True

        # Check if process belongs to us
        result = subprocess.run(
            ["ps", "-o", "user=", "-p", str(pid)],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return False

        process_user = result.stdout.strip()
        current_user = subprocess.run(
            ["whoami"], capture_output=True, text=True
        ).stdout.strip()

        return process_user == current_user

    def sanitize_command(self, command: str) -> str:
        """Remove sensitive information from command strings."""
        # Patterns that might contain secrets
        sensitive_patterns = [
            r'--password[=\s]+\S+',
            r'--token[=\s]+\S+',
            r'--api-key[=\s]+\S+',
            r'--secret[=\s]+\S+',
            r'(?:API_KEY|SECRET|TOKEN|PASSWORD)=\S+',
        ]

        import re
        sanitized = command
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.I)

        return sanitized
```

---

## 7. Unified Monitoring Class

```python
import subprocess
import time
import json
import threading
import asyncio
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable, List
from datetime import datetime

@dataclass
class ProcessEvent:
    """Represents a process lifecycle event."""
    event_type: str  # 'start', 'stop', 'resource_spike'
    pid: int
    command: str
    timestamp: float
    details: dict = field(default_factory=dict)

@dataclass
class SystemState:
    """Current system state snapshot."""
    timestamp: float

    # CPU
    cpu_user: float
    cpu_sys: float
    cpu_idle: float
    load_1m: float
    load_5m: float
    load_15m: float

    # Memory
    mem_used_gb: float
    mem_free_gb: float
    mem_pressure: str

    # Disk
    disk_used_percent: float

    # Process counts
    processes_total: int
    processes_running: int

    # App Focus
    frontmost_app: str
    frontmost_window: str

    # Network
    active_connections: int
    listening_ports: int

    def to_dict(self) -> dict:
        return asdict(self)

    def to_llm_context(self) -> str:
        """Format for LLM context injection."""
        return f"""SYSTEM STATE ({datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')}):
- CPU: {self.cpu_user:.1f}% user, {self.cpu_sys:.1f}% sys, {self.cpu_idle:.1f}% idle
- Load: {self.load_1m:.2f} / {self.load_5m:.2f} / {self.load_15m:.2f}
- Memory: {self.mem_used_gb:.1f}GB used, {self.mem_free_gb:.1f}GB free ({self.mem_pressure})
- Disk: {self.disk_used_percent:.1f}% used
- Processes: {self.processes_running}/{self.processes_total} running
- Focus: {self.frontmost_app} - {self.frontmost_window[:50] if self.frontmost_window else 'N/A'}
- Network: {self.active_connections} connections, {self.listening_ports} listening"""


class ConsciousnessProcessMonitor:
    """Unified system monitoring for AI consciousness layer."""

    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self.running = False
        self.current_state: Optional[SystemState] = None
        self.state_callbacks: List[Callable[[SystemState], None]] = []
        self.event_callbacks: List[Callable[[ProcessEvent], None]] = []
        self.previous_pids: set = set()
        self.process_info_cache: dict = {}

    def add_state_callback(self, callback: Callable[[SystemState], None]):
        """Add callback for state updates."""
        self.state_callbacks.append(callback)

    def add_event_callback(self, callback: Callable[[ProcessEvent], None]):
        """Add callback for process events."""
        self.event_callbacks.append(callback)

    def _run_cmd(self, cmd: list[str]) -> str:
        """Run command and return output."""
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def _get_top_stats(self) -> dict:
        """Get CPU/memory stats from top."""
        output = self._run_cmd(["top", "-l", "1", "-n", "0"])
        stats = {
            'cpu_user': 0, 'cpu_sys': 0, 'cpu_idle': 100,
            'load_1m': 0, 'load_5m': 0, 'load_15m': 0,
            'mem_used_gb': 0, 'mem_free_gb': 0,
            'processes_total': 0, 'processes_running': 0
        }

        import re
        for line in output.split('\n'):
            if 'Processes:' in line:
                match = re.search(r'(\d+) total, (\d+) running', line)
                if match:
                    stats['processes_total'] = int(match.group(1))
                    stats['processes_running'] = int(match.group(2))

            elif 'Load Avg' in line:
                match = re.search(r'Load Avg: ([\d.]+), ([\d.]+), ([\d.]+)', line)
                if match:
                    stats['load_1m'] = float(match.group(1))
                    stats['load_5m'] = float(match.group(2))
                    stats['load_15m'] = float(match.group(3))

            elif 'CPU usage' in line:
                match = re.search(r'([\d.]+)% user, ([\d.]+)% sys, ([\d.]+)% idle', line)
                if match:
                    stats['cpu_user'] = float(match.group(1))
                    stats['cpu_sys'] = float(match.group(2))
                    stats['cpu_idle'] = float(match.group(3))

            elif 'PhysMem' in line:
                match = re.search(r'(\d+)([GMK])? used.*?(\d+)([GMK])? unused', line)
                if match:
                    used = int(match.group(1))
                    used_unit = match.group(2) or 'M'
                    free = int(match.group(3))
                    free_unit = match.group(4) or 'M'

                    multipliers = {'G': 1, 'M': 1/1024, 'K': 1/(1024*1024)}
                    stats['mem_used_gb'] = used * multipliers.get(used_unit, 1/1024)
                    stats['mem_free_gb'] = free * multipliers.get(free_unit, 1/1024)

        return stats

    def _get_frontmost_app(self) -> tuple[str, str]:
        """Get frontmost application and window title."""
        script = '''
        tell application "System Events"
            set frontProc to first process whose frontmost is true
            set appName to name of frontProc
            set winTitle to ""
            tell frontProc
                if (count of windows) > 0 then
                    set winTitle to name of window 1
                end if
            end tell
            return appName & "|" & winTitle
        end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split('|', 1)
            return parts[0], parts[1] if len(parts) > 1 else ''

        return 'Unknown', ''

    def _get_disk_usage(self) -> float:
        """Get root disk usage percentage."""
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True
        )

        for line in result.stdout.split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 5:
                return float(parts[4].rstrip('%'))

        return 0.0

    def _get_network_stats(self) -> tuple[int, int]:
        """Get network connection counts."""
        result = subprocess.run(
            ["netstat", "-an"],
            capture_output=True, text=True
        )

        established = result.stdout.count('ESTABLISHED')
        listening = result.stdout.count('LISTEN')

        return established, listening

    def _get_memory_pressure(self) -> str:
        """Get memory pressure level."""
        result = subprocess.run(
            ["memory_pressure"],
            capture_output=True, text=True
        )

        output = result.stdout.lower()
        if 'no memory pressure' in output:
            return 'normal'
        elif 'warning' in output:
            return 'warning'
        elif 'critical' in output:
            return 'critical'

        return 'unknown'

    def _get_current_pids(self) -> dict[int, str]:
        """Get current PIDs and their commands."""
        result = subprocess.run(
            ["ps", "-eo", "pid,command"],
            capture_output=True, text=True
        )

        pids = {}
        for line in result.stdout.strip().split('\n')[1:]:
            parts = line.strip().split(None, 1)
            if len(parts) >= 2:
                try:
                    pids[int(parts[0])] = parts[1]
                except ValueError:
                    pass
        return pids

    def _detect_process_events(self) -> List[ProcessEvent]:
        """Detect process start/stop events."""
        events = []
        current_pids = self._get_current_pids()
        current_pid_set = set(current_pids.keys())

        # Detect new processes
        for pid in current_pid_set - self.previous_pids:
            command = current_pids.get(pid, 'unknown')
            events.append(ProcessEvent(
                event_type='start',
                pid=pid,
                command=command,
                timestamp=time.time()
            ))

        # Detect stopped processes
        for pid in self.previous_pids - current_pid_set:
            command = self.process_info_cache.get(pid, 'unknown')
            events.append(ProcessEvent(
                event_type='stop',
                pid=pid,
                command=command,
                timestamp=time.time()
            ))

        # Update cache
        self.previous_pids = current_pid_set
        self.process_info_cache.update(current_pids)

        return events

    def snapshot(self) -> SystemState:
        """Take a complete system state snapshot."""
        top_stats = self._get_top_stats()
        app_name, window_title = self._get_frontmost_app()
        connections, listening = self._get_network_stats()

        state = SystemState(
            timestamp=time.time(),
            cpu_user=top_stats['cpu_user'],
            cpu_sys=top_stats['cpu_sys'],
            cpu_idle=top_stats['cpu_idle'],
            load_1m=top_stats['load_1m'],
            load_5m=top_stats['load_5m'],
            load_15m=top_stats['load_15m'],
            mem_used_gb=top_stats['mem_used_gb'],
            mem_free_gb=top_stats['mem_free_gb'],
            mem_pressure=self._get_memory_pressure(),
            disk_used_percent=self._get_disk_usage(),
            processes_total=top_stats['processes_total'],
            processes_running=top_stats['processes_running'],
            frontmost_app=app_name,
            frontmost_window=window_title,
            active_connections=connections,
            listening_ports=listening
        )

        self.current_state = state
        return state

    def _monitor_loop(self):
        """Main monitoring loop."""
        # Initialize previous PIDs
        self.previous_pids = set(self._get_current_pids().keys())

        while self.running:
            # Take state snapshot
            state = self.snapshot()
            for callback in self.state_callbacks:
                try:
                    callback(state)
                except Exception as e:
                    print(f"State callback error: {e}")

            # Detect process events
            events = self._detect_process_events()
            for event in events:
                for callback in self.event_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Event callback error: {e}")

            time.sleep(self.poll_interval)

    def start(self):
        """Start background monitoring."""
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background monitoring."""
        self.running = False
        if hasattr(self, '_thread'):
            self._thread.join(timeout=2.0)


# Usage Example
if __name__ == "__main__":
    monitor = ConsciousnessProcessMonitor(poll_interval=1.0)

    def on_state(state: SystemState):
        print("\n" + state.to_llm_context())

    def on_event(event: ProcessEvent):
        print(f"[PROCESS {event.event_type.upper()}] PID={event.pid} CMD={event.command[:60]}")

    monitor.add_state_callback(on_state)
    monitor.add_event_callback(on_event)
    monitor.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        monitor.stop()
```

---

## 8. LLM Context Integration

### 8.1 Context Injection Format

For feeding system state into an LLM context window:

```python
def generate_consciousness_context(monitor: ConsciousnessProcessMonitor) -> str:
    """Generate context block for LLM injection."""
    state = monitor.current_state
    if not state:
        return ""

    # Calculate cognitive load estimate
    cpu_load = 100 - state.cpu_idle
    mem_pressure_score = {'normal': 0, 'warning': 50, 'critical': 100}.get(
        state.mem_pressure, 25
    )
    cognitive_load = (cpu_load * 0.4 + mem_pressure_score * 0.4 +
                      (state.load_1m / 8 * 100) * 0.2)

    return f"""<system_awareness>
ENVIRONMENTAL CONTEXT (real-time):
- Active Application: {state.frontmost_app}
- Window Context: {state.frontmost_window}
- System Load: {'high' if cognitive_load > 70 else 'moderate' if cognitive_load > 40 else 'low'}
- Available Resources: {state.mem_free_gb:.0f}GB RAM, {100-state.disk_used_percent:.0f}% disk
- Process Activity: {state.processes_running} running of {state.processes_total}
- Network Activity: {state.active_connections} connections
- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
</system_awareness>"""
```

### 8.2 Threshold-Based Alerts

```python
from dataclasses import dataclass

@dataclass
class SystemAlert:
    level: str  # 'info', 'warning', 'critical'
    category: str
    message: str
    timestamp: float

def check_system_alerts(state: SystemState) -> list[SystemAlert]:
    """Check for system conditions that should influence AI behavior."""
    alerts = []

    # High CPU load
    if state.cpu_idle < 20:
        alerts.append(SystemAlert(
            level='warning',
            category='cpu',
            message='High CPU utilization - consider deferring intensive operations',
            timestamp=time.time()
        ))

    # Memory pressure
    if state.mem_pressure == 'critical':
        alerts.append(SystemAlert(
            level='critical',
            category='memory',
            message='Critical memory pressure - avoid memory-intensive operations',
            timestamp=time.time()
        ))

    # Disk space
    if state.disk_used_percent > 90:
        alerts.append(SystemAlert(
            level='warning',
            category='disk',
            message='Low disk space - clean up before creating files',
            timestamp=time.time()
        ))

    # High system load
    if state.load_1m > 10:
        alerts.append(SystemAlert(
            level='warning',
            category='load',
            message='System under heavy load - responses may be slower',
            timestamp=time.time()
        ))

    # Many processes
    if state.processes_running > 50:
        alerts.append(SystemAlert(
            level='info',
            category='processes',
            message='High process count - system is busy',
            timestamp=time.time()
        ))

    return alerts
```

---

## 9. Summary

| Capability | Tool | Permissions | Latency | Notes |
|------------|------|-------------|---------|-------|
| Process list | `ps` | None | ~10ms | BSD-style options on macOS |
| CPU/Memory | `top -l 1` | None | ~500ms | Non-interactive mode |
| Active window | `osascript` | Accessibility | ~100ms | TCC permission needed |
| Clipboard | `pbpaste` | None | ~10ms | - |
| Network | `netstat`/`lsof` | None | ~50ms | - |
| Disk I/O | `iostat` | None | ~100ms | - |
| GPU info | `system_profiler` | None | ~1s | - |
| GPU power | `powermetrics` | Root | ~1s | Sudo required |
| Services | `launchctl` | None | ~50ms | - |
| System info | `sysctl` | None | ~10ms | - |
| Process events | DTrace | Root | Real-time | Best for event detection |
| Open files | `lsof -p PID` | None (own) | ~100ms | Limited for other users |
| I/O tracing | DTrace | Root | Real-time | Captures reads/writes |

### Key Insights for Consciousness Systems

1. **Polling vs Events**: Use polling for state snapshots, DTrace for real-time events
2. **Permission Boundaries**: Respect macOS security model; work within sandbox constraints
3. **Performance Impact**: Monitor at appropriate intervals; too frequent polling wastes resources
4. **Privacy Awareness**: Sanitize command lines and window titles that may contain secrets
5. **Graceful Degradation**: Handle permission denials gracefully; provide partial data when full access unavailable

This monitoring infrastructure provides the foundation for an AI consciousness layer to maintain awareness of its operating environment and adapt its behavior accordingly.

---

## Sources

### Apple Documentation
- [Process Information](https://developer.apple.com/documentation/darwin/process-information)
- [Endpoint Security](https://developer.apple.com/documentation/endpointsecurity)
- [DTrace Guide](https://www.oracle.com/solaris/technologies/dtrace-tutorial.html)

### Node.js Documentation
- [child_process module](https://nodejs.org/api/child_process.html)
- [process module](https://nodejs.org/api/process.html)

### macOS Man Pages
- `man ps` - Process status
- `man top` - Display sorted information about processes
- `man lsof` - List open files
- `man launchctl` - Interfaces with launchd
- `man sysctl` - Get or set kernel state
- `man dtrace` - Dynamic tracing compiler and tracing utility

---

*Research compiled: 2026-01-04*
*Status: Active research document*
