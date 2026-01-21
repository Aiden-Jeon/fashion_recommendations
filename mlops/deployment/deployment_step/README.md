# Model Deployment Step

This folder contains notebooks for the MLflow 3.0 deployment workflow, which evaluates, approves, and deploys models by setting the champion alias.

## Overview

The deployment workflow consists of three steps:

1. **Evaluation** (`evaluation.ipynb`) - Evaluates a candidate model on validation/test data
2. **Approval** (`approval.ipynb`) - Checks if the model has been approved for deployment
3. **Deployment** (`deployment.ipynb`) - Sets the 'champion' alias to the approved model version

## Workflow Steps

### 1. Evaluation Step

**Purpose:** Evaluate a candidate model version on validation or test dataset.

**Key Features:**
- Loads model from Unity Catalog
- Generates predictions on evaluation dataset
- Calculates MAP@12 and other recommendation metrics
- Logs evaluation results to MLflow

**Parameters:**
- `model_name` - Fully qualified model name (e.g., `shared.fashion_recommendations.ensemble_model`)
- `model_version` - Model version to evaluate (e.g., `"1"`)
- `catalog_name` - Unity Catalog name (default: `shared`)
- `schema_name` - Schema name (default: `fashion_recommendations`)
- `evaluation_dataset` - Dataset to use: `"val"` or `"test"` (default: `"val"`)

**Output:**
- Evaluation metrics logged to MLflow
- Console output with MAP@12 score

### 2. Approval Step

**Purpose:** Verify that the model version has been approved for deployment.

**Key Features:**
- Checks for the `deployment_approval` tag on the model version
- Verifies that the tag value is `"approved"`
- Blocks deployment if not approved

**Parameters:**
- `model_name` - Fully qualified model name
- `model_version` - Model version to check
- `approval_tag_name` - Name of approval tag (default: `"deployment_approval"`)

**How to Approve a Model:**

Option 1: Via Unity Catalog UI
1. Navigate to Unity Catalog → Models → [Your Model] → Version [X]
2. Click "Add Tag"
3. Add tag `deployment_approval` with value `approved`

Option 2: Via MLflow API
```python
from mlflow import MlflowClient
client = MlflowClient(registry_uri="databricks-uc")
client.set_model_version_tag(
    name="shared.fashion_recommendations.ensemble_model",
    version="1",
    key="deployment_approval",
    value="approved"
)
```

### 3. Deployment Step

**Purpose:** Deploy the model by setting the 'champion' alias.

**Key Features:**
- Sets the 'champion' alias to the approved model version
- Adds deployment timestamp and metadata tags
- Does NOT deploy to model serving (only updates alias)
- Batch inference jobs automatically use the champion model

**Parameters:**
- `model_name` - Fully qualified model name
- `model_version` - Model version to deploy
- `alias` - Alias to set (default: `"champion"`)

**Output:**
- Champion alias points to new model version
- Deployment tags added to model version
- Model URI for reference: `models:/[model_name]@champion`

## Running the Workflow

### Via Databricks Asset Bundle (DAB)

The deployment workflow is defined in `mlops/resources/model-deployment-workflow.yml`.

**Deploy the bundle:**
```bash
cd mlops
databricks bundle deploy --target dev
```

**Run the deployment workflow:**
```bash
databricks bundle run model_deployment_job --target dev
```

### Manual Execution

You can run individual notebooks manually for testing:

1. Open the notebook in Databricks workspace
2. Attach to a cluster
3. Set widget values manually
4. Run all cells

**Note:** These notebooks are designed for job execution, not interactive runs.

## Configuration

### Model Selection

By default, the workflow deploys the `ensemble_model`. To deploy a different model:

1. Edit `mlops/resources/model-deployment-workflow.yml`
2. Change `${var.model_ensemble}` to:
   - `${var.model_popularity}` - Popularity baseline
   - `${var.model_age_rules}` - Age-based rules
   - Or specify a custom model name

### Dynamic Model Version

Currently, the workflow uses a hardcoded model version (`"1"`). To make it dynamic:

**Option 1: Use latest version**
```python
from mlflow import MlflowClient
client = MlflowClient(registry_uri="databricks-uc")
versions = client.search_model_versions(f"name='{model_name}'")
latest_version = max([int(v.version) for v in versions])
```

**Option 2: Trigger with parameter**
- Add a job parameter for `model_version`
- Pass it when triggering the job

**Option 3: Use latest run from training**
- Query MLflow experiments for latest successful run
- Get model version from run metadata

## Champion Alias vs Model Serving

**Champion Alias (Current Approach):**
- ✅ Updates alias pointer in Unity Catalog
- ✅ Batch inference jobs use `models:/[name]@champion`
- ✅ No infrastructure provisioning
- ✅ Instant deployment
- ✅ Cost-effective for batch workloads

**Model Serving (Alternative):**
- Provisions a real-time serving endpoint
- Requires compute resources (always-on or scale-to-zero)
- Higher cost for low-traffic scenarios
- Better for real-time/interactive applications

**For this project:** We use champion alias because:
1. Fashion recommendations are batch-generated
2. No real-time serving requirement
3. Predictions are pre-computed for all customers
4. More cost-effective for the use case

## Workflow Architecture

```
┌─────────────────┐
│ Model Training  │
│    Workflow     │
└────────┬────────┘
         │ Produces new model versions
         ▼
┌─────────────────┐
│   Evaluation    │  ← Load model & validation data
│     Step        │  ← Calculate MAP@12
└────────┬────────┘  ← Log metrics to MLflow
         │
         ▼
┌─────────────────┐
│   Approval      │  ← Check for approval tag
│     Step        │  ← Verify tag = "approved"
└────────┬────────┘  ← Block if not approved
         │
         ▼
┌─────────────────┐
│   Deployment    │  ← Set champion alias
│     Step        │  ← Add deployment tags
└────────┬────────┘  ← Update UC registry
         │
         ▼
┌─────────────────┐
│ Batch Inference │  ← Uses champion alias
│    Workflow     │  ← Generates predictions
└─────────────────┘
```

## Troubleshooting

### Evaluation fails: "Model not found"
- Verify the model exists in Unity Catalog
- Check that `catalog_name` and `schema_name` are correct
- Ensure model version exists

### Approval fails: "Missing tag"
- Add the `deployment_approval` tag with value `approved` to the model version
- Use the Unity Catalog UI or MLflow API

### Deployment fails: "Permission denied"
- Ensure you have `CAN_MANAGE` permission on the model
- Check that the model is in READY status

### Batch inference doesn't use new model
- Verify the champion alias was set correctly
- Check batch inference notebook loads `models:/[name]@champion`
- May need to restart batch inference job

## Next Steps

1. **Automated Approval:** Add metric threshold checks to auto-approve models
2. **Dynamic Versioning:** Use latest version or pass as parameter
3. **Rollback Capability:** Add notebook to rollback to previous champion
4. **Model Comparison:** Compare new model with current champion before deployment
5. **Notifications:** Add Slack/email notifications on deployment success/failure
