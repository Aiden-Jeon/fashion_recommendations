# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook Template
# MAGIC
# MAGIC **Base Environment:** Use `base-core.yml` (or base-viz/base-dl as needed)
# MAGIC
# MAGIC ## Setup Instructions:
# MAGIC 1. Duplicate this notebook
# MAGIC 2. Environment panel → Base environment → Custom
# MAGIC 3. Enter path: `/Workspace/Users/<your-email>/.bundle/fashion_recommendations/dev/environments/base-core.yml`
# MAGIC 4. Save and continue working!

# COMMAND ----------

# MAGIC %md
# MAGIC ## Alternative: Quick Setup with %pip
# MAGIC
# MAGIC If you haven't configured the base environment yet, run this cell:

# COMMAND ----------

# Uncomment to install dependencies
# %pip install -r ../../requirements.txt
# %restart_python

# COMMAND ----------

# MAGIC %md
# MAGIC ## Start Your Work Here

# COMMAND ----------

import sys
from pyspark.sql.functions import *
from pyspark.sql.types import *
import pandas as pd

# Add project root to path (go up 2 levels from notebooks/)
sys.path.append("../..")

# Your code here
