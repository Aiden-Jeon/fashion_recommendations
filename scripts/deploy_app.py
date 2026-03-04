#!/usr/bin/env python3
"""
Databricks App Deployment Script

Handles both initial deployment and update deployment of Databricks apps.
Includes pre-deploy validation of Lakebase synced tables.
"""

import subprocess
import sys
import argparse
import json
import os


# Lakebase configuration
LAKEBASE_INSTANCE = "shared-lakebase"
WAREHOUSE_ID = "75fd8278393d07eb"
SYNCED_TABLES = [
    "articles_synced",
    "customers_synced",
    "customer_demographics_synced",
    "product_sales_summary_synced",
    "time_series_sales_synced",
    "transactions_synced",
    "predictions_synced_v2",
]
CATALOG_SCHEMA = "shared.fashion_recommendations"


def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"\n🔄 {description}...")
    print(f"   Command: {command}")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error: {description} failed")
        print(f"   stderr: {result.stderr}")
        return False

    print(f"✅ {description} completed")
    if result.stdout:
        print(f"   {result.stdout}")

    return True


def validate_lakebase(profile):
    """
    Validate Lakebase instance and synced tables are accessible.
    Returns True if all checks pass, False otherwise.
    """
    print(f"\n{'='*60}")
    print(f"🔍 Pre-Deploy Validation: Lakebase & Synced Tables")
    print(f"{'='*60}\n")

    all_ok = True

    # 1. Check Lakebase instance status
    print("1. Checking Lakebase instance status...")
    result = subprocess.run(
        f"databricks database get-database-instance {LAKEBASE_INSTANCE} -p {profile} -o json",
        shell=True, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"   ❌ Cannot reach Lakebase instance '{LAKEBASE_INSTANCE}': {result.stderr.strip()}")
        return False

    instance = json.loads(result.stdout)
    state = instance.get("state", "UNKNOWN")
    if state != "AVAILABLE":
        print(f"   ❌ Lakebase instance is {state} (expected AVAILABLE)")
        return False
    print(f"   ✅ Instance '{LAKEBASE_INSTANCE}' is AVAILABLE")

    # 2. Check synced table statuses
    print("\n2. Checking synced table statuses...")
    for tbl in SYNCED_TABLES:
        full_name = f"{CATALOG_SCHEMA}.{tbl}"
        result = subprocess.run(
            f"databricks api get /api/2.0/database/synced_tables/{full_name} -p {profile}",
            shell=True, capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"   ❌ {tbl}: not found or error")
            all_ok = False
            continue

        info = json.loads(result.stdout)
        sync_state = info.get("data_synchronization_status", {}).get("detailed_state", "UNKNOWN")
        if "ONLINE" in sync_state:
            print(f"   ✅ {tbl}: {sync_state}")
        elif "PROVISIONING" in sync_state:
            print(f"   ⚠️  {tbl}: {sync_state} (initial sync in progress)")
        else:
            print(f"   ❌ {tbl}: {sync_state}")
            all_ok = False

    # 3. Test a query against synced tables
    print("\n3. Testing query execution against synced tables...")
    test_query = f"SELECT count(*) as cnt FROM {CATALOG_SCHEMA}.articles_synced"
    result = subprocess.run(
        f'''databricks api post /api/2.0/sql/statements -p {profile} --json '{{"warehouse_id": "{WAREHOUSE_ID}", "statement": "{test_query}", "wait_timeout": "30s"}}\'''',
        shell=True, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"   ❌ Query execution failed: {result.stderr.strip()}")
        all_ok = False
    else:
        resp = json.loads(result.stdout)
        query_state = resp.get("status", {}).get("state", "UNKNOWN")
        if query_state == "SUCCEEDED":
            rows = resp.get("result", {}).get("data_array", [])
            count = rows[0][0] if rows else "?"
            print(f"   ✅ Test query succeeded (articles_synced count: {count})")
        else:
            error_msg = resp.get("status", {}).get("error", {}).get("message", "unknown error")
            print(f"   ❌ Query failed: {error_msg}")
            all_ok = False

    print(f"\n{'='*60}")
    if all_ok:
        print("✅ All pre-deploy validations passed!")
    else:
        print("❌ Some validations failed. Fix issues before deploying.")
    print(f"{'='*60}\n")

    return all_ok


def deploy_app(app_name, target_env, profile, source_code_path, is_initial_deployment, skip_validation=False):
    """
    Deploy a Databricks app.

    Args:
        app_name: Name of the app (e.g., 'fashion-recommendations-simple')
        target_env: Target environment (e.g., 'dev', 'prod')
        profile: Databricks profile name (e.g., 'DEFAULT')
        source_code_path: Path to source code in Workspace
        is_initial_deployment: True for first deployment, False for updates
        skip_validation: Skip Lakebase pre-deploy validation
    """

    print(f"\n{'='*60}")
    print(f"🚀 Databricks App Deployment")
    print(f"{'='*60}")
    print(f"   App Name: {app_name}")
    print(f"   Environment: {target_env}")
    print(f"   Profile: {profile}")
    print(f"   Deployment Type: {'Initial' if is_initial_deployment else 'Update'}")
    print(f"{'='*60}\n")

    # Step 0: Pre-deploy validation
    if skip_validation:
        print("⚠️  Skipping Lakebase pre-deploy validation (--skip-validation)")
    elif not validate_lakebase(profile):
        print("❌ Aborting deployment due to failed pre-deploy validation.")
        print("   Ensure Lakebase instance and synced tables are healthy.")
        print("   Use --skip-validation to bypass this check.")
        return False

    # Step 1: Bundle deploy (both initial and update)
    bundle_cmd = f"databricks bundle deploy -t {target_env} -p {profile}"
    if not run_command(bundle_cmd, "Bundle deploy"):
        return False

    # Step 2: App start (only for initial deployment)
    if is_initial_deployment:
        start_cmd = f"databricks apps start {app_name} -p {profile}"
        if not run_command(start_cmd, "App start"):
            return False

    # Step 3: App deploy (both initial and update)
    deploy_cmd = f"databricks apps deploy {app_name} --source-code-path {source_code_path} -p {profile}"
    if not run_command(deploy_cmd, "App deploy"):
        return False

    print(f"\n{'='*60}")
    print(f"✅ Deployment completed successfully!")
    print(f"{'='*60}\n")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Databricks apps with support for initial and update deployments"
    )

    parser.add_argument(
        "app_name", help="Name of the app (e.g., 'fashion-recommendations-simple')"
    )

    parser.add_argument(
        "--target", "-t", default="dev", help="Target environment (default: dev)"
    )

    parser.add_argument(
        "--profile",
        "-p",
        default="DEFAULT",
        help="Databricks profile name (default: DEFAULT)",
    )

    parser.add_argument(
        "--source-code-path",
        required=True,
        help="Path to source code in Workspace (e.g., /Workspace/Users/user@domain.com/.bundle/app_name/dev/files)",
    )

    parser.add_argument(
        "--initial",
        action="store_true",
        help="Flag for initial deployment (includes app start command)",
    )

    parser.add_argument(
        "--update",
        action="store_true",
        help="Flag for update deployment (skips app start command)",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Lakebase pre-deploy validation",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run pre-deploy validation, do not deploy",
    )

    args = parser.parse_args()

    # Validate-only mode
    if args.validate_only:
        success = validate_lakebase(args.profile)
        sys.exit(0 if success else 1)

    # Determine deployment type
    if args.initial and args.update:
        print("❌ Error: Cannot specify both --initial and --update")
        sys.exit(1)

    # Default to update if neither is specified
    is_initial = args.initial

    # Deploy the app
    success = deploy_app(
        app_name=args.app_name,
        target_env=args.target,
        profile=args.profile,
        source_code_path=args.source_code_path,
        is_initial_deployment=is_initial,
        skip_validation=args.skip_validation,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
