.PHONY: help deploy deploy-dev deploy-prod run test clean install auth status logs start stop sync validate

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
SCRIPTS_DIR := scripts
APP_NAME_DEV := fashion-rec-app-dev
APP_NAME_PROD := fashion-rec-app-prod
WORKSPACE_PATH_DEV := /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
WORKSPACE_PATH_PROD := /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-prod

##@ Help

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install Python dependencies locally
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

run: ## Run the app locally for development
	@echo "🚀 Starting local development server..."
	@chmod +x $(SCRIPTS_DIR)/run.sh
	@./$(SCRIPTS_DIR)/run.sh

test: ## Run deployment tests
	@echo "🧪 Running tests..."
	@$(PYTHON) $(SCRIPTS_DIR)/test_deployment.py

clean: ## Clean up temporary files and caches
	@echo "🧹 Cleaning up..."
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf *.egg-info
	@rm -rf build dist
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

##@ Deployment

deploy: deploy-dev ## Deploy to dev environment (default)

deploy-dev: ## Deploy to dev environment
	@echo "🚀 Deploying to dev environment..."
	@chmod +x $(SCRIPTS_DIR)/deploy.sh
	@./$(SCRIPTS_DIR)/deploy.sh dev

deploy-prod: ## Deploy to production environment
	@echo "🚀 Deploying to production environment..."
	@chmod +x $(SCRIPTS_DIR)/deploy.sh
	@./$(SCRIPTS_DIR)/deploy.sh prod

##@ Databricks CLI

auth: ## Authenticate with Databricks
	@echo "🔐 Authenticating with Databricks..."
	@databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com/

auth-status: ## Check authentication status
	@echo "🔍 Checking authentication status..."
	@databricks auth profiles

##@ App Management (Dev)

status: ## Check dev app status
	@echo "📊 Checking dev app status..."
	@databricks apps get $(APP_NAME_DEV)

status-prod: ## Check prod app status
	@echo "📊 Checking prod app status..."
	@databricks apps get $(APP_NAME_PROD)

logs: ## View dev app logs (check in Databricks UI)
	@echo "📜 App Logs:"
	@echo "View logs in Databricks UI:"
	@echo "  → Apps → $(APP_NAME_DEV) → Logs"
	@echo ""
	@echo "Or access the app directly:"
	@echo "  https://fashion-rec-app-dev-1444828305810485.aws.databricksapps.com"

logs-prod: ## View prod app logs (check in Databricks UI)
	@echo "📜 App Logs:"
	@echo "View logs in Databricks UI:"
	@echo "  → Apps → $(APP_NAME_PROD) → Logs"
	@echo ""
	@echo "Or access the app directly:"
	@echo "  https://fashion-rec-app-prod-1444828305810485.aws.databricksapps.com"

start: ## Start dev app
	@echo "▶️  Starting dev app..."
	@databricks apps start $(APP_NAME_DEV)
	@echo "✅ Dev app started"

start-prod: ## Start prod app
	@echo "▶️  Starting prod app..."
	@databricks apps start $(APP_NAME_PROD)
	@echo "✅ Prod app started"

stop: ## Stop dev app
	@echo "⏸️  Stopping dev app..."
	@databricks apps stop $(APP_NAME_DEV)
	@echo "✅ Dev app stopped"

stop-prod: ## Stop prod app
	@echo "⏸️  Stopping prod app..."
	@databricks apps stop $(APP_NAME_PROD)
	@echo "✅ Prod app stopped"

delete: ## Delete dev app (careful!)
	@echo "🗑️  Deleting dev app..."
	@read -p "Are you sure you want to delete $(APP_NAME_DEV)? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		databricks apps delete $(APP_NAME_DEV); \
		echo "✅ Dev app deleted"; \
	else \
		echo "❌ Deletion cancelled"; \
	fi

delete-prod: ## Delete prod app (careful!)
	@echo "🗑️  Deleting prod app..."
	@read -p "Are you sure you want to delete $(APP_NAME_PROD)? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		databricks apps delete $(APP_NAME_PROD); \
		echo "✅ Prod app deleted"; \
	else \
		echo "❌ Deletion cancelled"; \
	fi

list: ## List all apps in workspace
	@echo "📋 Listing all apps..."
	@databricks apps list | grep -E "(Name|fashion)" || databricks apps list

##@ Sync Operations

sync: ## One-time sync to dev workspace
	@echo "🔄 Syncing to dev workspace..."
	@databricks sync . $(WORKSPACE_PATH_DEV)
	@echo "✅ Sync complete"

sync-watch: ## Continuous sync to dev workspace (watch mode)
	@echo "👀 Starting continuous sync to dev workspace..."
	@echo "Press Ctrl+C to stop"
	@databricks sync --watch . $(WORKSPACE_PATH_DEV)

sync-prod: ## One-time sync to prod workspace
	@echo "🔄 Syncing to prod workspace..."
	@databricks sync . $(WORKSPACE_PATH_PROD)
	@echo "✅ Sync complete"

sync-watch-prod: ## Continuous sync to prod workspace (watch mode)
	@echo "👀 Starting continuous sync to prod workspace..."
	@echo "Press Ctrl+C to stop"
	@databricks sync --watch . $(WORKSPACE_PATH_PROD)

##@ Validation

validate: ## Validate configuration files
	@echo "✅ Validating configuration..."
	@if [ ! -f "app.yaml" ]; then echo "❌ app.yaml not found"; exit 1; fi
	@if [ ! -f "requirements.txt" ]; then echo "❌ requirements.txt not found"; exit 1; fi
	@if [ ! -f "app.py" ]; then echo "❌ app.py not found"; exit 1; fi
	@echo "✅ All required files present"

validate-bundle: ## Validate Databricks bundle
	@echo "✅ Validating bundle..."
	@databricks bundle validate

##@ Quick Actions

quick-deploy: sync deploy ## Quick deploy: sync + deploy to dev
	@echo "✅ Quick deploy complete"

redeploy: ## Redeploy dev app (sync + deploy)
	@echo "🔄 Redeploying dev app..."
	@$(MAKE) sync
	@databricks apps deploy $(APP_NAME_DEV) --source-code-path $(WORKSPACE_PATH_DEV)
	@echo "✅ Redeploy complete"

redeploy-prod: ## Redeploy prod app (sync + deploy)
	@echo "🔄 Redeploying prod app..."
	@$(MAKE) sync-prod
	@databricks apps deploy $(APP_NAME_PROD) --source-code-path $(WORKSPACE_PATH_PROD)
	@echo "✅ Prod redeploy complete"

restart: stop start ## Restart dev app
	@echo "✅ Dev app restarted"

restart-prod: stop-prod start-prod ## Restart prod app
	@echo "✅ Prod app restarted"

##@ Information

info: ## Show app URLs and configuration
	@echo "📊 Fashion Recommendations Dashboard"
	@echo "======================================"
	@echo ""
	@echo "Development:"
	@echo "  App Name: $(APP_NAME_DEV)"
	@echo "  Workspace Path: $(WORKSPACE_PATH_DEV)"
	@echo "  URL: https://fashion-rec-app-dev-1444828305810485.aws.databricksapps.com"
	@echo ""
	@echo "Production:"
	@echo "  App Name: $(APP_NAME_PROD)"
	@echo "  Workspace Path: $(WORKSPACE_PATH_PROD)"
	@echo "  URL: https://fashion-rec-app-prod-1444828305810485.aws.databricksapps.com"
	@echo ""
	@echo "Run 'make help' for available commands"

version: ## Show CLI and app versions
	@echo "🔍 Version Information"
	@echo "======================"
	@echo -n "Databricks CLI: "
	@databricks --version
	@echo -n "Python: "
	@$(PYTHON) --version
	@echo -n "Make: "
	@make --version | head -n 1

##@ Combined Workflows

first-deploy: install auth deploy ## First time setup and deployment
	@echo "✅ First deployment complete!"

full-deploy-dev: clean sync deploy status ## Full dev deployment with status check
	@echo "✅ Full dev deployment complete!"

full-deploy-prod: clean sync-prod deploy-prod status-prod ## Full prod deployment with status check
	@echo "✅ Full prod deployment complete!"

promote: ## Promote from dev to prod (deploy to prod)
	@echo "🚀 Promoting to production..."
	@read -p "Have you tested in dev? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(MAKE) deploy-prod; \
	else \
		echo "❌ Promotion cancelled. Please test in dev first."; \
	fi

