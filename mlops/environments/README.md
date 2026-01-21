# Environment Management for Databricks Serverless

## Strategy: Minimal Environment Files

The environment YAML files (`base-core.yml`, `base-viz.yml`, `base-dl.yml`) contain **only essential packages**:

- `mlflow>=3.0.0`
- `databricks-feature-engineering>=0.2.0`  
- `pandas>=1.5.0`
- `numpy>=1.24.0`
- `scikit-learn>=1.3.0`
- Plus visualization or deep learning specific packages

## Why Minimal?

**Databricks Serverless Runtime 4** already includes most packages:

### Pre-installed in Runtime (CPU)
- `pandas`, `numpy`, `pyarrow`
- `scikit-learn` 1.6.1, `scipy` 1.15.1
- `matplotlib`, `seaborn` 0.13.2
- `mlflow` (native on Databricks)
- `pyspark` 4.0.0+

### Pre-installed in GPU Environments
- `torch` 2.7.1, `torchvision` 0.22.1
- `pytorch-lightning` 2.5.4
- `transformers` 4.56.1

### Cloud & Utilities
- `requests`, `httpx`, `pydantic`
- `azure-*` packages (storage, identity, etc.)

## Environment Files

- **base-core.yml** - Minimal core packages (5 packages)
- **base-viz.yml** - Core + visualization (7 packages)
- **base-dl.yml** - Core + deep learning + viz (10 packages)

## Additional Packages

Install notebook-specific packages via `%pip install`:

```python
# Example: Install a specific package not in environment file
%pip install xgboost
%restart_python
```

## Benefits

✅ **Fast cluster startup** (~30 sec vs 3-5 min with 180+ packages)  
✅ **Leverages pre-installed packages** (no redundant installs)  
✅ **Clear dependencies** (only what's truly needed)

## References
- [Databricks Serverless Environment 4 (CPU)](https://docs.databricks.com/release-notes/serverless/environment-version/four)
- [Databricks Serverless Environment 4 (GPU)](https://docs.databricks.com/release-notes/serverless/environment-version/four-gpu)
