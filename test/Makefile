# Labrynth Test Project Makefile

# Path to labrynth framework source (use quotes in commands for spaces)
LABRYNTH_SRC = "/Users/amaannawab/research/temp prefect/labrynth-framework"
LABRYNTH_UI = "/Users/amaannawab/research/temp prefect/labrynth-framework/ui"
LABRYNTH_SERVER_UI = "/Users/amaannawab/research/temp prefect/labrynth-framework/src/labrynth/server/ui"

# Default target
.PHONY: help
help:
	@echo "Labrynth Test Project Commands:"
	@echo ""
	@echo "  make install      - Install/reinstall labrynth from source"
	@echo "  make build-ui     - Build UI and copy to server"
	@echo "  make deploy       - Deploy agents to database"
	@echo "  make fresh-deploy - Clean db + deploy (removes stale agents)"
	@echo "  make server       - Start the labrynth server"
	@echo "  make dev          - Clean + install + build-ui + deploy + server"
	@echo "  make dev-server   - Start server with auto-deploy (no reinstall)"
	@echo "  make refresh      - Install + build-ui + start with auto-deploy"
	@echo "  make clean        - Remove labrynth database (~/.labrynth/labrynth.db)"
	@echo ""

# Install labrynth from local source
.PHONY: install
install:
	@echo "Installing labrynth from source..."
	pip install -e $(LABRYNTH_SRC)
	@echo "Done!"

# Build UI and copy to server directory
.PHONY: build-ui
build-ui:
	@echo "Building UI..."
	cd $(LABRYNTH_UI) && npm run build
	@echo "Copying UI to server..."
	rm -rf $(LABRYNTH_SERVER_UI)
	cp -r $(LABRYNTH_UI)/dist $(LABRYNTH_SERVER_UI)
	@echo "Done!"

# Deploy agents
.PHONY: deploy
deploy:
	@echo "Deploying agents..."
	labrynth deploy
	@echo "Done!"

# Clean database and deploy (removes stale agents from other projects)
.PHONY: fresh-deploy
fresh-deploy: clean deploy

# Start server
.PHONY: server
server:
	@echo "Starting labrynth server..."
	labrynth server start

# Full development refresh: clean db + reinstall + build-ui + deploy + server
.PHONY: dev
dev: clean install build-ui deploy server

# Start server with auto-deploy (uses LABRYNTH_DEV_PROJECT)
.PHONY: dev-server
dev-server:
	@echo "Starting server with auto-deploy..."
	LABRYNTH_DEV_PROJECT="$(CURDIR)" labrynth server start

# Clean up database (removes the global labrynth database)
.PHONY: clean
clean:
	@echo "Removing labrynth database..."
	rm -f ~/.labrynth/labrynth.db
	@echo "Done!"

# Reinstall + build UI + start with auto-deploy (recommended for development)
.PHONY: refresh
refresh: install build-ui dev-server
