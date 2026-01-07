#!/usr/bin/env python3
"""
Update notebook environment metadata with workspace paths based on target environment.

This script automatically discovers all notebooks under the src/ directory and updates
the base_environment path in notebook metadata to point to the correct location in the
Databricks workspace after bundle deployment.

Usage:
    python scripts/update_notebook_environments.py --target dev
    python scripts/update_notebook_environments.py --target staging
    python scripts/update_notebook_environments.py --target prod
"""

import json
import argparse
import subprocess
import yaml
from pathlib import Path


# Default environment file for notebooks
DEFAULT_ENV_FILE = "base-core.yml"


def discover_notebooks(project_root: Path, src_dir: str = "src") -> dict:
    """
    Discover all notebooks under the specified source directory.
    
    Args:
        project_root: Project root directory
        src_dir: Source directory name to search for notebooks (default: "src")
    
    Returns:
        Dictionary mapping notebook relative paths to environment file names
    """
    notebooks = {}
    src_path = project_root / src_dir
    
    if not src_path.exists():
        print(f"⚠ Warning: Source directory {src_path} not found")
        return notebooks
    
    # Find all .ipynb files recursively
    for notebook_path in src_path.rglob("*.ipynb"):
        # Skip checkpoint files
        if ".ipynb_checkpoints" in str(notebook_path):
            continue
        
        # Get relative path from project root
        rel_path = notebook_path.relative_to(project_root)
        notebooks[str(rel_path)] = DEFAULT_ENV_FILE
    
    return notebooks


def get_bundle_name(project_root: Path = None) -> str:
    """
    Read the bundle name from databricks.yml.

    Args:
        project_root: Project root directory. If None, auto-detect from script location.

    Returns:
        Bundle name from databricks.yml

    Raises:
        FileNotFoundError: If databricks.yml is not found
        ValueError: If bundle name is not found in databricks.yml
    """
    if not project_root:
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    
    databricks_yml = project_root / "databricks.yml"
    
    if not databricks_yml.exists():
        raise FileNotFoundError(
            f"databricks.yml not found at {databricks_yml}. "
            "Please ensure you're running the script from the correct directory."
        )
    
    try:
        with open(databricks_yml, 'r') as f:
            config = yaml.safe_load(f)
            bundle_name = config.get('bundle', {}).get('name')
            
            if not bundle_name:
                raise ValueError(
                    f"Bundle name not found in {databricks_yml}. "
                    "Please ensure 'bundle.name' is defined in the YAML file."
                )
            
            return bundle_name
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing databricks.yml: {e}")


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
    # Get default bundle name from databricks.yml
    default_bundle_name = get_bundle_name()
    
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
        default=default_bundle_name,
        help=f'Bundle name (default: {default_bundle_name})'
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

    # Discover all notebooks under src directory
    notebook_mapping = discover_notebooks(project_root)
    
    if not notebook_mapping:
        print("⚠ No notebooks found to update")
        return
    
    print(f"Found {len(notebook_mapping)} notebook(s) to update:")
    for notebook_rel_path in notebook_mapping.keys():
        print(f"  - {notebook_rel_path}")
    print()

    # Update notebooks with custom workspace environments
    for notebook_rel_path, env_file in notebook_mapping.items():
        notebook_path = project_root / notebook_rel_path

        if not notebook_path.exists():
            print(f"⚠ Warning: {notebook_rel_path} not found, skipping")
            continue

        update_notebook_environment(notebook_path, env_file, workspace_root, is_databricks_provided=False)

    print()
    print(f"✓ All notebooks updated for {args.target} environment!")
    print()
    print("Next steps:")
    print(f"  1. Commit the changes: git add . && git commit -m 'Update notebook environments for {args.target}'")
    print(f"  2. Deploy the bundle: databricks bundle deploy -t {args.target}")


if __name__ == '__main__':
    main()
