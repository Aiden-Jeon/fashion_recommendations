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

* `src/`: Data loading notebooks, SQL scripts, and utilities
  * `src/01_load_data.ipynb`: Load CSV data to Delta tables
  * `src/02_create_features.ipynb`: Create aggregated feature tables
  * `src/setup_lakebase_sync.sql`: Full sync setup (7 tables)
  * `src/setup_lakebase_sync_minimal.sql`: Minimal sync (6 tables)
  * `src/fashion_rec_dataops/`: Shared Python utilities for data operations
* `resources/`: Workflow configurations
  * `resources/data-pipeline-workflow.yml`: Complete data pipeline (load → features → sync)
* `config/`: Catalog and path configurations
* `scripts/`: Data management scripts
  * `scripts/setup_synced_tables.sh`: Shell script for SQL-based syncing
  * `scripts/manage_synced_tables.py`: Legacy Python SDK approach
* **Documentation:**
  * `SETUP_GUIDE.md`: Complete setup walkthrough
  * `SYNCED_TABLES.md`: Synced tables documentation
  * `SYNCED_TABLES_QUICK_REF.md`: Quick reference
  * `MIGRATION_SUMMARY.md`: Python SDK → SQL migration guide


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

# Run data loading workflow (load raw data -> create features -> sync to Lakebase)
make run-workflow
```

**⚠️ IMPORTANT:** 
- The `deploy-dev` and `deploy-prod` commands automatically update notebook environment metadata to point to the correct workspace paths before deployment.
- The workflow now includes automatic syncing to Lakebase at the end.
- **Set SQL Warehouse ID** in `databricks.yml` before running the workflow (see [Configuration](#configuration) below).

## Configuration

### SQL Warehouse Setup (Required for Workflows)

The data pipeline workflow automatically syncs tables to Lakebase at the end. You need to configure a SQL Warehouse ID:

1. **List available warehouses:**
   ```bash
   databricks sql warehouses list
   ```

2. **Set the warehouse ID in `databricks.yml`:**
   ```yaml
   targets:
     dev:
       variables:
         sql_warehouse_id: "your-warehouse-id-here"
   ```

3. **Or use environment variable:**
   ```bash
   export DATABRICKS_WAREHOUSE_ID=your-warehouse-id
   ```

The workflow will use this warehouse to execute the Lakebase sync SQL at the end of each pipeline run.

**📖 For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

## Integration with MLOps

DataOps pipeline flow:

```
DataOps Pipeline (this project)
  1. Load Data (01_load_data.ipynb)
     ↓ Creates raw Delta tables
     → articles, customers, transactions
  
  2. Create Features (02_create_features.ipynb)
     ↓ Creates aggregated feature tables
     → product_sales_summary, customer_demographics, time_series_sales
  
  3. Sync to Lakebase (setup_lakebase_sync_minimal.sql)
     ↓ Creates synced tables for low-latency access
     → *_synced tables in Lakebase (PostgreSQL)
     ↓
  Databricks Apps
     → Use synced tables for fast OLTP queries
```

MLOps integration (separate project):
```
MLOps (../mlops/)
  ← Reads DataOps bronze tables
  → Feature engineering (Feature Store)
  → Model training
  → Batch inference
```

## Synced Tables for Low-Latency Access

This project creates synced tables in Lakebase for low-latency OLTP access by Databricks Apps. 

### SQL-Based Approach (RECOMMENDED)

We use SQL to create synced tables, which is simpler and more maintainable than the Python SDK approach:

```bash
# Create/update all synced tables (auto-detects warehouse)
make setup-synced-tables

# Or for specific environments
make setup-synced-tables-dev    # For dev environment
make setup-synced-tables-prod   # For prod environment

# Optional: Set warehouse ID explicitly
export DATABRICKS_WAREHOUSE_ID=<your_warehouse_id>
make setup-synced-tables
```

**Note:** The script will automatically find a running SQL Warehouse if you don't provide one. To use a specific warehouse, set `DATABRICKS_WAREHOUSE_ID` environment variable.

**Synced Tables Created:**
- **Raw tables**: `articles_synced`, `customers_synced`, `transactions_synced`
- **Feature tables**: `product_sales_summary_synced`, `customer_demographics_synced`, `time_series_sales_synced`

The SQL script (`src/setup_lakebase_sync.sql`) handles:
- Enabling Change Data Feed on source tables
- Creating synced tables with correct primary keys
- Setting up triggered scheduling policy
- Verification and data quality checks

### Manual SQL Execution

You can also run the SQL script directly:

```bash
# With default parameters
databricks sql execute --warehouse-id <id> --file src/setup_lakebase_sync.sql

# Or use the shell script with custom parameters
./scripts/setup_synced_tables.sh \
  --warehouse-id <id> \
  --catalog jongseob_demo \
  --schema fashion_recommendations \
  --lakebase-instance shared-online-store
```

### Legacy Python SDK Approach

The Python SDK approach (`scripts/manage_synced_tables.py`) is still available but deprecated in favor of SQL:

```bash
# Create synced tables (legacy)
python scripts/manage_synced_tables.py create \
  --catalog jongseob_demo \
  --schema fashion_recommendations

# Check status
python scripts/manage_synced_tables.py status \
  --catalog jongseob_demo \
  --schema fashion_recommendations
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
