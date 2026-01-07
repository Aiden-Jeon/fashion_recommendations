.PHONY: help update-requirements update-environments clean \
        update-notebooks-dev update-notebooks-prod \
        validate sync deploy-dev deploy-prod deploy \
        run-workflow setup-synced-tables

# Default target
help:
	@echo "Fashion Recommendations DataOps - Development Commands"
	@echo ""
	@echo "Environment Management:"
	@echo "  make update-requirements    - Export Poetry dependencies to requirements.txt"
	@echo "  make update-environments    - Update Databricks environment YAML files from Poetry"
	@echo ""
	@echo "Notebook Environment Setup:"
	@echo "  make update-notebooks-dev   - Update notebook metadata for dev deployment"
	@echo "  make update-notebooks-prod  - Update notebook metadata for prod deployment"
	@echo ""
	@echo "Bundle Commands (RECOMMENDED):"
	@echo "  make deploy-dev             - Deploy to dev (auto-updates notebooks)"
	@echo "  make deploy-prod            - Deploy to prod (auto-updates notebooks)"
	@echo "  make deploy                 - Alias for deploy-dev"
	@echo "  make validate               - Validate Databricks bundle configuration"
	@echo "  make sync                   - Sync bundle to Databricks workspace (dev)"
	@echo ""
	@echo "⚠️  IMPORTANT: Always use 'make deploy-*' commands to ensure notebooks are updated!"
	@echo ""
	@echo "Workflow Commands:"
	@echo "  make run-workflow           - Run data loading workflow (dev)"
	@echo ""
	@echo "Synced Tables (SQL-based):"
	@echo "  make setup-synced-tables    - Create/update synced tables using SQL"
	@echo "  make setup-synced-tables-dev- Create synced tables for dev environment"
	@echo "  make setup-synced-tables-prod-Create synced tables for prod environment"
	@echo ""
	@echo "Development:"
	@echo "  make install                - Install dependencies with Poetry"
	@echo "  make clean                  - Clean temporary files"

# Install dependencies
install:
	poetry install

# Update requirements.txt from Poetry
update-requirements:
	@echo "Exporting core requirements..."
	poetry export -f requirements.txt --without-hashes -o requirements.txt
	@echo "✓ Requirements file updated"

# Update Databricks environment YAML files
update-environments: update-requirements
	@echo "Updating base-core.yml..."
	@poetry export -f requirements.txt --without-hashes | \
		awk 'BEGIN {print "  - pip:"} {print "      - " $$0}' > /tmp/deps-core.txt
	@sed -i.bak '/- pip:/,$$d' environments/base-core.yml
	@cat /tmp/deps-core.txt >> environments/base-core.yml
	@rm -f /tmp/deps-*.txt environments/*.bak
	@echo "✓ Environment YAML files updated"

# Validate bundle configuration
validate:
	databricks bundle validate

# Sync bundle to workspace (useful for development)
sync:
	@echo "Syncing bundle to Databricks workspace (dev)..."
	databricks bundle sync -t dev
	@echo "✓ Bundle synced to dev environment"

# Update notebook environment metadata for each target
update-notebooks-dev:
	@echo "Updating notebook metadata for dev environment..."
	python3 scripts/update_notebook_environments.py --target dev
	@echo "✓ Notebooks updated for dev"

update-notebooks-prod:
	@echo "Updating notebook metadata for prod environment..."
	python3 scripts/update_notebook_environments.py --target prod
	@echo "✓ Notebooks updated for prod"

# Full deployment workflow: update notebooks + deploy bundle
deploy-dev: update-notebooks-dev
	@echo "Deploying bundle to dev..."
	databricks bundle deploy -t dev
	@echo "✓ Deployed to dev environment"

deploy-prod: update-notebooks-prod
	@echo "Deploying bundle to prod..."
	databricks bundle deploy -t prod
	@echo "✓ Deployed to prod environment"

# Alias for deploy-dev
deploy: deploy-dev

# Run data loading workflow (bronze tables only)
run-workflow:
	@echo "Running data loading workflow on dev..."
	databricks bundle run data_pipeline_job -t dev
	@echo "✓ Data loading workflow completed"


# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -f /tmp/deps-*.txt environments/*.bak
	@echo "✓ Cleaned temporary files"

