# Databricks notebook source
# MAGIC %pip install kaggle
# MAGIC %restart_python

# COMMAND ----------

import os

os.environ['KAGGLE_API_TOKEN'] = 'KGAT_372d4096f74ae5dc36a553328e947e86'

# COMMAND ----------

# MAGIC %sh
# MAGIC # Download H&M Personalized Fashion Recommendations dataset to ephemeral storage
# MAGIC kaggle competitions download -c h-and-m-personalized-fashion-recommendations -p /tmp/hm_data

# COMMAND ----------

# Unzip the downloaded files directly to the volume
import zipfile
import glob

for zip_file in glob.glob('/tmp/hm_data/*.zip'):
    with zipfile.ZipFile(zip_file, 'r') as z:
        z.extractall('/Volumes/jongseob_demo/fashion_recommendations/data/')

# COMMAND ----------

# %sh
# cp -r /tmp/hm_data/* /Volumes/jongseob_demo/fashion_recommendations/data/