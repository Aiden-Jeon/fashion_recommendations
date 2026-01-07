# Databricks Serverless Environment Configurations

This directory contains base environment YAML files for Databricks serverless notebooks. These files define the Python dependencies that will be pre-installed in your notebook environments, enabling quick interactive development without manual package installation.

## Available Environments

### 1. `base-core.yml` (Recommended for most notebooks)
Core ML and data engineering dependencies:
- mlflow
- databricks-feature-engineering
- pandas, numpy
- scikit-learn

**Use for:** Data engineering, feature engineering, traditional ML model training

### 2. `base-viz.yml`
Core dependencies + visualization libraries:
- All core dependencies
- matplotlib, seaborn

**Use for:** Exploratory data analysis, model performance visualization

### 3. `base-dl.yml`
Core dependencies + deep learning libraries:
- All core dependencies
- PyTorch, torchvision
- tqdm
- matplotlib, seaborn

**Use for:** LSTM model training, deep learning experiments

## How to Use in Notebooks

### Option 1: Configure in Notebook (One-time setup)

1. Open your notebook in Databricks
2. Click the **Environment** panel on the right side
3. In the **Base environment** dropdown, select **Custom**
4. Enter the workspace path to the environment file:
   ```
   /Workspace/Users/<your-email>/.bundle/fashion_recommendations/dev/environments/base-core.yml
   ```
5. The dependencies will be automatically installed when the notebook starts

### Option 2: Use Workspace Files Path (After bundle deploy)

After running `databricks bundle deploy`, the environment files are synced to:
```
/Workspace/Users/<your-email>/.bundle/fashion_recommendations/<target>/environments/
```

Select this path in the Environment panel's Base environment dropdown.

## Managing Dependencies

### Updating Dependencies

1. **Update `pyproject.toml`** with new packages:
   ```bash
   poetry add <package-name>
   ```

2. **Regenerate environment files**:
   ```bash
   make update-environments
   ```
   Or manually:
   ```bash
   # Update core environment
   poetry export -f requirements.txt --without-hashes | \
     sed 's/^/      - /' > temp && \
     sed '/# Core ML/r temp' environments/base-core.yml -i.bak

   # Update viz environment
   poetry export --with viz -f requirements.txt --without-hashes | \
     sed 's/^/      - /' > temp && \
     sed '/# Core dependencies/r temp' environments/base-viz.yml -i.bak

   # Update dl environment
   poetry export --with dl -f requirements.txt --without-hashes | \
     sed 's/^/      - /' > temp && \
     sed '/# Core dependencies/r temp' environments/base-dl.yml -i.bak

   rm temp *.bak
   ```

3. **Deploy to Databricks**:
   ```bash
   databricks bundle deploy
   ```

4. **Restart notebook environment** to pick up new dependencies

### Version Control

These environment files are:
- ✅ Version controlled (committed to git)
- ✅ Synced via Databricks Asset Bundles
- ✅ Generated from Poetry's lock file
- ✅ Consistent across team members

## Important Notes

### ⚠️ Limitations

1. **Interactive notebooks only**: These base environments configure the interactive notebook environment. Job dependencies are still defined in workflow YAML files.

2. **No PySpark**: Do NOT add PySpark to these environment files - it will crash serverless notebooks.

3. **One-time setup**: You must select the base environment once per notebook via the UI. This cannot (yet) be automated via DAB.

4. **Restart required**: After updating and deploying new environment files, restart your notebook environment to pick up changes.

### 💡 Best Practices

1. **Start minimal**: Use `base-core.yml` by default. Only switch to `base-viz.yml` or `base-dl.yml` when needed.

2. **Pin versions**: Use `==` for production, `>=` for development to balance reproducibility and flexibility.

3. **Keep DRY**: Manage dependencies in `pyproject.toml`, not directly in environment files.

4. **Deploy regularly**: Run `databricks bundle deploy` after updating dependencies to sync changes.

## Troubleshooting

### "Module not found" after installing package

**Cause**: Environment files not synced or notebook not using correct base environment

**Solution**:
1. Run `databricks bundle deploy`
2. Verify environment file path in notebook's Environment panel
3. Restart notebook environment

### "Serverless session stopped" error

**Cause**: Likely installed PySpark or conflicting package

**Solution**:
1. Check environment file for PySpark dependencies
2. Remove conflicting package
3. Restart notebook environment

### Changes not taking effect

**Cause**: Notebook environment caching

**Solution**:
1. Go to Environment panel → Click "Reset environment"
2. Wait for environment to reinitialize
3. Your new dependencies should now be available
