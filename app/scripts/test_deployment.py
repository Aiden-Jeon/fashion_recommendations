#!/usr/bin/env python3
"""
Test script to verify Databricks App deployment

This script checks:
1. Databricks authentication
2. App existence and status
3. Required tables availability
4. Volume access
"""

import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import ApplicationState
from settings import get_settings


def test_authentication():
    """Test Databricks authentication."""
    print("Testing Databricks authentication...")
    try:
        w = WorkspaceClient()
        print(f"✅ Connected to: {w.config.host}")
        return w
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("Run: databricks configure --token")
        return None


def test_app_exists(w: WorkspaceClient, app_name: str):
    """Test if app exists and check its status."""
    print(f"\nChecking app '{app_name}'...")
    try:
        app = w.apps.get(name=app_name)
        print(f"✅ App found: {app.name}")
        state = app.app_status.state if app.app_status else "UNKNOWN"
        print(f"   State: {state}")
        print(f"   URL: {w.config.host}/apps/{app_name}")
        
        if state == ApplicationState.RUNNING:
            print("   ✅ App is running")
            return True
        elif state in [ApplicationState.UNAVAILABLE, ApplicationState.CRASHED]:
            print(f"   ❌ App is in {state} state")
            if app.app_status and app.app_status.message:
                print(f"   Error: {app.app_status.message}")
            return False
        else:
            print(f"   ⚠️  App is in {state} state")
            return False
    except Exception as e:
        print(f"❌ App not found: {e}")
        print("   Run ./deploy.sh to create and deploy the app")
        return False


def test_tables(w: WorkspaceClient):
    """Test if required tables exist."""
    print("\nChecking required tables...")
    settings = get_settings()
    
    required_tables = [
        "articles_synced",
        "customer_demographics_synced",
        "product_sales_summary_synced",
        "time_series_sales_synced",
        "transactions_synced",
    ]
    
    all_exist = True
    for table_name in required_tables:
        full_name = f"{settings.catalog_name}.{settings.schema_name}.{table_name}"
        try:
            # Try to get table info
            w.tables.get(full_name=full_name)
            print(f"✅ {full_name}")
        except Exception as e:
            print(f"❌ {full_name} - {e}")
            all_exist = False
    
    return all_exist


def test_volume_access(w: WorkspaceClient):
    """Test if volume is accessible."""
    print("\nChecking volume access...")
    settings = get_settings()
    
    try:
        # Try to list files in the volume
        volume_path = f"{settings.volume_path}/images/"
        files = list(w.files.list_directory_contents(directory_path=volume_path))
        print(f"✅ Volume accessible: {volume_path}")
        print(f"   Found {len(files)} directories/files")
        return True
    except Exception as e:
        print(f"❌ Volume access failed: {e}")
        print(f"   Path: {settings.volume_path}")
        return False


def test_sql_warehouse(w: WorkspaceClient):
    """Test if SQL Warehouse is available."""
    print("\nChecking SQL Warehouses...")
    try:
        warehouses = list(w.warehouses.list())
        if not warehouses:
            print("❌ No SQL Warehouses found")
            print("   Create a SQL Warehouse in Databricks workspace")
            return False
        
        print(f"✅ Found {len(warehouses)} SQL Warehouse(s)")
        for wh in warehouses[:3]:  # Show first 3
            status = "🟢" if wh.state.value == "RUNNING" else "🔴"
            print(f"   {status} {wh.name} ({wh.state.value})")
        return True
    except Exception as e:
        print(f"❌ Error checking SQL Warehouses: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Databricks App Deployment Test")
    print("=" * 60)
    
    # Test authentication
    w = test_authentication()
    if not w:
        sys.exit(1)
    
    # Test app for both dev and prod
    app_names = ["fashion-rec-app", "fashion-rec-app-prod"]
    app_exists = False
    for app_name in app_names:
        if test_app_exists(w, app_name):
            app_exists = True
    
    # Test tables
    tables_ok = test_tables(w)
    
    # Test volume
    volume_ok = test_volume_access(w)
    
    # Test SQL Warehouse
    warehouse_ok = test_sql_warehouse(w)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Authentication: ✅")
    print(f"App Deployed: {'✅' if app_exists else '❌ Run ./deploy.sh'}")
    print(f"Tables: {'✅' if tables_ok else '❌'}")
    print(f"Volume: {'✅' if volume_ok else '❌'}")
    print(f"SQL Warehouse: {'✅' if warehouse_ok else '❌'}")
    
    if app_exists and tables_ok and volume_ok and warehouse_ok:
        print("\n✅ All checks passed! Your app should be working.")
        sys.exit(0)
    else:
        print("\n⚠️  Some checks failed. Please review the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

