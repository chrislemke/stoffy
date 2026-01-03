# ═══════════════════════════════════════════════════════════════════════════════
#  Makefile for open_assistant environment
# ═══════════════════════════════════════════════════════════════════════════════
#
#  Usage: make [target]
#
#  Run 'make help' for a list of available targets.
#  Run 'make setup' for interactive guided setup (recommended for first-time).
#
# ═══════════════════════════════════════════════════════════════════════════════

# --- Configuration ---
ENV_NAME ?= open_assistant
BREWFILE := Brewfile
CONDA_LOCK_FILE := conda-lock.yml
REPO_ROOT := $(shell pwd)
SHELL := /bin/bash

# Reminder daemon configuration
LAUNCHAGENT_LABEL := com.leadstuff.calendar-reminder
LAUNCHAGENT_PLIST := $(HOME)/Library/LaunchAgents/$(LAUNCHAGENT_LABEL).plist
LAUNCHAGENT_TEMPLATE := scripts/launchagent/$(LAUNCHAGENT_LABEL).plist.template

# Setup tracking directory
MARKERS_DIR := .setup_markers

# --- Phony Targets ---
.PHONY: all setup help check-homebrew brew pre-commit conda activate auth gh-login \
        install-reminder-daemon uninstall-reminder-daemon reminder-status reminder-test \
        clean uninstall \
        _step_homebrew _step_brew _step_precommit _step_conda _step_activate _step_optional

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

## Interactive guided setup (recommended for first-time users)
setup:
	@printf '\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\033[1m  open_assistant Setup\033[0m\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'
	@mkdir -p $(MARKERS_DIR)
	@$(MAKE) --no-print-directory _step_homebrew
	@$(MAKE) --no-print-directory _step_brew
	@$(MAKE) --no-print-directory _step_precommit
	@$(MAKE) --no-print-directory _step_conda
	@$(MAKE) --no-print-directory _step_activate
	@$(MAKE) --no-print-directory _step_optional
	@printf '\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\033[32m\033[1m  Setup complete!\033[0m\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'
	@printf 'Next steps:\n'
	@SHELL_CONFIG=""; \
	if [ -n "$$ZSH_VERSION" ] || [ "$$SHELL" = "/bin/zsh" ]; then \
		SHELL_CONFIG="$$HOME/.zshrc"; \
	else \
		SHELL_CONFIG="$$HOME/.bashrc"; \
	fi; \
	if [ -f "$(MARKERS_DIR)/alias_added" ]; then \
		printf '  1. Restart terminal or run: source %s\n' "$$SHELL_CONFIG"; \
		printf '  2. Start working: \033[36mopen_assistant\033[0m (or just: \033[36moa\033[0m)\n'; \
	else \
		printf '  1. Activate environment: \033[36msource scripts/activate.sh\033[0m\n'; \
		printf '  2. Start opencode: \033[36mopencode\033[0m\n'; \
	fi; \
	printf '  3. Check reminders: \033[36mmake reminder-status\033[0m\n'
	@printf '\n'
	@say "setup completed" 2>/dev/null || true

## Show this help message
help:
	@printf '\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\033[1m  open_assistant - Makefile Help\033[0m\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'
	@printf 'Usage: make [target]\n'
	@printf '\n'
	@printf '\033[1mSETUP\033[0m\n'
	@printf '  setup                      Interactive guided setup (start here!)\n'
	@printf '                             Auto-detects conda/mamba/micromamba;\n'
	@printf '                             installs micromamba if none found\n'
	@printf '  check-homebrew             Check/install Homebrew\n'
	@printf '  brew                       Install dependencies from Brewfile\n'
	@printf '  pre-commit                 Install pre-commit Git hooks\n'
	@printf '  conda                      Create conda environment\n'
	@printf '  activate                   Create activation script & configure shell\n'
	@printf '  auth                       Authenticate with opencode\n'
	@printf '  gh-login                   Authenticate with GitHub CLI\n'
	@printf '\n'
	@printf '\033[1mREMINDER DAEMON\033[0m\n'
	@printf '  install-reminder-daemon    Install background notification service\n'
	@printf '  uninstall-reminder-daemon  Remove notification service\n'
	@printf '  reminder-status            Check status & send test notification\n'
	@printf '  reminder-test              Send test notification only\n'
	@printf '\n'
	@printf '\033[1mCLEANUP\033[0m\n'
	@printf '  clean                      Remove conda environment only\n'
	@printf '  uninstall                  Remove everything installed by setup\n'
	@printf '\n'
	@printf '\033[1mVARIABLES\033[0m\n'
	@printf '  ENV_NAME                   Conda environment name (default: %s)\n' "$(ENV_NAME)"
	@printf '\n'
	@printf '\033[1mEXAMPLES\033[0m\n'
	@printf '  make setup                 Full interactive setup (first time)\n'
	@printf '  make reminder-status       Verify notifications work\n'
	@printf '  make uninstall             Clean removal of all components\n'
	@printf '\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'

# ═══════════════════════════════════════════════════════════════════════════════
#  SETUP STEPS (can be run individually)
# ═══════════════════════════════════════════════════════════════════════════════

## Check if Homebrew is installed, offer to install if not
check-homebrew:
	@printf '\n'
	@printf '\033[1mChecking Homebrew...\033[0m\n'
	@printf '\n'
	@if command -v brew &> /dev/null; then \
		BREW_VERSION=$$(brew --version | head -n1); \
		printf '\033[32mHomebrew is installed\033[0m (%s)\n' "$$BREW_VERSION"; \
	else \
		printf '\033[33mHomebrew is not installed.\033[0m\n'; \
		printf '\n'; \
		printf 'Homebrew is a package manager for macOS needed to install\n'; \
		printf 'dependencies like conda-lock and terminal-notifier.\n'; \
		printf '\n'; \
		printf 'Learn more: https://brew.sh\n'; \
		printf '\n'; \
		read -p "Install Homebrew now? [Y/n]: " REPLY; \
		REPLY=$${REPLY:-Y}; \
		if [[ "$$REPLY" =~ ^[Yy] ]]; then \
			printf '\n'; \
			printf '\033[36mInstalling Homebrew...\033[0m\n'; \
			/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
			mkdir -p $(MARKERS_DIR); \
			touch $(MARKERS_DIR)/homebrew_installed; \
			printf '\n'; \
			printf '\033[32mHomebrew installed successfully\033[0m\n'; \
			printf '\n'; \
			printf '\033[33mNote: You may need to run the following to add Homebrew to your PATH:\033[0m\n'; \
			printf '  eval "$$(/opt/homebrew/bin/brew shellenv)"\n'; \
		else \
			printf '\n'; \
			printf '\033[31mSetup cannot continue without Homebrew.\033[0m\n'; \
			exit 1; \
		fi; \
	fi
	@printf '\n'

## Install dependencies from Brewfile
brew:
	@printf '\n'
	@printf '\033[1mInstalling dependencies from Brewfile...\033[0m\n'
	@printf '\n'
	@mkdir -p $(MARKERS_DIR)
	@while IFS= read -r line || [ -n "$$line" ]; do \
		if echo "$$line" | grep -q '^brew "'; then \
			FORMULA=$$(echo "$$line" | sed 's/brew "\([^"]*\)".*/\1/'); \
			if brew list --formula "$$FORMULA" &> /dev/null; then \
				printf '  \033[32m%s\033[0m (already installed)\n' "$$FORMULA"; \
			else \
				printf '  \033[36mInstalling %s...\033[0m\n' "$$FORMULA"; \
				brew install "$$FORMULA"; \
				echo "$$FORMULA" >> $(MARKERS_DIR)/brews_installed; \
				printf '  \033[32m%s installed\033[0m\n' "$$FORMULA"; \
			fi; \
		fi; \
	done < $(BREWFILE)
	@printf '\n'
	@printf '\033[32mAll dependencies installed\033[0m\n'
	@printf '\n'

## Install pre-commit Git hooks
pre-commit:
	@printf '\n'
	@printf '\033[1mInstalling pre-commit hooks...\033[0m\n'
	@printf '\n'
	@if command -v pre-commit &> /dev/null; then \
		pre-commit install; \
		printf '\n'; \
		printf '\033[32mPre-commit hooks installed\033[0m\n'; \
	else \
		printf '\033[33mpre-commit not found. Install it first with: pip install pre-commit\033[0m\n'; \
	fi
	@printf '\n'

## Create conda environment from lock file
conda:
	@printf '\n'
	@printf '\033[1mCreating conda environment '"'"'%s'"'"'...\033[0m\n' "$(ENV_NAME)"
	@printf '\n'
	@mkdir -p $(MARKERS_DIR)
	@# Detect conda tool (priority: micromamba > mamba > conda)
	@if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		printf '\033[31mError: No conda-compatible tool found.\033[0m\n'; \
		printf 'Install one of: conda, mamba, or micromamba\n'; \
		exit 1; \
	fi; \
	\
	if $$CONDA_CMD env list | grep -q "^$(ENV_NAME) "; then \
		printf '\033[33mEnvironment '"'"'%s'"'"' already exists.\033[0m\n' "$(ENV_NAME)"; \
		read -p "Recreate it? [y/N]: " REPLY; \
		if [[ "$$REPLY" =~ ^[Yy] ]]; then \
			printf '\n'; \
			printf '\033[36mRemoving existing environment...\033[0m\n'; \
			$$CONDA_CMD env remove -n $(ENV_NAME) -y; \
			printf '\033[36mCreating environment from lock file...\033[0m\n'; \
			conda-lock install -n $(ENV_NAME) $(CONDA_LOCK_FILE); \
			touch $(MARKERS_DIR)/conda_created; \
			printf '\n'; \
			printf '\033[32mEnvironment recreated\033[0m\n'; \
		else \
			printf '\n'; \
			printf 'Keeping existing environment.\n'; \
		fi; \
	else \
		printf '\033[36mCreating environment from lock file...\033[0m\n'; \
		conda-lock install -n $(ENV_NAME) $(CONDA_LOCK_FILE); \
		touch $(MARKERS_DIR)/conda_created; \
		printf '\n'; \
		printf '\033[32mEnvironment created\033[0m\n'; \
	fi
	@printf '\n'

## Create activation script and configure shell aliases
activate:
	@printf '\n'
	@printf '\033[1mShell Configuration\033[0m\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'
	@printf 'Activation script: \033[36mscripts/activate.sh\033[0m\n'
	@printf '\n'
	@# Detect shell and conda tool
	@SHELL_NAME=""; \
	SHELL_CONFIG=""; \
	if [ -n "$$ZSH_VERSION" ] || [ "$$SHELL" = "/bin/zsh" ]; then \
		SHELL_NAME="zsh"; \
		SHELL_CONFIG="$$HOME/.zshrc"; \
	elif [ -n "$$BASH_VERSION" ] || [ "$$SHELL" = "/bin/bash" ]; then \
		SHELL_NAME="bash"; \
		SHELL_CONFIG="$$HOME/.bashrc"; \
	else \
		SHELL_NAME="bash"; \
		SHELL_CONFIG="$$HOME/.profile"; \
	fi; \
	\
	if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		printf '\033[31mError: No conda-compatible tool found.\033[0m\n'; \
		exit 1; \
	fi; \
	\
	if [ "$$CONDA_CMD" = "micromamba" ]; then \
		ACTIVATE_CMD="eval \"\$$(micromamba shell hook --shell $$SHELL_NAME)\" && micromamba activate $(ENV_NAME)"; \
	else \
		ACTIVATE_CMD="$$CONDA_CMD activate $(ENV_NAME)"; \
	fi; \
	\
	printf 'Detected shell: \033[36m%s\033[0m\n' "$$SHELL_NAME"; \
	printf 'Config file: \033[36m%s\033[0m\n' "$$SHELL_CONFIG"; \
	printf '\n'; \
	printf 'To activate the environment manually, run:\n'; \
	printf '  \033[36msource %s/scripts/activate.sh\033[0m\n' "$(REPO_ROOT)"; \
	printf '\n'; \
	printf 'For convenience, you can add these aliases to your shell:\n'; \
	printf '  \033[36malias open_assistant='"'"'cd %s && source .env && %s && opencode'"'"'\033[0m\n' "$(REPO_ROOT)" "$$ACTIVATE_CMD"; \
	printf '  \033[36malias oa='"'"'cd %s && source .env && %s && opencode'"'"'\033[0m\n' "$(REPO_ROOT)" "$$ACTIVATE_CMD"; \
	printf '\n'; \
	read -p "Add these aliases to $$SHELL_CONFIG now? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		printf '\n'; \
		if grep -q "alias open_assistant=" "$$SHELL_CONFIG" 2>/dev/null; then \
			printf '\033[33mAliases already exist in %s\033[0m\n' "$$SHELL_CONFIG"; \
		else \
			cp "$$SHELL_CONFIG" "$$SHELL_CONFIG.backup" 2>/dev/null || true; \
			echo "" >> "$$SHELL_CONFIG"; \
			echo "# open_assistant aliases (added by make setup)" >> "$$SHELL_CONFIG"; \
			echo "alias open_assistant='cd $(REPO_ROOT) && source .env && $$ACTIVATE_CMD && opencode'" >> "$$SHELL_CONFIG"; \
			echo "alias oa='cd $(REPO_ROOT) && source .env && $$ACTIVATE_CMD && opencode'" >> "$$SHELL_CONFIG"; \
			mkdir -p $(MARKERS_DIR); \
			echo "$$SHELL_CONFIG" > $(MARKERS_DIR)/alias_added; \
			printf '\033[32mAliases added to %s\033[0m\n' "$$SHELL_CONFIG"; \
			printf '\n'; \
			printf 'Run '"'"'\033[36msource %s\033[0m'"'"' to apply changes.\n' "$$SHELL_CONFIG"; \
		fi; \
	else \
		printf '\n'; \
		printf 'Skipped. You can add the aliases manually later.\n'; \
	fi
	@printf '\n'

## Authenticate with opencode (opens browser)
auth:
	@printf '\n'
	@printf '┌─────────────────────────────────────────────────────────────┐\n'
	@printf '│ \033[1mOpenCode Authentication\033[0m                       │\n'
	@printf '│                                                             │\n'
	@printf '│ opencode needs authentication to access AI features.        │\n'
	@printf '│ This will open a browser for you to log in.                 │\n'
	@printf '└─────────────────────────────────────────────────────────────┘\n'
	@printf '\n'
	@read -p "Run 'opencode auth login' now? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		printf '\n'; \
		printf '\033[36mOpening browser for authentication...\033[0m\n'; \
		opencode auth login; \
	else \
		printf '\n'; \
		printf 'Skipped. Run '"'"'\033[36mopencode auth login\033[0m'"'"' later to authenticate.\n'; \
	fi
	@printf '\n'

## Authenticate with GitHub CLI
gh-login:
	@printf '\n'
	@printf '┌─────────────────────────────────────────────────────────────┐\n'
	@printf '│ \033[1mGitHub CLI Authentication\033[0m                     │\n'
	@printf '│                                                             │\n'
	@printf '│ GitHub CLI (gh) enables Git operations and GitHub API       │\n'
	@printf '│ access from the command line.                               │\n'
	@printf '└─────────────────────────────────────────────────────────────┘\n'
	@printf '\n'
	@read -p "Run 'gh auth login' now? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		printf '\n'; \
		printf '\033[36mStarting GitHub authentication...\033[0m\n'; \
		gh auth login; \
	else \
		printf '\n'; \
		printf 'Skipped. Run '"'"'\033[36mgh auth login\033[0m'"'"' later to authenticate.\n'; \
	fi
	@printf '\n'

# ═══════════════════════════════════════════════════════════════════════════════
#  REMINDER DAEMON
# ═══════════════════════════════════════════════════════════════════════════════

## Install calendar reminder background service
install-reminder-daemon:
	@printf '\n'
	@printf '┌─────────────────────────────────────────────────────────────┐\n'
	@printf '│ \033[1mReminder Daemon\033[0m                               │\n'
	@printf '│                                                             │\n'
	@printf '│ A background service that sends macOS notifications for     │\n'
	@printf '│ calendar events and reminders in this workspace.            │\n'
	@printf '│ Checks every 5 minutes using terminal-notifier.             │\n'
	@printf '└─────────────────────────────────────────────────────────────┘\n'
	@printf '\n'
	@# Detect conda tool (priority: micromamba > mamba > conda)
	@if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		printf '\033[31mError: No conda-compatible tool found.\033[0m\n'; \
		exit 1; \
	fi; \
	\
	CONDA_PYTHON=$$($$CONDA_CMD run -n $(ENV_NAME) which python 2>/dev/null); \
	if [ -z "$$CONDA_PYTHON" ]; then \
		printf '\033[31mError: Conda environment '"'"'%s'"'"' not found.\033[0m\n' "$(ENV_NAME)"; \
		printf 'Run '"'"'make conda'"'"' first to create the environment.\n'; \
		exit 1; \
	fi; \
	printf 'Installing reminder daemon...\n'; \
	printf '  Python: %s\n' "$$CONDA_PYTHON"; \
	printf '  Repo:   %s\n' "$(REPO_ROOT)"; \
	printf '\n'; \
	mkdir -p $(HOME)/Library/LaunchAgents; \
	mkdir -p $(MARKERS_DIR); \
	sed -e "s|{{PYTHON_PATH}}|$$CONDA_PYTHON|g" \
	    -e "s|{{REPO_ROOT}}|$(REPO_ROOT)|g" \
	    $(LAUNCHAGENT_TEMPLATE) > $(LAUNCHAGENT_PLIST); \
	launchctl unload $(LAUNCHAGENT_PLIST) 2>/dev/null || true; \
	launchctl load $(LAUNCHAGENT_PLIST); \
	touch $(MARKERS_DIR)/reminder_installed; \
	printf '\033[32mReminder daemon installed and started\033[0m\n'; \
	printf '\n'; \
	printf 'It will check for reminders every 5 minutes.\n'
	@printf '\n'

## Remove calendar reminder service
uninstall-reminder-daemon:
	@printf '\n'
	@printf '\033[1mUninstalling reminder daemon...\033[0m\n'
	@printf '\n'
	@launchctl unload $(LAUNCHAGENT_PLIST) 2>/dev/null || true
	@rm -f $(LAUNCHAGENT_PLIST)
	@rm -f $(MARKERS_DIR)/reminder_installed 2>/dev/null || true
	@printf '\033[32mReminder daemon uninstalled\033[0m\n'
	@printf '\n'

## Check daemon status and send test notification
reminder-status:
	@printf '\n'
	@printf '\033[1mReminder Daemon Status\033[0m\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'
	@if launchctl list 2>/dev/null | grep -q $(LAUNCHAGENT_LABEL); then \
		printf 'Status: \033[32mRUNNING\033[0m\n'; \
		printf '\n'; \
		launchctl list | grep $(LAUNCHAGENT_LABEL) | awk '{print "  PID: " $$1 "\n  Label: " $$3}'; \
	else \
		printf 'Status: \033[33mNOT RUNNING\033[0m\n'; \
		printf '\n'; \
		printf 'Install with: \033[36mmake install-reminder-daemon\033[0m\n'; \
	fi
	@printf '\n'
	@printf '\033[1mPending reminders:\033[0m\n'
	@# Detect conda tool for running Python script
	@if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		CONDA_CMD=""; \
	fi; \
	if python scripts/calendar_reminder.py status 2>/dev/null; then \
		: ; \
	elif [ -n "$$CONDA_CMD" ] && $$CONDA_CMD run -n $(ENV_NAME) python scripts/calendar_reminder.py status 2>/dev/null; then \
		: ; \
	else \
		printf '  (Could not check - activate conda environment first)\n'; \
	fi
	@printf '\n'
	@printf '\033[1mSending test notification...\033[0m\n'
	@$(MAKE) --no-print-directory reminder-test
	@printf '\n'

## Send a test notification
reminder-test:
	@if command -v terminal-notifier &> /dev/null; then \
		terminal-notifier -title "open_assistant" -message "Test notification successful!" -sound default; \
		printf '\033[32mTest notification sent\033[0m (check your notifications)\n'; \
	else \
		printf '\033[33mterminal-notifier not found. Install with: make brew\033[0m\n'; \
	fi

# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

## Remove conda environment only
clean:
	@printf '\n'
	@printf '\033[1mRemoving conda environment '"'"'%s'"'"'...\033[0m\n' "$(ENV_NAME)"
	@printf '\n'
	@# Detect conda tool (priority: micromamba > mamba > conda)
	@if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		printf '\033[31mError: No conda-compatible tool found.\033[0m\n'; \
		exit 1; \
	fi; \
	\
	if $$CONDA_CMD env list | grep -q "^$(ENV_NAME) "; then \
		$$CONDA_CMD env remove -n $(ENV_NAME) -y; \
		rm -f $(MARKERS_DIR)/conda_created 2>/dev/null || true; \
		printf '\033[32mEnvironment removed\033[0m\n'; \
	else \
		printf 'Environment '"'"'%s'"'"' does not exist.\n' "$(ENV_NAME)"; \
	fi
	@printf '\n'

## Remove everything installed by this setup
uninstall:
	@printf '\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\033[1m  open_assistant Uninstall\033[0m\n'
	@printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'
	@printf '\n'
	@printf 'This will remove the following components:\n'
	@printf '\n'
	@# Detect conda tool for uninstall (priority: micromamba > mamba > conda)
	@if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		CONDA_CMD=""; \
	fi; \
	if [ -n "$$CONDA_CMD" ] && $$CONDA_CMD env list 2>/dev/null | grep -q "^$(ENV_NAME) "; then \
		printf '  \033[32m[x]\033[0m Conda environment '"'"'%s'"'"'\n' "$(ENV_NAME)"; \
	else \
		printf '  [ ] Conda environment '"'"'%s'"'"' (not found)\n' "$(ENV_NAME)"; \
	fi
	@if [ -f "$(LAUNCHAGENT_PLIST)" ] || [ -f "$(MARKERS_DIR)/reminder_installed" ]; then \
		printf '  \033[32m[x]\033[0m Reminder daemon\n'; \
	else \
		printf '  [ ] Reminder daemon (not installed)\n'; \
	fi
	@if [ -f "$(MARKERS_DIR)/alias_added" ]; then \
		SHELL_CONFIG=$$(cat $(MARKERS_DIR)/alias_added); \
		printf '  \033[32m[x]\033[0m Shell aliases from %s\n' "$$SHELL_CONFIG"; \
	else \
		printf '  [ ] Shell aliases (not added by setup)\n'; \
	fi
	@if [ -f "$(MARKERS_DIR)/brews_installed" ]; then \
		BREWS=$$(cat $(MARKERS_DIR)/brews_installed | tr '\n' ', ' | sed 's/,$$//'); \
		printf '  \033[32m[x]\033[0m Homebrew formulas: %s\n' "$$BREWS"; \
	else \
		printf '  [ ] Homebrew formulas (none installed by setup)\n'; \
	fi
	@if [ -f "$(MARKERS_DIR)/homebrew_installed" ]; then \
		printf '  \033[32m[x]\033[0m Homebrew (installed by setup)\n'; \
	else \
		printf '  [ ] Homebrew (not installed by setup)\n'; \
	fi
	@printf '\n'
	@printf '\033[33mNote: Only components installed by '"'"'make setup'"'"' will be removed.\033[0m\n'
	@printf '\n'
	@read -p "Continue with uninstall? [y/N]: " REPLY; \
	if [[ ! "$$REPLY" =~ ^[Yy] ]]; then \
		printf '\n'; \
		printf 'Uninstall cancelled.\n'; \
		exit 0; \
	fi; \
	printf '\n'; \
	\
	printf '\033[36mStopping reminder daemon...\033[0m\n'; \
	launchctl unload $(LAUNCHAGENT_PLIST) 2>/dev/null || true; \
	rm -f $(LAUNCHAGENT_PLIST); \
	rm -f $(MARKERS_DIR)/reminder_installed 2>/dev/null || true; \
	printf '\033[32mReminder daemon removed\033[0m\n'; \
	printf '\n'; \
	\
	if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		CONDA_CMD=""; \
	fi; \
	if [ -n "$$CONDA_CMD" ] && $$CONDA_CMD env list 2>/dev/null | grep -q "^$(ENV_NAME) "; then \
		printf '\033[36mRemoving conda environment...\033[0m\n'; \
		$$CONDA_CMD env remove -n $(ENV_NAME) -y; \
		rm -f $(MARKERS_DIR)/conda_created 2>/dev/null || true; \
		printf '\033[32mConda environment removed\033[0m\n'; \
		printf '\n'; \
	fi; \
	\
	if [ -f "$(MARKERS_DIR)/alias_added" ]; then \
		SHELL_CONFIG=$$(cat $(MARKERS_DIR)/alias_added); \
		printf '\033[36mRemoving shell aliases from %s...\033[0m\n' "$$SHELL_CONFIG"; \
		if [ -f "$$SHELL_CONFIG" ]; then \
			grep -v "# open_assistant aliases" "$$SHELL_CONFIG" | \
			grep -v "alias open_assistant=" | \
			grep -v "alias oa='cd $(REPO_ROOT)" > "$$SHELL_CONFIG.tmp"; \
			mv "$$SHELL_CONFIG.tmp" "$$SHELL_CONFIG"; \
			printf '\033[32mAliases removed\033[0m\n'; \
		fi; \
		rm -f $(MARKERS_DIR)/alias_added; \
		printf '\n'; \
	fi; \
	\
	if [ -f "$(MARKERS_DIR)/brews_installed" ]; then \
		printf '\033[36mUninstalling Homebrew formulas...\033[0m\n'; \
		while IFS= read -r formula || [ -n "$$formula" ]; do \
			if [ -n "$$formula" ] && brew list --formula "$$formula" &> /dev/null; then \
				brew uninstall "$$formula" 2>/dev/null || true; \
				printf '\033[32m%s uninstalled\033[0m\n' "$$formula"; \
			fi; \
		done < $(MARKERS_DIR)/brews_installed; \
		rm -f $(MARKERS_DIR)/brews_installed; \
		printf '\n'; \
	fi; \
	\
	if [ -f "$(MARKERS_DIR)/homebrew_installed" ]; then \
		BREW_FORMULAS=$$(brew list --formula 2>/dev/null | wc -l | tr -d ' '); \
		if [ "$$BREW_FORMULAS" = "0" ]; then \
			printf '\033[33mHomebrew was installed by this setup and has no other formulas.\033[0m\n'; \
			read -p "Remove Homebrew entirely? [y/N]: " BREW_REPLY; \
			if [[ "$$BREW_REPLY" =~ ^[Yy] ]]; then \
				printf '\033[36mUninstalling Homebrew...\033[0m\n'; \
				/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"; \
				rm -f $(MARKERS_DIR)/homebrew_installed; \
				printf '\033[32mHomebrew removed\033[0m\n'; \
			else \
				printf 'Keeping Homebrew.\n'; \
				rm -f $(MARKERS_DIR)/homebrew_installed; \
			fi; \
		else \
			printf 'Homebrew has other formulas installed (%s). Keeping Homebrew.\n' "$$BREW_FORMULAS"; \
			rm -f $(MARKERS_DIR)/homebrew_installed; \
		fi; \
		printf '\n'; \
	fi; \
	\
	rmdir $(MARKERS_DIR) 2>/dev/null || true; \
	\
	printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'; \
	printf '\033[32m\033[1m  Uninstall complete\033[0m\n'; \
	printf '\033[1m═══════════════════════════════════════════════════════════════\033[0m\n'; \
	printf '\n'

# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL TARGETS (used by setup)
# ═══════════════════════════════════════════════════════════════════════════════

_step_homebrew:
	@printf '\033[1mStep 1/6: Checking Homebrew...\033[0m\n'
	@if command -v brew &> /dev/null; then \
		BREW_VERSION=$$(brew --version | head -n1); \
		printf '  \033[32mHomebrew is installed\033[0m (%s)\n' "$$BREW_VERSION"; \
	else \
		printf '  \033[33mHomebrew is not installed.\033[0m\n'; \
		printf '\n'; \
		printf '  Homebrew is a package manager for macOS needed to install\n'; \
		printf '  dependencies like conda-lock and terminal-notifier.\n'; \
		printf '\n'; \
		printf '  Learn more: https://brew.sh\n'; \
		printf '\n'; \
		read -p "  Install Homebrew now? [Y/n]: " REPLY; \
		REPLY=$${REPLY:-Y}; \
		if [[ "$$REPLY" =~ ^[Yy] ]]; then \
			printf '\n'; \
			printf '  \033[36mInstalling Homebrew...\033[0m\n'; \
			/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
			touch $(MARKERS_DIR)/homebrew_installed; \
			printf '\n'; \
			printf '  \033[32mHomebrew installed\033[0m\n'; \
			printf '\n'; \
			printf '  \033[33mNote: You may need to restart your terminal or run:\033[0m\n'; \
			printf '    eval "$$(/opt/homebrew/bin/brew shellenv)"\n'; \
			printf '\n'; \
			read -p "  Press Enter to continue..."; \
		else \
			printf '\n'; \
			printf '  \033[31mSetup cannot continue without Homebrew.\033[0m\n'; \
			exit 1; \
		fi; \
	fi
	@printf '\n'

_step_brew:
	@printf '\033[1mStep 2/6: Installing dependencies from Brewfile...\033[0m\n'
	@printf '\n'
	@# Detect existing conda tool (priority: micromamba > mamba > conda)
	@CONDA_DETECTED=""; \
	if command -v micromamba &> /dev/null; then \
		CONDA_DETECTED="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_DETECTED="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_DETECTED="conda"; \
	fi; \
	\
	if [ -n "$$CONDA_DETECTED" ]; then \
		printf '  \033[32mDetected: %s\033[0m - skipping micromamba installation\n' "$$CONDA_DETECTED"; \
		printf '\n'; \
	else \
		printf '  \033[33mNo conda-compatible tool detected.\033[0m\n'; \
		printf '\n'; \
		printf '  ┌─────────────────────────────────────────────────────────────┐\n'; \
		printf '  │ \033[1mConda Environment Manager Required\033[0m            │\n'; \
		printf '  │                                                             │\n'; \
		printf '  │ A conda-compatible tool (conda, mamba, or micromamba) is    │\n'; \
		printf '  │ required to manage Python environments for this project.    │\n'; \
		printf '  │                                                             │\n'; \
		printf '  │ micromamba is a fast, lightweight option that can be        │\n'; \
		printf '  │ installed via Homebrew.                                     │\n'; \
		printf '  └─────────────────────────────────────────────────────────────┘\n'; \
		printf '\n'; \
		read -p "  Install micromamba now? [Y/n]: " REPLY; \
		REPLY=$${REPLY:-Y}; \
		if [[ ! "$$REPLY" =~ ^[Yy] ]]; then \
			printf '\n'; \
			printf '  \033[31mSetup cannot continue without a conda-compatible tool.\033[0m\n'; \
			printf '  You can install one manually:\n'; \
			printf '    - micromamba: \033[36mbrew install micromamba\033[0m\n'; \
			printf '    - miniforge:  \033[36mhttps://github.com/conda-forge/miniforge\033[0m\n'; \
			printf '    - miniconda:  \033[36mhttps://docs.conda.io/en/latest/miniconda.html\033[0m\n'; \
			printf '\n'; \
			exit 1; \
		fi; \
		printf '\n'; \
	fi; \
	\
	while IFS= read -r line || [ -n "$$line" ]; do \
		if echo "$$line" | grep -q '^brew "'; then \
			FORMULA=$$(echo "$$line" | sed 's/brew "\([^"]*\)".*/\1/'); \
			if [ "$$FORMULA" = "micromamba" ] && [ -n "$$CONDA_DETECTED" ]; then \
				printf '  \033[90m%s\033[0m (skipped - using %s)\n' "$$FORMULA" "$$CONDA_DETECTED"; \
			elif brew list --formula "$$FORMULA" &> /dev/null; then \
				printf '  \033[32m%s\033[0m (already installed)\n' "$$FORMULA"; \
			else \
				printf '  \033[36mInstalling %s...\033[0m\n' "$$FORMULA"; \
				brew install "$$FORMULA"; \
				echo "$$FORMULA" >> $(MARKERS_DIR)/brews_installed; \
				printf '  \033[32m%s installed\033[0m\n' "$$FORMULA"; \
			fi; \
		fi; \
	done < $(BREWFILE)
	@printf '\n'
	@printf '  \033[32mAll dependencies installed\033[0m\n'
	@printf '\n'

_step_precommit:
	@printf '\033[1mStep 3/6: Installing pre-commit hooks...\033[0m\n'
	@if command -v pre-commit &> /dev/null; then \
		pre-commit install > /dev/null 2>&1; \
		printf '  \033[32mPre-commit hooks installed\033[0m\n'; \
	else \
		printf '  \033[33mpre-commit not found, skipping\033[0m\n'; \
	fi
	@printf '\n'

_step_conda:
	@printf '\033[1mStep 4/6: Creating conda environment '"'"'%s'"'"'...\033[0m\n' "$(ENV_NAME)"
	@printf '\n'
	@# Detect conda tool (priority: micromamba > mamba > conda)
	@if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		printf '  \033[31mError: No conda-compatible tool found.\033[0m\n'; \
		printf '  Run the brew step first or install conda/mamba/micromamba manually.\n'; \
		exit 1; \
	fi; \
	printf '  Using: \033[36m%s\033[0m for environment management\n' "$$CONDA_CMD"; \
	printf '\n'; \
	\
	if $$CONDA_CMD env list | grep -q "^$(ENV_NAME) "; then \
		printf '  \033[33mEnvironment '"'"'%s'"'"' already exists.\033[0m\n' "$(ENV_NAME)"; \
		read -p "  Recreate it? [y/N]: " REPLY; \
		if [[ "$$REPLY" =~ ^[Yy] ]]; then \
			printf '  \033[36mRemoving existing environment...\033[0m\n'; \
			$$CONDA_CMD env remove -n $(ENV_NAME) -y > /dev/null 2>&1; \
			printf '  \033[36mCreating environment from lock file...\033[0m\n'; \
			conda-lock install -n $(ENV_NAME) $(CONDA_LOCK_FILE); \
			touch $(MARKERS_DIR)/conda_created; \
			printf '  \033[32mEnvironment recreated\033[0m\n'; \
		else \
			printf '  Keeping existing environment.\n'; \
		fi; \
	else \
		printf '  \033[36mCreating environment from lock file...\033[0m\n'; \
		conda-lock install -n $(ENV_NAME) $(CONDA_LOCK_FILE); \
		touch $(MARKERS_DIR)/conda_created; \
		printf '  \033[32mEnvironment created\033[0m\n'; \
	fi
	@printf '\n'

_step_activate:
	@printf '\033[1mStep 5/6: Shell configuration...\033[0m\n'
	@printf '  Created: scripts/activate.sh\n'
	@# Detect shell and conda tool
	@SHELL_NAME=""; \
	SHELL_CONFIG=""; \
	if [ -n "$$ZSH_VERSION" ] || [ "$$SHELL" = "/bin/zsh" ]; then \
		SHELL_NAME="zsh"; \
		SHELL_CONFIG="$$HOME/.zshrc"; \
	elif [ -n "$$BASH_VERSION" ] || [ "$$SHELL" = "/bin/bash" ]; then \
		SHELL_NAME="bash"; \
		SHELL_CONFIG="$$HOME/.bashrc"; \
	else \
		SHELL_NAME="bash"; \
		SHELL_CONFIG="$$HOME/.profile"; \
	fi; \
	\
	if command -v micromamba &> /dev/null; then \
		CONDA_CMD="micromamba"; \
	elif command -v mamba &> /dev/null; then \
		CONDA_CMD="mamba"; \
	elif command -v conda &> /dev/null; then \
		CONDA_CMD="conda"; \
	else \
		printf '  \033[31mError: No conda-compatible tool found.\033[0m\n'; \
		exit 1; \
	fi; \
	\
	printf '  Detected shell: %s\n' "$$SHELL_NAME"; \
	printf '  Detected conda tool: %s\n' "$$CONDA_CMD"; \
	printf '\n'; \
	printf '  To activate manually:\n'; \
	printf '    \033[36msource %s/scripts/activate.sh\033[0m\n' "$(REPO_ROOT)"; \
	printf '\n'; \
	\
	if [ "$$CONDA_CMD" = "micromamba" ]; then \
		ACTIVATE_CMD="eval \"\$$(micromamba shell hook --shell $$SHELL_NAME)\" && micromamba activate $(ENV_NAME)"; \
	else \
		ACTIVATE_CMD="$$CONDA_CMD activate $(ENV_NAME)"; \
	fi; \
	\
	read -p "  Add aliases to $$SHELL_CONFIG? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		if grep -q "alias open_assistant=" "$$SHELL_CONFIG" 2>/dev/null; then \
			printf '  \033[33mAliases already exist in %s\033[0m\n' "$$SHELL_CONFIG"; \
			printf '  To update them, remove the existing aliases first and re-run setup.\n'; \
		else \
			cp "$$SHELL_CONFIG" "$$SHELL_CONFIG.backup" 2>/dev/null || true; \
			echo "" >> "$$SHELL_CONFIG"; \
			echo "# open_assistant aliases (added by make setup)" >> "$$SHELL_CONFIG"; \
			echo "alias open_assistant='cd $(REPO_ROOT) && source .env && $$ACTIVATE_CMD && opencode'" >> "$$SHELL_CONFIG"; \
			echo "alias oa='cd $(REPO_ROOT) && source .env && $$ACTIVATE_CMD && opencode'" >> "$$SHELL_CONFIG"; \
			echo "$$SHELL_CONFIG" > $(MARKERS_DIR)/alias_added; \
			printf '\n'; \
			printf '  \033[32mAliases added:\033[0m\n'; \
			printf '    - \033[36mopen_assistant\033[0m  (cd + activate + opencode)\n'; \
			printf '    - \033[36moa\033[0m              (short version)\n'; \
			printf '\n'; \
			printf '  Run '"'"'\033[36msource %s\033[0m'"'"' or restart terminal to use them.\n' "$$SHELL_CONFIG"; \
		fi; \
	else \
		printf '  Skipped.\n'; \
	fi
	@printf '\n'

_step_optional:
	@printf '\033[1mStep 6/6: Optional components...\033[0m\n'
	@printf '\n'
	@printf '  ┌─────────────────────────────────────────────────────────────┐\n'
	@printf '  │ \033[1mReminder Daemon\033[0m                               │\n'
	@printf '  │                                                             │\n'
	@printf '  │ A background service that sends macOS notifications for     │\n'
	@printf '  │ calendar events and reminders in this workspace.            │\n'
	@printf '  │ Checks every 5 minutes using terminal-notifier.             │\n'
	@printf '  └─────────────────────────────────────────────────────────────┘\n'
	@printf '\n'
	@read -p "  Install reminder daemon? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		if command -v micromamba &> /dev/null; then \
			CONDA_CMD="micromamba"; \
		elif command -v mamba &> /dev/null; then \
			CONDA_CMD="mamba"; \
		elif command -v conda &> /dev/null; then \
			CONDA_CMD="conda"; \
		else \
			printf '  \033[31mNo conda-compatible tool found. Skipping.\033[0m\n'; \
			CONDA_CMD=""; \
		fi; \
		if [ -n "$$CONDA_CMD" ]; then \
			CONDA_PYTHON=$$($$CONDA_CMD run -n $(ENV_NAME) which python 2>/dev/null); \
			if [ -z "$$CONDA_PYTHON" ]; then \
				printf '  \033[33mCould not find Python in conda environment. Skipping.\033[0m\n'; \
			else \
				mkdir -p $(HOME)/Library/LaunchAgents; \
				sed -e "s|{{PYTHON_PATH}}|$$CONDA_PYTHON|g" \
				    -e "s|{{REPO_ROOT}}|$(REPO_ROOT)|g" \
				    $(LAUNCHAGENT_TEMPLATE) > $(LAUNCHAGENT_PLIST); \
				launchctl unload $(LAUNCHAGENT_PLIST) 2>/dev/null || true; \
				launchctl load $(LAUNCHAGENT_PLIST); \
				touch $(MARKERS_DIR)/reminder_installed; \
				printf '  \033[32mReminder daemon installed\033[0m\n'; \
			fi; \
		fi; \
	else \
		printf '  Skipped. Install later with: \033[36mmake install-reminder-daemon\033[0m\n'; \
	fi
	@printf '\n'
	@printf '  ┌─────────────────────────────────────────────────────────────┐\n'
	@printf '  │ \033[1mGitHub CLI Authentication\033[0m                     │\n'
	@printf '  │                                                             │\n'
	@printf '  │ GitHub CLI (gh) enables Git operations and GitHub API       │\n'
	@printf '  │ access from the command line.                               │\n'
	@printf '  └─────────────────────────────────────────────────────────────┘\n'
	@printf '\n'
	@read -p "  Run 'gh auth login' now? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		printf '\n'; \
		printf '  \033[36mStarting GitHub authentication...\033[0m\n'; \
		gh auth login; \
	else \
		printf '  Skipped. Run later: \033[36mgh auth login\033[0m\n'; \
	fi
	@printf '\n'
	@printf '  ┌─────────────────────────────────────────────────────────────┐\n'
	@printf '  │ \033[1mOpenCode Authentication\033[0m                       │\n'
	@printf '  │                                                             │\n'
	@printf '  │ opencode needs authentication to access AI features.        │\n'
	@printf '  │ This will open a browser for you to log in.                 │\n'
	@printf '  └─────────────────────────────────────────────────────────────┘\n'
	@printf '\n'
	@read -p "  Run 'opencode auth login' now? [Y/n]: " REPLY; \
	REPLY=$${REPLY:-Y}; \
	if [[ "$$REPLY" =~ ^[Yy] ]]; then \
		printf '\n'; \
		printf '  \033[36mOpening browser for authentication...\033[0m\n'; \
		opencode auth login; \
	else \
		printf '  Skipped. Run later: \033[36mopencode auth login\033[0m\n'; \
	fi
