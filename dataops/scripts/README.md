# Scripts

## manage_synced_tables.py

Manages Lakebase synced tables for low-latency OLTP access to app features. This script creates, deletes, and checks the status of synced tables that mirror Delta tables in Lakebase for serving to Databricks Apps.

### Why Synced Tables are Needed

Databricks Apps require low-latency access to data for interactive dashboards. Synced tables in Lakebase provide:
- **Low latency**: Sub-second query response times for OLTP workloads
- **Real-time updates**: Automatic synchronization from Delta tables using Change Data Feed
- **Scalability**: Optimized for high-concurrency read operations

### Usage

```bash
# Create all app feature synced tables
python scripts/manage_synced_tables.py create \
  --catalog jongseob_demo \
  --schema dev_fashion_recommendations

# Check status of synced tables
python scripts/manage_synced_tables.py status \
  --catalog jongseob_demo \
  --schema dev_fashion_recommendations

# Delete all synced tables
python scripts/manage_synced_tables.py delete \
  --catalog jongseob_demo \
  --schema dev_fashion_recommendations
```

### App Feature Tables

The script manages synced tables for these app features:

| Source Delta Table | Synced Table | Primary Key | Purpose |
|-------------------|--------------|-------------|----------|
| `product_sales_summary` | `product_sales_summary_synced` | `article_id` | Product sales metrics |
| `customer_demographics` | `customer_demographics_synced` | `customer_id` | Customer segmentation |
| `time_series_sales` | `time_series_sales_synced` | `date` | Time series trends |

### Lakebase Instance

- **Default instance**: `shared-online-store`
- Can be overridden with `--lakebase-instance` flag

### Options

```
create                  Create synced tables from Delta tables
  --catalog CATALOG     Catalog name (required)
  --schema SCHEMA       Schema name (required)
  --lakebase-instance   Lakebase instance name (default: shared-online-store)

status                  Check status of synced tables
  --catalog CATALOG     Catalog name (required)
  --schema SCHEMA       Schema name (required)

delete                  Delete synced tables
  --catalog CATALOG     Catalog name (required)
  --schema SCHEMA       Schema name (required)
```

### Example Output

```
Creating synced tables for jongseob_demo.dev_fashion_recommendations
Lakebase instance: shared-online-store

================================================================================
Creating 4 synced table(s)
================================================================================

[1/4] Processing: jongseob_demo.dev_fashion_recommendations.product_sales_summary_synced
--------------------------------------------------------------------------------
Creating synced table: jongseob_demo.dev_fashion_recommendations.product_sales_summary_synced
  Source: jongseob_demo.dev_fashion_recommendations.product_sales_summary
  Database instance: shared-online-store
  Primary key: ['article_id']
  Enabling Change Data Feed on source table...
  ✓ Change Data Feed enabled
  No existing table to delete
  Creating synced table...
✓ Synced table created successfully: jongseob_demo.dev_fashion_recommendations.product_sales_summary_synced
...

================================================================================
SYNCED TABLE CREATION SUMMARY
================================================================================
Total: 4
Successful: 4
Failed: 0
```

---

## update_notebook_environments.py

Updates notebook environment metadata with workspace paths based on the target deployment environment.

### Why This Script is Needed

Databricks notebooks need to reference environment YAML files using absolute workspace paths (not relative paths). Since the deployment location differs between dev/staging/prod environments, we need to update the notebook metadata before each deployment.

### Usage

```bash
# For dev environment (deploys to user's personal workspace)
python scripts/update_notebook_environments.py --target dev

# For staging environment (deploys to shared workspace)
python scripts/update_notebook_environments.py --target staging

# For production environment (deploys to shared workspace)
python scripts/update_notebook_environments.py --target prod
```

### Workspace Paths by Environment

- **Dev**: `/Workspace/Users/${user.userName}/.bundle/fashion_recs/dev/environments/`
- **Staging**: `/Workspace/Shared/.bundle/fashion_recs/staging/environments/`
- **Prod**: `/Workspace/Shared/.bundle/fashion_recs/prod/environments/`

### What It Does

The script updates the `environmentMetadata.base_environment` field in each notebook's metadata to point to the correct workspace location:

```json
{
  "metadata": {
    "application/vnd.databricks.v1+notebook": {
      "environmentMetadata": {
        "base_environment": "/Workspace/Users/${user.userName}/.bundle/fashion_recs/dev/environments/base-viz.yml",
        "dependencies": [],
        "environment_version": "4"
      }
    }
  }
}
```

### Deployment Workflow

1. **Update notebook environments for target**:
   ```bash
   python scripts/update_notebook_environments.py --target dev
   ```

2. **Commit the changes**:
   ```bash
   git add .
   git commit -m "Update notebook environments for dev deployment"
   ```

3. **Deploy the bundle**:
   ```bash
   databricks bundle deploy -t dev
   ```

### Environment File Mapping

The script maps notebooks to their required environment files:

| Notebook | Environment |
|----------|-------------|
| `data_engineering/notebooks/*.ipynb` | `base-core.yml` (workspace) |
| `training/notebooks/train_popularity.ipynb` | `base-viz.yml` (workspace) |
| `training/notebooks/train_age_rules.ipynb` | `base-viz.yml` (workspace) |
| `training/notebooks/train_ensemble.ipynb` | `base-viz.yml` (workspace) |
| `training/notebooks/train_lstm.ipynb` | `databricks_ai_v4` (Databricks-provided) |
| `deployment/batch_inference/notebooks/*.ipynb` | `base-core.yml` (workspace) |

**Note**: The LSTM notebook uses the Databricks-provided `databricks_ai_v4` environment which includes PyTorch and other deep learning dependencies pre-installed, optimized for GPU workloads.

### Options

```
--target {dev,staging,prod}
    Target environment (required)

--bundle-name BUNDLE_NAME
    Bundle name (default: fashion_recs)

--project-root PROJECT_ROOT
    Project root directory (default: auto-detect from script location)
```

### Example Output

```
Project root: /path/to/project
Target environment: dev

Workspace root: /Workspace/Users/${user.userName}/.bundle/fashion_recs/dev

Updating data_engineering/notebooks/01_load_data.ipynb...
  ✓ Set base_environment to: /Workspace/Users/${user.userName}/.bundle/fashion_recs/dev/environments/base-core.yml
...

✓ All notebooks updated for dev environment!

Next steps:
  1. Commit the changes: git add . && git commit -m 'Update notebook environments for dev'
  2. Deploy the bundle: databricks bundle deploy -t dev
```
