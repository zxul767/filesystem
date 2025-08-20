##
# Filesystem
#
# @file
# @version 0.1

# ANSI color codes
RED=\033[1;31m
GREEN=\033[1;32m
YELLOW=\033[1;33m
BLUE=\033[1;34m
CYAN=\033[1;36m
RESET=\033[0m

all: compile check

check:
	@echo "$(YELLOW)==> Running tests with pytest$(RESET)"
	@python -m pytest tests

check_session:
	@echo "$(CYAN)==> Watching for file changes...$(RESET)"

compile: lint typecheck

lint:
	@echo "$(YELLOW)==> Running linter and formatter$(RESET)"
	@ruff format filesystem
	@ruff check --fix filesystem

typecheck:
	@echo "$(YELLOW)==> Running type checker (mypy)$(RESET)"
	@mypy filesystem

typecheck_session:
	@find filesystem tests -type f | entr -r make typecheck

# end
