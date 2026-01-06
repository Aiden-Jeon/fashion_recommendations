#!/usr/bin/env python3
"""
Update notebook environment metadata with workspace paths based on target environment.

This script updates the base_environment path in notebook metadata to point to the
correct location in the Databricks workspace after bundle deployment.

Usage:
    python scripts/update_notebook_environments.py --target dev
    python scripts/update_notebook_environments.py --target staging
    python scripts/update_notebook_environments.py --target prod
"""

import json
import argparse
import subprocess
from pathlib import Path


# Notebook to environment file mapping
# Note: train_lstm uses Databricks-provided databricks_ai_v4 environment
NOTEBOOK_ENV_MAPPING = {
    # Data engineering notebooks
    "data_engineering/notebooks/01_load_data.ipynb": "base-core.yml",
    "data_engineering/notebooks/02_create_features.ipynb": "base-core.yml",
    "data_engineering/notebooks/03_create_splits.ipynb": "base-core.yml",

    # Training notebooks
    "training/notebooks/train_popularity.ipynb": "base-viz.yml",
    "training/notebooks/train_age_rules.ipynb": "base-viz.yml",
    "training/notebooks/train_ensemble.ipynb": "base-viz.yml",
    # train_lstm uses databricks_ai_v4 (handled separately)

    # Batch inference notebook
    "deployment/batch_inference/notebooks/batch_inference.ipynb": "base-core.yml",
}

# Notebooks that use Databricks-provided environments (not custom workspace paths)
DATABRICKS_PROVIDED_ENV_MAPPING = {
    "training/notebooks/train_lstm.ipynb": "databricks_ai_v4",
}


def get_current_user() -> str:
    """
    Get the current Databricks workspace user email.

    Returns:
        User email/username from databricks current-user command
    """
    try:
        result = subprocess.run(
            ["databricks", "current-user", "me"],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse JSON output to get userName
        import json
        user_info = json.loads(result.stdout)
        return user_info.get("userName", "")
    except Exception as e:
        print(f"⚠ Warning: Could not get current user: {e}")
        print("  Using template variable instead")
        return "${workspace.current_user.userName}"


def get_workspace_path(target: str, bundle_name: str = "fashion_recommendations", user_name: str = None) -> str:
    """
    Get the workspace root path for the given target environment.

    Args:
        target: Environment target (dev, staging, prod)
        bundle_name: Name of the bundle
        user_name: Optional user name for dev environment

    Returns:
        Workspace path where bundle is deployed
    """
    if target == "dev":
        if not user_name:
            user_name = "${workspace.current_user.userName}"
        return f"/Workspace/Users/{user_name}/.bundle/{bundle_name}/{target}/files"
    elif target in ["staging", "prod"]:
        return f"/Workspace/Shared/.bundle/{bundle_name}/{target}/files"
    else:
        raise ValueError(f"Unknown target: {target}. Must be dev, staging, or prod")


def update_notebook_environment(notebook_path: Path, env_file: str, workspace_root: str, is_databricks_provided: bool = False):
    """
    Update a single notebook's environment metadata.

    Args:
        notebook_path: Path to the notebook file
        env_file: Environment YAML file name (e.g., base-core.yml) or Databricks environment name (e.g., databricks_ai_v4)
        workspace_root: Workspace root path for the target environment
        is_databricks_provided: If True, uses Databricks-provided environment instead of workspace path
    """
    print(f"Updating {notebook_path.relative_to(notebook_path.parents[2])}...")

    with open(notebook_path, 'r') as f:
        notebook = json.load(f)

    # Ensure the Databricks v1 notebook key exists
    databricks_key = 'application/vnd.databricks.v1+notebook'
    if databricks_key not in notebook['metadata']:
        notebook['metadata'][databricks_key] = {}

    if is_databricks_provided:
        # Use Databricks-provided environment (no dependencies array)
        notebook['metadata'][databricks_key]['environmentMetadata'] = {
            'base_environment': env_file,
            'environment_version': '4'
        }
        print(f"  ✓ Set base_environment to Databricks-provided: {env_file}")
    else:
        # Build the workspace path to environment file
        env_workspace_path = f"{workspace_root}/environments/{env_file}"

        # Update environmentMetadata with workspace path
        notebook['metadata'][databricks_key]['environmentMetadata'] = {
            'base_environment': env_workspace_path,
            'dependencies': [],
            'environment_version': '4'
        }
        print(f"  ✓ Set base_environment to: {env_workspace_path}")

    # Write back
    with open(notebook_path, 'w') as f:
        json.dump(notebook, f, indent=1)


def main():
    parser = argparse.ArgumentParser(
        description='Update notebook environment paths for Databricks workspace deployment'
    )
    parser.add_argument(
        '--target',
        required=True,
        choices=['dev', 'staging', 'prod'],
        help='Target environment (dev, staging, or prod)'
    )
    parser.add_argument(
        '--bundle-name',
        default='fashion_recommendations',
        help='Bundle name (default: fashion_recommendations)'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=None,
        help='Project root directory (default: auto-detect from script location)'
    )

    args = parser.parse_args()

    # Determine project root
    if args.project_root:
        project_root = args.project_root
    else:
        # Script is in scripts/ directory, project root is parent
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

    print(f"Project root: {project_root}")
    print(f"Target environment: {args.target}")
    print()

    # Get current user for dev environment
    user_name = None
    if args.target == "dev":
        user_name = get_current_user()
        if user_name and user_name != "${workspace.current_user.userName}":
            print(f"Current user: {user_name}")
        print()

    # Get workspace path for target
    workspace_root = get_workspace_path(args.target, args.bundle_name, user_name)
    print(f"Workspace root: {workspace_root}")
    print()

    # Update notebooks with custom workspace environments
    for notebook_rel_path, env_file in NOTEBOOK_ENV_MAPPING.items():
        notebook_path = project_root / notebook_rel_path

        if not notebook_path.exists():
            print(f"⚠ Warning: {notebook_rel_path} not found, skipping")
            continue

        update_notebook_environment(notebook_path, env_file, workspace_root, is_databricks_provided=False)

    # Update notebooks with Databricks-provided environments
    for notebook_rel_path, env_name in DATABRICKS_PROVIDED_ENV_MAPPING.items():
        notebook_path = project_root / notebook_rel_path

        if not notebook_path.exists():
            print(f"⚠ Warning: {notebook_rel_path} not found, skipping")
            continue

        update_notebook_environment(notebook_path, env_name, workspace_root, is_databricks_provided=True)

    print()
    print(f"✓ All notebooks updated for {args.target} environment!")
    print()
    print("Next steps:")
    print(f"  1. Commit the changes: git add . && git commit -m 'Update notebook environments for {args.target}'")
    print(f"  2. Deploy the bundle: databricks bundle deploy -t {args.target}")


if __name__ == '__main__':
    main()
