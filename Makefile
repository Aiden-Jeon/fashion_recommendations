.PHONY: help update-requirements update-environments deploy-environments clean \
        update-notebooks-dev update-notebooks-staging update-notebooks-prod \
        deploy-dev deploy-staging deploy-prod test

# Default target
help:
	@echo "Fashion Recommendations MLOps - Development Commands"
	@echo ""
	@echo "Environment Management:"
	@echo "  make update-requirements    - Export Poetry dependencies to requirements.txt files"
	@echo "  make update-environments    - Update Databricks environment YAML files from Poetry"
	@echo "  make deploy-environments    - Deploy environment files to Databricks workspace"
	@echo ""
	@echo "Notebook Environment Setup:"
	@echo "  make update-notebooks-dev   - Update notebook metadata for dev deployment"
	@echo "  make update-notebooks-staging - Update notebook metadata for staging deployment"
	@echo "  make update-notebooks-prod  - Update notebook metadata for prod deployment"
	@echo ""
	@echo "Bundle Commands:"
	@echo "  make validate               - Validate Databricks bundle configuration"
	@echo "  make deploy-dev             - Update notebooks + deploy to dev (recommended)"
	@echo "  make deploy-staging         - Update notebooks + deploy to staging (recommended)"
	@echo "  make deploy-prod            - Update notebooks + deploy to prod (recommended)"
	@echo "  make deploy                 - Alias for deploy-dev"
	@echo ""
	@echo "Development:"
	@echo "  make install                - Install dependencies with Poetry"
	@echo "  make install-all            - Install all dependencies (including viz, dl, dev)"
	@echo "  make test                   - Run tests with pytest"
	@echo "  make clean                  - Clean temporary files"

# Install dependencies
install:
	poetry install

install-all:
	poetry install --with viz,dl,dev

# Update requirements.txt files from Poetry
update-requirements:
	@echo "Exporting core requirements..."
	poetry export -f requirements.txt --without-hashes -o requirements.txt
	@echo "Exporting viz requirements..."
	poetry export --with viz -f requirements.txt --without-hashes -o requirements-viz.txt
	@echo "Exporting dev requirements..."
	poetry export --only dev -f requirements.txt --without-hashes -o requirements-dev.txt
	@echo "✓ Requirements files updated"

# Update Databricks environment YAML files
update-environments: update-requirements
	@echo "Updating base-core.yml..."
	@poetry export -f requirements.txt --without-hashes | \
		awk 'BEGIN {print "  - pip:"} {print "      - " $$0}' > /tmp/deps-core.txt
	@sed -i.bak '/- pip:/,$$d' environments/base-core.yml
	@cat /tmp/deps-core.txt >> environments/base-core.yml

	@echo "Updating base-viz.yml..."
	@poetry export --with viz -f requirements.txt --without-hashes | \
		awk 'BEGIN {print "  - pip:"} {print "      - " $$0}' > /tmp/deps-viz.txt
	@sed -i.bak '/- pip:/,$$d' environments/base-viz.yml
	@cat /tmp/deps-viz.txt >> environments/base-viz.yml

	@echo "Updating base-dl.yml..."
	@poetry export --with dl,viz -f requirements.txt --without-hashes | \
		awk 'BEGIN {print "  - pip:"} {print "      - " $$0}' > /tmp/deps-dl.txt
	@sed -i.bak '/- pip:/,$$d' environments/base-dl.yml
	@cat /tmp/deps-dl.txt >> environments/base-dl.yml

	@rm -f /tmp/deps-*.txt environments/*.bak
	@echo "✓ Environment YAML files updated"

# Validate bundle configuration
validate:
	databricks bundle validate

# Update notebook environment metadata for each target
update-notebooks-dev:
	@echo "Updating notebook metadata for dev environment..."
	python3 scripts/update_notebook_environments.py --target dev
	@echo "✓ Notebooks updated for dev"

update-notebooks-staging:
	@echo "Updating notebook metadata for staging environment..."
	python3 scripts/update_notebook_environments.py --target staging
	@echo "✓ Notebooks updated for staging"

update-notebooks-prod:
	@echo "Updating notebook metadata for prod environment..."
	python3 scripts/update_notebook_environments.py --target prod
	@echo "✓ Notebooks updated for prod"

# Deploy environments only (faster than full deploy)
deploy-environments:
	@echo "Deploying environment files to Databricks..."
	databricks bundle deploy
	@echo "✓ Environment files deployed"

# Full deployment workflow: update notebooks + deploy bundle
deploy-dev: update-notebooks-dev
	@echo "Deploying bundle to dev..."
	databricks bundle deploy -t dev
	@echo "✓ Deployed to dev environment"

deploy-staging: update-notebooks-staging
	@echo "Deploying bundle to staging..."
	databricks bundle deploy -t staging
	@echo "✓ Deployed to staging environment"

deploy-prod: update-notebooks-prod
	@echo "Deploying bundle to prod..."
	databricks bundle deploy -t prod
	@echo "✓ Deployed to prod environment"

# Alias for deploy-dev
deploy: deploy-dev

# Run tests
test:
	poetry run pytest

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -f /tmp/deps-*.txt environments/*.bak
	@echo "✓ Cleaned temporary files"
