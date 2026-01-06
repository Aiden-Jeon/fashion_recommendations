.PHONY: help update-requirements update-environments deploy-environments clean

# Default target
help:
	@echo "Fashion Recommendations MLOps - Development Commands"
	@echo ""
	@echo "Environment Management:"
	@echo "  make update-requirements    - Export Poetry dependencies to requirements.txt files"
	@echo "  make update-environments    - Update Databricks environment YAML files from Poetry"
	@echo "  make deploy-environments    - Deploy environment files to Databricks workspace"
	@echo ""
	@echo "Bundle Commands:"
	@echo "  make validate              - Validate Databricks bundle configuration"
	@echo "  make deploy                - Deploy bundle to dev environment"
	@echo "  make deploy-staging        - Deploy bundle to staging environment"
	@echo "  make deploy-prod           - Deploy bundle to production environment"
	@echo ""
	@echo "Development:"
	@echo "  make install               - Install dependencies with Poetry"
	@echo "  make install-all           - Install all dependencies (including viz, dl, dev)"
	@echo "  make clean                 - Clean temporary files"

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

# Deploy environments only (faster than full deploy)
deploy-environments:
	@echo "Deploying environment files to Databricks..."
	databricks bundle deploy
	@echo "✓ Environment files deployed"
	@echo ""
	@echo "Next steps:"
	@echo "1. Open your notebook in Databricks"
	@echo "2. Click the Environment panel"
	@echo "3. Select Custom base environment"
	@echo "4. Enter path: /Workspace/Users/$$USER/.bundle/fashion_recommendations/dev/environments/base-core.yml"
	@echo "5. Restart notebook environment"

# Deploy bundle to environments
deploy:
	databricks bundle deploy -t dev

deploy-staging:
	databricks bundle deploy -t staging

deploy-prod:
	databricks bundle deploy -t prod

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -f /tmp/deps-*.txt environments/*.bak
	@echo "✓ Cleaned temporary files"
