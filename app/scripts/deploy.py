#!/usr/bin/env python3
"""
Databricks App Deployment Script - Sync & Deploy Approach

This script:
1. Validates app.yaml and requirements.txt exist
2. Syncs source code to Databricks workspace
3. Starts the app (if not already active)
4. Deploys the code to the app
"""

import os
import subprocess
import sys
import time
from typing import Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import App, ComputeState


APP_NAME = "fashion-rec-app-dev"
APP_DESCRIPTION = "Fashion Recommendations Dashboard"
WORKSPACE_PATH = "/Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev"


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    
    return result


def validate_configuration() -> bool:
    """Validate that required configuration files exist."""
    print("Validating configuration files...")
    
    required_files = ["app.yaml", "requirements.txt", "app.py"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✓ All required configuration files found")
    return True


def check_app_exists(w: WorkspaceClient, app_name: str) -> Optional[App]:
    """Check if an app with the given name exists."""
    print(f"Checking if app '{app_name}' exists...")
    try:
        app = w.apps.get(name=app_name)
        compute_status = app.compute_status.state if app.compute_status else "UNKNOWN"
        print(f"✓ Found existing app: {app.name} (compute: {compute_status})")
        return app
    except Exception as e:
        print(f"App '{app_name}' not found: {e}")
        return None


def create_app(w: WorkspaceClient, app_name: str) -> App:
    """Create a new Databricks app."""
    print(f"Creating app '{app_name}'...")
    
    try:
        app = w.apps.create(
            name=app_name,
            description=APP_DESCRIPTION,
            user_api_scopes=[
                "sql",
                "files.files",
                "catalog.catalogs:read",
                "catalog.schemas:read",
                "catalog.tables:read",
            ]
        )
        print(f"✓ App created successfully: {app.name}")
        return app
    except Exception as e:
        print(f"❌ Error creating app: {e}")
        raise


def sync_source_code(workspace_path: str) -> bool:
    """Sync source code to Databricks workspace."""
    print(f"\nSyncing source code to {workspace_path}...")
    
    # Run sync without watch mode (one-time sync)
    result = run_command(
        ["databricks", "sync", ".", workspace_path],
        check=False
    )
    
    if result.returncode != 0:
        print("❌ Sync failed!")
        return False
    
    print("✓ Source code synced successfully")
    return True


def start_app(w: WorkspaceClient, app_name: str) -> bool:
    """Start the app if it's not already running."""
    print(f"\nStarting app '{app_name}'...")
    
    try:
        app = w.apps.get(name=app_name)
        compute_status = app.compute_status.state if app.compute_status else None
        
        if compute_status == ComputeState.ACTIVE:
            print("✓ App compute is already active")
            return True
        
        # Start the app
        w.apps.start(name=app_name)
        
        # Wait for compute to be active
        max_retries = 30
        for i in range(max_retries):
            time.sleep(2)
            app = w.apps.get(name=app_name)
            compute_status = app.compute_status.state if app.compute_status else None
            
            if compute_status == ComputeState.ACTIVE:
                print("✓ App compute is now active")
                return True
            
            if i % 5 == 0:
                print(f"  Waiting for compute to start... ({compute_status})")
        
        print("⚠️  Timeout waiting for compute to start")
        return False
        
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        return False


def deploy_app(app_name: str, workspace_path: str) -> bool:
    """Deploy the app using databricks apps deploy."""
    print(f"\nDeploying app '{app_name}'...")
    
    result = run_command(
        ["databricks", "apps", "deploy", app_name, "--source-code-path", workspace_path],
        check=False
    )
    
    if result.returncode != 0:
        print("❌ Deployment failed!")
        return False
    
    print("✓ App deployed successfully")
    return True


def get_app_url(w: WorkspaceClient, app_name: str) -> Optional[str]:
    """Get the URL for the deployed app."""
    try:
        app = w.apps.get(name=app_name)
        return app.url
    except Exception:
        return None


def main():
    """Main deployment logic."""
    print("=" * 60)
    print("Databricks App Deployment - Sync & Deploy")
    print("=" * 60)
    
    # Parse environment from args
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    app_name = f"fashion-rec-app-{env}"
    workspace_path = f"/Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-{env}"
    
    print(f"Environment: {env}")
    print(f"App Name: {app_name}")
    print(f"Workspace Path: {workspace_path}")
    print()
    
    # Validate configuration
    if not validate_configuration():
        print("\n❌ Configuration validation failed!")
        sys.exit(1)
    
    # Initialize Workspace Client
    print("\nInitializing Databricks workspace client...")
    try:
        w = WorkspaceClient()
        print(f"✓ Connected to workspace: {w.config.host}")
    except Exception as e:
        print(f"❌ Error initializing workspace client: {e}")
        print("Please ensure you have authenticated with Databricks CLI")
        print("Run: databricks auth login --host <your-workspace-url>")
        sys.exit(1)
    
    # Check if app exists, create if not
    existing_app = check_app_exists(w, app_name)
    
    if not existing_app:
        print(f"\nApp '{app_name}' does not exist. Creating it...")
        try:
            create_app(w, app_name)
        except Exception as e:
            print(f"\n❌ Failed to create app: {e}")
            sys.exit(1)
    
    # Sync source code
    if not sync_source_code(workspace_path):
        print("\n❌ Source code sync failed!")
        sys.exit(1)
    
    # Start app
    if not start_app(w, app_name):
        print("\n⚠️  Warning: App may not be fully started")
        print("Continuing with deployment...")
    
    # Deploy app
    if not deploy_app(app_name, workspace_path):
        print("\n❌ Deployment failed!")
        sys.exit(1)
    
    # Get app URL
    app_url = get_app_url(w, app_name)
    
    print("\n" + "=" * 60)
    print("✅ Deployment Successful!")
    print("=" * 60)
    if app_url:
        print(f"\n🌐 App URL: {app_url}")
    print(f"\n📊 Monitor your app:")
    print(f"   databricks apps get {app_name}")
    print(f"\n🔄 To sync and redeploy changes:")
    print(f"   ./deploy.sh {env}")
    print()


if __name__ == "__main__":
    main()
