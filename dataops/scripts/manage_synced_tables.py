#!/usr/bin/env python3
"""
Manage Lakebase synced tables for low-latency OLTP access.

This script provides utilities to create, delete, and check the status of synced tables
that mirror Delta tables in Lakebase for serving to Databricks Apps.

Usage:
    # Create all app feature synced tables
    python scripts/manage_synced_tables.py create --catalog jongseob_demo --schema dev_fashion_recommendations
    
    # Delete all synced tables
    python scripts/manage_synced_tables.py delete --catalog jongseob_demo --schema dev_fashion_recommendations
    
    # Check status of synced tables
    python scripts/manage_synced_tables.py status --catalog jongseob_demo --schema dev_fashion_recommendations
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.append(str(project_root / "src"))

from fashion_rec_dataops.synced_table_utils import (
    create_multiple_synced_tables,
    delete_synced_table,
    get_synced_table_status
)
from config.catalog_config import LAKEBASE_INSTANCE


# App feature table configurations
APP_FEATURE_TABLES = [
    {
        "table_suffix": "product_sales_summary",
        "primary_key": ["article_id"]
    },
    {
        "table_suffix": "category_insights",
        "primary_key": ["product_group_name", "product_type_name"]
    },
    {
        "table_suffix": "customer_demographics",
        "primary_key": ["customer_id"]
    },
    {
        "table_suffix": "time_series_sales",
        "primary_key": ["date"]
    }
]


def create_synced_tables(catalog: str, schema: str, lakebase_instance: str):
    """Create all app feature synced tables."""
    print(f"Creating synced tables for {catalog}.{schema}")
    print(f"Lakebase instance: {lakebase_instance}")
    print()
    
    # Build configurations with full table names
    configs = []
    for table_config in APP_FEATURE_TABLES:
        table_suffix = table_config["table_suffix"]
        configs.append({
            "source_table": f"{catalog}.{schema}.{table_suffix}",
            "synced_table": f"{catalog}.{schema}.{table_suffix}_synced",
            "primary_key": table_config["primary_key"]
        })
    
    # Create synced tables
    results = create_multiple_synced_tables(
        table_configs=configs,
        lakebase_instance=lakebase_instance
    )
    
    # Return success status
    successful = sum(1 for success in results.values() if success)
    return successful == len(configs)


def delete_synced_tables(catalog: str, schema: str):
    """Delete all app feature synced tables."""
    print(f"Deleting synced tables for {catalog}.{schema}")
    print()
    
    success_count = 0
    for table_config in APP_FEATURE_TABLES:
        table_suffix = table_config["table_suffix"]
        synced_table = f"{catalog}.{schema}.{table_suffix}_synced"
        
        print(f"Deleting: {synced_table}")
        if delete_synced_table(synced_table):
            success_count += 1
        print()
    
    print("=" * 80)
    print(f"Deleted {success_count}/{len(APP_FEATURE_TABLES)} synced tables")
    print("=" * 80)
    
    return success_count == len(APP_FEATURE_TABLES)


def check_synced_table_status(catalog: str, schema: str):
    """Check status of all app feature synced tables."""
    print(f"Checking synced table status for {catalog}.{schema}")
    print()
    
    statuses = []
    for table_config in APP_FEATURE_TABLES:
        table_suffix = table_config["table_suffix"]
        synced_table = f"{catalog}.{schema}.{table_suffix}_synced"
        
        print(f"Checking: {synced_table}")
        status = get_synced_table_status(synced_table)
        
        if status:
            print(f"  ✓ Status: {status.get('detailed_state', 'UNKNOWN')}")
            print(f"  Source: {status.get('source_table', 'N/A')}")
            print(f"  Instance: {status.get('database_instance', 'N/A')}")
            statuses.append(status)
        else:
            print(f"  ✗ Table not found or error retrieving status")
        print()
    
    print("=" * 80)
    print(f"Found {len(statuses)}/{len(APP_FEATURE_TABLES)} synced tables")
    print("=" * 80)
    
    return statuses


def main():
    parser = argparse.ArgumentParser(
        description='Manage Lakebase synced tables for app features'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create synced tables')
    create_parser.add_argument(
        '--catalog',
        required=True,
        help='Catalog name (e.g., jongseob_demo)'
    )
    create_parser.add_argument(
        '--schema',
        required=True,
        help='Schema name (e.g., dev_fashion_recommendations)'
    )
    create_parser.add_argument(
        '--lakebase-instance',
        default=LAKEBASE_INSTANCE,
        help=f'Lakebase instance name (default: {LAKEBASE_INSTANCE})'
    )
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete synced tables')
    delete_parser.add_argument(
        '--catalog',
        required=True,
        help='Catalog name (e.g., jongseob_demo)'
    )
    delete_parser.add_argument(
        '--schema',
        required=True,
        help='Schema name (e.g., dev_fashion_recommendations)'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check synced table status')
    status_parser.add_argument(
        '--catalog',
        required=True,
        help='Catalog name (e.g., jongseob_demo)'
    )
    status_parser.add_argument(
        '--schema',
        required=True,
        help='Schema name (e.g., dev_fashion_recommendations)'
    )
    
    args = parser.parse_args()
    
    # Execute command
    if args.command == 'create':
        success = create_synced_tables(args.catalog, args.schema, args.lakebase_instance)
        sys.exit(0 if success else 1)
    
    elif args.command == 'delete':
        success = delete_synced_tables(args.catalog, args.schema)
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        statuses = check_synced_table_status(args.catalog, args.schema)
        sys.exit(0 if len(statuses) > 0 else 1)


if __name__ == '__main__':
    main()

