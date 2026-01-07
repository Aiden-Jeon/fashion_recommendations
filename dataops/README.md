# Fashion Recommendations DataOps

Data operations project for loading raw data and preparing application-specific features.

## Scope & Responsibilities

**DataOps handles:**
- Raw data ingestion from CSV files to Bronze tables
- Application-specific feature tables (synced to Lakebase for low-latency OLTP access)
- Data operations utilities and scripts

**MLOps handles** (separate project):
- Feature engineering for ML models (Feature Store)
- Model training and evaluation
- Batch inference and predictions

## Project Structure

* `src/`: Data loading notebooks and utilities
  * `src/01_load_data.ipynb`: Load CSV data to Bronze Delta tables
  * `src/03_prepare_app_features.ipynb`: Prepare app-specific features
  * `src/fashion_rec_dataops/`: Shared Python utilities for data operations
* `resources/`: Workflow configurations
  * `resources/data-loading-workflow.yml`: Bronze table creation workflow
  * `resources/app-data-prep-workflow.yml`: App feature preparation workflow
* `config/`: Catalog and path configurations
* `scripts/`: Data management scripts (synced tables, etc.)


## Getting started

Choose how you want to work on this project:

(a) Directly in your Databricks workspace, see
    https://docs.databricks.com/dev-tools/bundles/workspace.

(b) Locally with an IDE like Cursor or VS Code, see
    https://docs.databricks.com/dev-tools/vscode-ext.html.

(c) With command line tools, see https://docs.databricks.com/dev-tools/cli/databricks-cli.html

If you're developing with an IDE, dependencies for this project should be installed using uv:

*  Make sure you have the UV package manager installed.
   It's an alternative to tools like pip: https://docs.astral.sh/uv/getting-started/installation/.
*  Run `uv sync --dev` to install the project's dependencies.


# Using this project

## Quick Start with Makefile (RECOMMENDED)

This project includes a Makefile for common development tasks:

```bash
# View all available commands
make help

# Deploy to dev environment (auto-updates notebooks)
make deploy-dev

# Deploy to prod environment (auto-updates notebooks)
make deploy-prod

# Run data loading workflow (load raw data to bronze tables)
make run-workflow
```

**⚠️ IMPORTANT:** The `deploy-dev` and `deploy-prod` commands automatically update notebook environment metadata to point to the correct workspace paths before deployment.

## Integration with MLOps

DataOps creates Bronze tables that MLOps consumes:

```
DataOps (this project)
  ↓ Creates bronze tables
  → articles_bronze, customers_bronze, transactions_bronze
       ↓ 
MLOps (../mlops/)
  → Feature engineering (Feature Store)
  → Model training
  → Batch inference
```

## Using the CLI Directly (Advanced)

The Databricks workspace and IDE extensions provide a graphical interface for working
with this project. It's also possible to interact with it directly using the CLI:

1. Authenticate to your Databricks workspace, if you have not done so already:
    ```
    $ databricks configure
    ```

2. **⚠️ WARNING:** If you use `databricks bundle deploy` directly, you must manually update notebook environments first:
    ```
    # Update notebooks for dev environment
    $ python3 scripts/update_notebook_environments.py --target dev
    
    # Then deploy
    $ databricks bundle deploy --target dev
    ```
    
    **Recommended:** Use `make deploy-dev` instead, which handles both steps automatically.

    (Note that "dev" is the default target, so the `--target` parameter
    is optional here.)

    This deploys everything that's defined for this project.
    For example, the default template would deploy a job called
    `[dev yourname] fashion_rec_dataops_job` to your workspace.
    You can find that resource by opening your workpace and clicking on **Jobs & Pipelines**.

3. Similarly, to deploy a production copy, type:
   ```
   $ databricks bundle deploy --target prod
   ```
   Note that the default job from the template has a schedule that runs every day
   (defined in resources/sample_job.job.yml). The schedule
   is paused when deploying in development mode (see
   https://docs.databricks.com/dev-tools/bundles/deployment-modes.html).

4. To run a job or pipeline, use the "run" command:
   ```
   $ databricks bundle run
   ```

5. Finally, to run tests locally, use `pytest`:
   ```
   $ uv run pytest
   ```
