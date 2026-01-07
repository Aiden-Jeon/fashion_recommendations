"""
Utilities for creating and managing Lakebase synced tables.

This module provides functions to create synced tables from Delta tables
for low-latency OLTP access in Databricks Apps.
"""

import time
from typing import List, Optional


def _check_synced_table_exists(synced_table: str) -> bool:
    """
    Check if a synced table exists.

    Args:
        synced_table: Synced table name (fully qualified: catalog.schema.table)

    Returns:
        True if table exists, False otherwise
    """
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        w.database.get_synced_database_table(name=synced_table)
        return True
    except Exception:
        return False


def _wait_for_synced_table_deletion(synced_table: str, max_wait_seconds: int = 300, poll_interval: int = 5) -> bool:
    """
    Wait for a synced table to be fully deleted.

    Args:
        synced_table: Synced table name (fully qualified: catalog.schema.table)
        max_wait_seconds: Maximum time to wait for deletion (default: 300 seconds / 5 minutes)
        poll_interval: Time between status checks in seconds (default: 5 seconds)

    Returns:
        True if table is confirmed deleted, False if timeout
    """
    start_time = time.time()
    elapsed = 0
    
    print(f"  Waiting for synced table deletion to complete...")
    
    while elapsed < max_wait_seconds:
        if not _check_synced_table_exists(synced_table):
            print(f"  ✓ Synced table deletion confirmed (waited {elapsed:.1f}s)")
            return True
        
        time.sleep(poll_interval)
        elapsed = time.time() - start_time
        
        if int(elapsed) % 30 == 0 and elapsed > 0:  # Log every 30 seconds
            print(f"  Still waiting for deletion... ({elapsed:.0f}s elapsed)")
    
    print(f"  ⚠ Timeout waiting for synced table deletion after {max_wait_seconds}s")
    return False


def create_or_update_synced_table(
    source_table: str,
    synced_table: str,
    lakebase_instance: str,
    primary_key: List[str] = None,
    auto_create_database: bool = True,
    skip_if_exists: bool = True,
    scheduling_policy: str = "SNAPSHOT"
) -> bool:
    """
    Create or update a synced table in Lakebase for OLTP access.

    This function:
    1. Validates table names for Postgres compatibility
    2. Enables Change Data Feed on source Delta table (only for TRIGGERED/CONTINUOUS modes)
    3. If skip_if_exists=False and table exists: deletes the table and waits for deletion to complete
    4. Creates the synced table with specified scheduling policy
    5. If skip_if_exists=True and table already exists, skips and returns success

    Args:
        source_table: Source Delta table name (fully qualified: catalog.schema.table)
        synced_table: Synced table name (fully qualified: catalog.schema.table)
        lakebase_instance: Lakebase instance name (e.g., "shared-online-store")
        primary_key: List of columns that form the primary key. If None, uses ["id"]
        auto_create_database: Whether to create database objects if missing
        skip_if_exists: If True, skip creation if synced table already exists. 
                       If False, delete existing table (wait for deletion), then recreate.
        scheduling_policy: Sync mode - "SNAPSHOT" (one-time), "TRIGGERED" (manual refresh), 
                          or "CONTINUOUS" (auto-refresh every 15+ seconds). Default: "SNAPSHOT"

    Returns:
        True if synced table was created successfully or already exists (when skipping), False otherwise

    Example:
        >>> create_or_update_synced_table(
        ...     source_table="catalog.schema.customers",
        ...     synced_table="catalog.schema.customers_synced",
        ...     lakebase_instance="shared-online-store",
        ...     primary_key=["customer_id"],
        ...     scheduling_policy="SNAPSHOT",
        ...     skip_if_exists=False  # Delete and recreate if exists
        ... )
        True
    """
    if primary_key is None:
        primary_key = ["id"]

    try:
        print(f"Creating synced table: {synced_table}")
        print(f"  Source: {source_table}")
        print(f"  Database instance: {lakebase_instance}")
        print(f"  Primary key: {primary_key}")
        print(f"  Scheduling policy: {scheduling_policy}")

        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.database import (
            SyncedDatabaseTable,
            SyncedTableSpec,
            NewPipelineSpec,
            SyncedTableSchedulingPolicy
        )

        w = WorkspaceClient()

        # Parse catalog and schema from synced table name
        synced_parts = synced_table.split('.')
        if len(synced_parts) != 3:
            raise ValueError(
                f"Synced table name must be fully qualified (catalog.schema.table), got: {synced_table}"
            )
        catalog = synced_parts[0]
        schema = synced_parts[1]
        table = synced_parts[2]
        
        # Validate naming conventions (Postgres requirement)
        # Postgres names must contain only alphanumeric characters and underscores
        import re
        postgres_name_pattern = r'^[A-Za-z0-9_]+$'
        if not re.match(postgres_name_pattern, schema):
            raise ValueError(
                f"Schema name must contain only alphanumeric characters and underscores. "
                f"Got: '{schema}'. Please use a valid Postgres identifier."
            )
        if not re.match(postgres_name_pattern, table):
            raise ValueError(
                f"Table name must contain only alphanumeric characters and underscores. "
                f"Got: '{table}'. Please use a valid Postgres identifier."
            )

        # Enable Change Data Feed only if using TRIGGERED or CONTINUOUS mode
        # SNAPSHOT mode does not require Change Data Feed
        if scheduling_policy.upper() in ["TRIGGERED", "CONTINUOUS"]:
            print(f"  Enabling Change Data Feed on source table (required for {scheduling_policy} mode)...")
            from pyspark.sql import SparkSession
            spark = SparkSession.builder.getOrCreate()
            
            spark.sql(f"""
                ALTER TABLE {source_table}
                SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
            """)
            print(f"  ✓ Change Data Feed enabled")
        else:
            print(f"  Change Data Feed not required for SNAPSHOT mode")

        # Delete existing synced table if not skipping
        if not skip_if_exists:
            print(f"  Checking for existing synced table...")
            if _check_synced_table_exists(synced_table):
                print(f"  Found existing synced table, deleting...")
                try:
                    w.database.delete_synced_database_table(name=synced_table)
                    print(f"  ✓ Deletion request submitted")
                    
                    # Wait for deletion to complete
                    if not _wait_for_synced_table_deletion(synced_table, max_wait_seconds=300):
                        raise Exception(f"Timeout waiting for synced table deletion: {synced_table}")
                    
                except Exception as e:
                    if "not found" not in str(e).lower():
                        raise
                    print(f"  Table already gone during deletion")
            else:
                print(f"  No existing table to delete")

        # Map scheduling policy string to enum
        policy_map = {
            "SNAPSHOT": SyncedTableSchedulingPolicy.SNAPSHOT,
            "TRIGGERED": SyncedTableSchedulingPolicy.TRIGGERED,
            "CONTINUOUS": SyncedTableSchedulingPolicy.CONTINUOUS
        }
        policy_enum = policy_map.get(scheduling_policy.upper(), SyncedTableSchedulingPolicy.SNAPSHOT)

        # Create synced table using the Databricks SDK
        # Using Standard Catalog approach with database_instance_name and logical_database_name
        print(f"  Creating synced table...")
        synced_table_obj = w.database.create_synced_database_table(
            SyncedDatabaseTable(
                name=synced_table,
                database_instance_name=lakebase_instance,
                logical_database_name=catalog,  # Use catalog name as the Postgres database name
                spec=SyncedTableSpec(
                    source_table_full_name=source_table,
                    primary_key_columns=primary_key,
                    scheduling_policy=policy_enum,
                    create_database_objects_if_missing=auto_create_database,
                    new_pipeline_spec=NewPipelineSpec(
                        storage_catalog=catalog,
                        storage_schema=schema
                    )
                )
            )
        )

        print(f"✓ Synced table created successfully: {synced_table}")
        print(f"  Name: {synced_table_obj.name}")
        if hasattr(synced_table_obj, 'data_synchronization_status'):
            print(f"  Status: {synced_table_obj.data_synchronization_status.detailed_state}")

        return True

    except Exception as e:
        error_msg = str(e).lower()
        
        # If table already exists and we're skipping, treat as success
        if skip_if_exists and ("already exists" in error_msg or "already registered" in error_msg):
            print(f"⊙ Synced table already exists, skipping: {synced_table}")
            return True
        
        # Otherwise, it's a real error
        print(f"✗ Error creating synced table: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def create_multiple_synced_tables(
    table_configs: List[dict],
    lakebase_instance: str,
    skip_if_exists: bool = True,
    scheduling_policy: str = "SNAPSHOT"
) -> dict:
    """
    Create multiple synced tables from a list of configurations.

    Args:
        table_configs: List of dictionaries with keys:
            - source_table: Source Delta table (required)
            - synced_table: Synced table name (required)
            - primary_key: Primary key columns (optional, defaults to ["id"])
            - scheduling_policy: Override default scheduling policy per table (optional)
        lakebase_instance: Lakebase instance name
        skip_if_exists: If True, skip creation if synced table already exists. 
                       If False, delete existing tables (wait for deletion), then recreate.
        scheduling_policy: Default sync mode for all tables - "SNAPSHOT", "TRIGGERED", or "CONTINUOUS".
                          Can be overridden per table in table_configs. Default: "SNAPSHOT"

    Returns:
        Dictionary with synced table names as keys and success status as values

    Example:
        >>> configs = [
        ...     {
        ...         "source_table": "catalog.schema.customers",
        ...         "synced_table": "catalog.schema.customers_synced",
        ...         "primary_key": ["customer_id"],
        ...         "scheduling_policy": "SNAPSHOT"  # Optional: override default
        ...     },
        ...     {
        ...         "source_table": "catalog.schema.products",
        ...         "synced_table": "catalog.schema.products_synced",
        ...         "primary_key": ["product_id"]
        ...         # Uses default scheduling_policy
        ...     }
        ... ]
        >>> results = create_multiple_synced_tables(
        ...     configs, 
        ...     "shared-online-store", 
        ...     skip_if_exists=False,
        ...     scheduling_policy="SNAPSHOT"
        ... )
        >>> print(results)
        {'catalog.schema.customers_synced': True, 'catalog.schema.products_synced': True}
    """
    results = {}

    print("=" * 80)
    print(f"Creating {len(table_configs)} synced table(s)")
    print(f"Default scheduling policy: {scheduling_policy}")
    if skip_if_exists:
        print("Mode: Skip if already exists")
    else:
        print("Mode: Recreate all tables")
    print("=" * 80)

    for i, config in enumerate(table_configs, 1):
        print(f"\n[{i}/{len(table_configs)}] Processing: {config['synced_table']}")
        print("-" * 80)

        # Use per-table scheduling policy if specified, otherwise use default
        table_scheduling_policy = config.get('scheduling_policy', scheduling_policy)

        success = create_or_update_synced_table(
            source_table=config['source_table'],
            synced_table=config['synced_table'],
            lakebase_instance=lakebase_instance,
            primary_key=config.get('primary_key', ["id"]),
            skip_if_exists=skip_if_exists,
            scheduling_policy=table_scheduling_policy
        )

        results[config['synced_table']] = success

    print("\n" + "=" * 80)
    print("SYNCED TABLE CREATION SUMMARY")
    print("=" * 80)
    successful = sum(1 for success in results.values() if success)
    failed = len(results) - successful
    print(f"Total: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed tables:")
        for table, success in results.items():
            if not success:
                print(f"  - {table}")

    return results


def delete_synced_table(synced_table: str) -> bool:
    """
    Delete a synced table from Lakebase.

    Args:
        synced_table: Synced table name (fully qualified: catalog.schema.table)

    Returns:
        True if deleted successfully, False otherwise

    Example:
        >>> delete_synced_table("catalog.schema.customers_synced")
        True
    """
    try:
        print(f"Deleting synced table: {synced_table}")

        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()

        w.database.delete_synced_database_table(name=synced_table)
        print(f"✓ Synced table deleted successfully: {synced_table}")
        return True

    except Exception as e:
        print(f"✗ Error deleting synced table: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def get_synced_table_status(synced_table: str) -> Optional[dict]:
    """
    Get the status of a synced table.

    Args:
        synced_table: Synced table name (fully qualified: catalog.schema.table)

    Returns:
        Dictionary with status information, or None if table doesn't exist

    Example:
        >>> status = get_synced_table_status("catalog.schema.customers_synced")
        >>> print(status['detailed_state'])
        'ACTIVE'
    """
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()

        table_info = w.database.get_synced_database_table(name=synced_table)

        status = {
            "name": table_info.name,
            "database_instance": table_info.database_instance_name,
            "source_table": table_info.spec.source_table_full_name if table_info.spec else None,
        }

        if hasattr(table_info, 'data_synchronization_status'):
            sync_status = table_info.data_synchronization_status
            status.update({
                "detailed_state": sync_status.detailed_state,
                "last_sync_time": sync_status.last_sync_time if hasattr(sync_status, 'last_sync_time') else None
            })

        return status

    except Exception as e:
        print(f"Error getting synced table status: {str(e)}")
        return None

