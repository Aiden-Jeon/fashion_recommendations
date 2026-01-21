# Scripts

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
| `data_engineering/notebooks/*.ipynb` | Serverless Runtime 4 (default) |
| `training/notebooks/train_popularity.ipynb` | Serverless Runtime 4 (default) |
| `training/notebooks/train_age_rules.ipynb` | Serverless Runtime 4 (default) |
| `training/notebooks/train_ensemble.ipynb` | Serverless Runtime 4 (default) |
| `training/notebooks/train_simple_mlp.ipynb` | `databricks_ai_v4` (GPU-optimized) |
| `deployment/batch_inference/notebooks/*.ipynb` | Serverless Runtime 4 (default) |

**Serverless Runtime 4 includes**: pandas, numpy, scikit-learn, torch, pytorch-lightning, matplotlib, seaborn, mlflow, and more.

**Additional packages** (if needed) are installed via `%pip install` in notebook cells.

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

Configuring notebooks for Databricks Serverless Runtime 4

Updating data_engineering/notebooks/01_create_features.ipynb...
  ✓ Using Serverless Runtime 4 (packages installed via %pip in notebook)

Updating training/notebooks/train_simple_mlp.ipynb...
  ✓ Using Databricks environment: databricks_ai_v4
...

✓ All notebooks configured for Serverless Runtime 4!

Next steps:
  1. Commit the changes: git add . && git commit -m 'Update notebook environments for dev'
  2. Deploy the bundle: databricks bundle deploy -t dev
```
