# Databricks Notebook Setup Guide

**Current Limitation:** You cannot set base environment programmatically in Python files. This must be configured via UI or workspace defaults.

## 🚀 Recommended Workflows

### Workflow 1: One-Time Manual Setup (Best for Long-term)

**When to use:** You work with the same notebooks regularly

**Steps:**
1. Deploy environment files:
   ```bash
   databricks bundle deploy
   ./scripts/get-environment-paths.sh  # Get the path
   ```

2. For EACH notebook (one-time):
   - Open notebook in Databricks
   - Click **Environment** panel (right side)
   - **Base environment** → Select **Custom**
   - Paste path:
     ```
     /Workspace/Users/<your-email>/.bundle/fashion_recommendations/dev/environments/base-core.yml
     ```
   - Click **Apply**

3. Done! Notebook always starts with dependencies pre-installed ✨

**Pros:**
- ✅ Fastest startup after initial setup
- ✅ No code changes needed
- ✅ Clean notebook code

**Cons:**
- ⏳ Must configure each notebook once via UI

---

### Workflow 2: Quick Setup Cell (Best for Rapid Development)

**When to use:** Creating many new notebooks, prototyping, one-off analysis

**Copy this to first cell of every notebook:**

```python
# Setup cell - Run once at start
%pip install -r ../../requirements.txt
%restart_python
```

**Then in second cell:**
```python
from utils.notebook_setup import setup_notebook
setup_notebook()  # Adds project root to path

# Now you can import project modules
from config.config import Config
from utils.data_utils import load_data
```

**Pros:**
- ✅ No manual UI configuration needed
- ✅ Works immediately in any notebook
- ✅ Version controlled

**Cons:**
- ⏱️ Slower startup (installs packages every time)
- 📝 Need to remember to run first cell

---

### Workflow 3: Workspace Default (Best for Teams)

**When to use:** Multiple people working on the project

**Requires workspace admin to:**

1. Go to **Settings → Workspace admin → Compute → Base environments for serverless compute**

2. Click **Create base environment**:
   - **Name:** `fashion-recs-core`
   - **Path:** `/Workspace/Users/<your-email>/.bundle/fashion_recommendations/dev/environments/base-core.yml`
   - Click **Save**

3. Click ⭐ **star icon** next to `fashion-recs-core` to set as default

4. Done! All **new** notebooks automatically use this environment

**Pros:**
- ✅ Zero setup for new notebooks
- ✅ Team consistency
- ✅ Clean notebook code

**Cons:**
- 🔒 Requires admin access
- ⚠️ Only applies to NEW notebooks (existing ones need manual update)

---

## 📋 Quick Reference

### Different Environment Files

Choose based on your notebook needs:

| File | Use Case | Dependencies |
|------|----------|-------------|
| `base-core.yml` | Data engineering, traditional ML | mlflow, pandas, sklearn |
| `base-viz.yml` | EDA, plotting, analysis | + matplotlib, seaborn |
| `base-dl.yml` | LSTM training, deep learning | + PyTorch, torchvision |

### Current Notebook in Screenshot

Based on your screenshot showing `train_ensemble`, I recommend:

**Option A - One-time UI setup (takes 30 seconds):**
1. Run: `./scripts/get-environment-paths.sh`
2. Copy the `base-core.yml` path
3. Set it in Environment panel
4. Remove the `%pip install` cells
5. Enjoy faster startup! 🚀

**Option B - Keep current approach:**
- Your current setup (`%pip install -r ../../requirements.txt`) works fine
- Just add `databricks bundle deploy` to sync requirements.txt
- Continue as-is if it doesn't bother you

---

## 🛠️ Troubleshooting

### "I updated dependencies but notebook doesn't see them"

**If using base environment:**
```
Environment panel → "Reset environment" button
```

**If using %pip install:**
```python
# Re-run first cell
%pip install -r ../../requirements.txt --upgrade
%restart_python
```

### "ModuleNotFoundError for project modules"

Add to your notebook:
```python
import sys
sys.path.append("../..")  # Adjust based on notebook location
```

Or use the setup utility:
```python
from utils.notebook_setup import setup_notebook
setup_notebook()
```

### "Want to switch between environments"

Just change the path in Environment panel:
- Core: `.../environments/base-core.yml`
- Viz: `.../environments/base-viz.yml`
- DL: `.../environments/base-dl.yml`

---

## 📊 Comparison Matrix

| Method | Setup Time | Startup Speed | Code Cleanliness | Team Friendly |
|--------|-----------|---------------|------------------|---------------|
| Workflow 1 (Manual UI) | 30s per notebook | ⚡⚡⚡ Fast | ✨ Clean | ⚠️ Individual |
| Workflow 2 (%pip cell) | 0s | 🐌 Slow | 📝 Extra cell | ✅ Easy |
| Workflow 3 (Default) | Admin only | ⚡⚡⚡ Fast | ✨ Clean | ✅✅ Best |

---

## 🔮 Future Improvements

Vote for this feature request: **"Set base environment via notebook metadata"**

Until then, use the workflows above! 🚀
