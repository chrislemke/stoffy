#!/usr/bin/env python3
"""
Consciousness Daemon Validation Script

Validates that all components are properly configured and operational:
1. LM Studio connection (localhost:1234)
2. Claude Code CLI availability
3. File system permissions
4. Python dependencies
5. Configuration files

Run with: python -m consciousness.validate
Or: python consciousness/validate.py
"""

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_check(name: str, passed: bool, message: str = "") -> None:
    """Print a validation check result."""
    status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
    print(f"  [{status}] {name}")
    if message:
        color = Colors.GREEN if passed else Colors.RED
        print(f"         {color}{message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"  {Colors.YELLOW}[WARN] {message}{Colors.RESET}")


def check_lm_studio_connection() -> Tuple[bool, str]:
    """
    Check if LM Studio is running and accessible.

    LM Studio should be running at http://localhost:1234
    with a model loaded for inference.
    """
    try:
        import httpx

        response = httpx.get(
            "http://localhost:1234/v1/models",
            timeout=5.0,
        )

        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            if models:
                model_id = models[0].get("id", "unknown")
                return True, f"Connected, model: {model_id}"
            return True, "Connected, no models loaded"
        return False, f"HTTP {response.status_code}"

    except ImportError:
        # Try with urllib if httpx not available
        try:
            import urllib.request
            import json

            req = urllib.request.Request("http://localhost:1234/v1/models")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                models = data.get("data", [])
                if models:
                    model_id = models[0].get("id", "unknown")
                    return True, f"Connected, model: {model_id}"
                return True, "Connected, no models loaded"
        except Exception as e:
            return False, str(e)

    except Exception as e:
        return False, str(e)


def check_claude_code_available() -> Tuple[bool, str]:
    """
    Check if Claude Code CLI is available.

    Tests:
    - claude --version command
    - Claude executable in PATH
    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            return True, f"Version: {version}"
        return False, f"Exit code: {result.returncode}"

    except FileNotFoundError:
        return False, "claude not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_file_permissions(path: str) -> Tuple[bool, str]:
    """
    Check if we have appropriate file permissions for the target directory.

    Tests:
    - Directory exists
    - Read permission
    - Write permission (to temp file)
    """
    target_path = Path(path)

    if not target_path.exists():
        return False, f"Path does not exist: {path}"

    if not target_path.is_dir():
        return False, f"Path is not a directory: {path}"

    # Check read permission
    try:
        list(target_path.iterdir())
    except PermissionError:
        return False, "No read permission"

    # Check write permission with temp file
    try:
        test_file = target_path / ".consciousness_write_test"
        test_file.write_text("test")
        test_file.unlink()
    except PermissionError:
        return False, "No write permission"
    except Exception as e:
        return False, f"Write test failed: {e}"

    return True, f"Full access to {path}"


def check_python_dependencies() -> Tuple[bool, str]:
    """
    Check if required Python dependencies are installed.

    Required packages:
    - watchfiles (file system watching)
    - openai (LM Studio client)
    - anthropic (Claude API)
    - pydantic (configuration)
    - structlog (logging)
    - typer (CLI)
    """
    required = [
        "watchfiles",
        "openai",
        "anthropic",
        "pydantic",
        "pydantic_settings",
        "structlog",
        "typer",
        "rich",
        "pyyaml",
    ]

    missing = []
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)

    if missing:
        return False, f"Missing: {', '.join(missing)}"

    return True, f"All {len(required)} packages installed"


def check_configuration() -> Tuple[bool, str]:
    """
    Check for configuration files.

    Looks for:
    - consciousness.yaml in current directory
    - consciousness.yaml in config/ subdirectory
    - ~/.config/consciousness.yaml
    """
    possible_paths = [
        Path("consciousness.yaml"),
        Path("config/consciousness.yaml"),
        Path.home() / ".config" / "consciousness.yaml",
    ]

    for path in possible_paths:
        if path.exists():
            return True, f"Found: {path}"

    return False, "No consciousness.yaml found (will use defaults)"


def check_stoffy_structure() -> Tuple[bool, str]:
    """
    Check if we're in the Stoffy repository with expected structure.
    """
    expected_dirs = [
        "knowledge",
        "indices",
        ".claude",
    ]

    stoffy_path = Path("/Users/chris/Developer/stoffy")

    if not stoffy_path.exists():
        return False, f"Stoffy path not found: {stoffy_path}"

    missing = []
    for dir_name in expected_dirs:
        if not (stoffy_path / dir_name).exists():
            missing.append(dir_name)

    if missing:
        return False, f"Missing directories: {', '.join(missing)}"

    return True, f"Stoffy structure valid at {stoffy_path}"


def check_anthropic_api_key() -> Tuple[bool, str]:
    """
    Check if ANTHROPIC_API_KEY is set.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")

    if not key:
        return False, "ANTHROPIC_API_KEY not set"

    if len(key) < 20:
        return False, "ANTHROPIC_API_KEY looks invalid (too short)"

    # Mask the key for display
    masked = key[:8] + "..." + key[-4:]
    return True, f"Set: {masked}"


async def check_async_observer() -> Tuple[bool, str]:
    """
    Test that the async file observer can be started.
    """
    try:
        # Import the observer
        sys.path.insert(0, str(Path(__file__).parent.parent / "docs" / "consciousness-research" / "implementation"))
        from consciousness.observers.filesystem import FileSystemObserver

        with tempfile.TemporaryDirectory() as tmpdir:
            observer = FileSystemObserver(
                watch_paths=[tmpdir],
                ignore_patterns=[],
                debounce_ms=100,
                root_path=Path(tmpdir),
            )

            await observer.start()

            # Create a test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            await asyncio.sleep(0.2)

            observations = await observer.get_observations()
            await observer.stop()

            if observations:
                return True, f"Observer working, detected {len(observations)} events"
            return True, "Observer started successfully (no events in brief test)"

    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def validate_all() -> bool:
    """
    Run all validation checks and return overall status.
    """
    print_header("CONSCIOUSNESS DAEMON VALIDATION")

    all_passed = True
    critical_passed = True

    # Critical checks
    print(f"{Colors.BOLD}Critical Components:{Colors.RESET}")

    # LM Studio
    passed, msg = check_lm_studio_connection()
    print_check("LM Studio Connection", passed, msg)
    if not passed:
        critical_passed = False
        print_warning("Start LM Studio and load a model at http://localhost:1234")

    # Claude Code
    passed, msg = check_claude_code_available()
    print_check("Claude Code CLI", passed, msg)
    if not passed:
        print_warning("Install Claude Code: npm install -g @anthropic-ai/claude-code")

    # Anthropic API Key
    passed, msg = check_anthropic_api_key()
    print_check("Anthropic API Key", passed, msg)
    if not passed:
        critical_passed = False
        print_warning("Set ANTHROPIC_API_KEY in environment")

    # File permissions
    stoffy_path = "/Users/chris/Developer/stoffy"
    passed, msg = check_file_permissions(stoffy_path)
    print_check("File Permissions", passed, msg)
    if not passed:
        critical_passed = False

    print(f"\n{Colors.BOLD}Dependencies:{Colors.RESET}")

    # Python dependencies
    passed, msg = check_python_dependencies()
    print_check("Python Packages", passed, msg)
    if not passed:
        all_passed = False
        print_warning("Install with: pip install -r requirements.txt")

    print(f"\n{Colors.BOLD}Configuration:{Colors.RESET}")

    # Configuration file
    passed, msg = check_configuration()
    print_check("Configuration File", passed, msg)
    if not passed:
        print_warning("Optional: Create consciousness.yaml for custom settings")

    # Stoffy structure
    passed, msg = check_stoffy_structure()
    print_check("Stoffy Repository", passed, msg)
    if not passed:
        all_passed = False

    print(f"\n{Colors.BOLD}Runtime Tests:{Colors.RESET}")

    # Async observer test
    passed, msg = asyncio.run(check_async_observer())
    print_check("File System Observer", passed, msg)
    if not passed:
        all_passed = False

    # Summary
    print_header("VALIDATION SUMMARY")

    if critical_passed and all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}All checks passed! Consciousness daemon is ready to run.{Colors.RESET}")
        print(f"\nStart with: {Colors.BLUE}python -m consciousness run{Colors.RESET}")
        return True
    elif critical_passed:
        print(f"{Colors.YELLOW}{Colors.BOLD}Some non-critical checks failed. Daemon may still run with limitations.{Colors.RESET}")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}Critical checks failed. Please resolve issues before running.{Colors.RESET}")
        return False


def main():
    """Main entry point."""
    try:
        success = validate_all()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validation cancelled.{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Validation error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
