"""
Utilities for creating and managing Lakebase synced tables.

This module provides functions to create synced tables from Delta tables
for low-latency OLTP access in Databricks Apps.
"""

from typing import List, Optional


def create_or_update_synced_table(
    source_table: str,
    synced_table: str,
    lakebase_instance: str,
    primary_key: List[str] = None,
    auto_create_database: bool = True
) -> bool:
    """
    Create or update a synced table in Lakebase for OLTP access.

    This function:
    1. Deletes any existing synced table with the same name
    2. Enables Change Data Feed on the source Delta table
    3. Creates a new synced table with triggered scheduling policy

    Args:
        source_table: Source Delta table name (fully qualified: catalog.schema.table)
        synced_table: Synced table name (fully qualified: catalog.schema.table)
        lakebase_instance: Lakebase instance name (e.g., "shared-online-store")
        primary_key: List of columns that form the primary key. If None, uses ["id"]
        auto_create_database: Whether to create database objects if missing

    Returns:
        True if synced table was created successfully, False otherwise

    Example:
        >>> create_or_update_synced_table(
        ...     source_table="catalog.schema.customers",
        ...     synced_table="catalog.schema.customers_synced",
        ...     lakebase_instance="shared-online-store",
        ...     primary_key=["customer_id"]
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

        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.database import (
            SyncedDatabaseTable,
            SyncedTableSpec,
            NewPipelineSpec,
            SyncedTableSchedulingPolicy
        )

        w = WorkspaceClient()

        # Enable Change Data Feed on source table (required for synced tables)
        print(f"  Enabling Change Data Feed on source table...")
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        
        spark.sql(f"""
            ALTER TABLE {source_table}
            SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
        """)
        print(f"  ✓ Change Data Feed enabled")

        # Delete existing synced table if it exists
        try:
            print(f"  Checking for existing synced table...")
            w.database.delete_synced_database_table(name=synced_table)
            print(f"  ✓ Deleted existing synced table")
        except Exception:
            # Table doesn't exist, which is fine
            print(f"  No existing table to delete")

        # Parse catalog and schema from synced table name
        synced_parts = synced_table.split('.')
        if len(synced_parts) != 3:
            raise ValueError(
                f"Synced table name must be fully qualified (catalog.schema.table), got: {synced_table}"
            )
        catalog = synced_parts[0]
        schema = synced_parts[1]

        # Create synced table using the Databricks SDK
        print(f"  Creating synced table...")
        synced_table_obj = w.database.create_synced_database_table(
            SyncedDatabaseTable(
                name=synced_table,
                database_instance_name=lakebase_instance,
                logical_database_name=f"{catalog}_{schema}",
                spec=SyncedTableSpec(
                    source_table_full_name=source_table,
                    primary_key_columns=primary_key,
                    scheduling_policy=SyncedTableSchedulingPolicy.TRIGGERED,
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
        print(f"✗ Error creating synced table: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def create_multiple_synced_tables(
    table_configs: List[dict],
    lakebase_instance: str
) -> dict:
    """
    Create multiple synced tables from a list of configurations.

    Args:
        table_configs: List of dictionaries with keys:
            - source_table: Source Delta table (required)
            - synced_table: Synced table name (required)
            - primary_key: Primary key columns (optional, defaults to ["id"])
        lakebase_instance: Lakebase instance name

    Returns:
        Dictionary with synced table names as keys and success status as values

    Example:
        >>> configs = [
        ...     {
        ...         "source_table": "catalog.schema.customers",
        ...         "synced_table": "catalog.schema.customers_synced",
        ...         "primary_key": ["customer_id"]
        ...     },
        ...     {
        ...         "source_table": "catalog.schema.products",
        ...         "synced_table": "catalog.schema.products_synced",
        ...         "primary_key": ["product_id"]
        ...     }
        ... ]
        >>> results = create_multiple_synced_tables(configs, "shared-online-store")
        >>> print(results)
        {'catalog.schema.customers_synced': True, 'catalog.schema.products_synced': True}
    """
    results = {}

    print("=" * 80)
    print(f"Creating {len(table_configs)} synced table(s)")
    print("=" * 80)

    for i, config in enumerate(table_configs, 1):
        print(f"\n[{i}/{len(table_configs)}] Processing: {config['synced_table']}")
        print("-" * 80)

        success = create_or_update_synced_table(
            source_table=config['source_table'],
            synced_table=config['synced_table'],
            lakebase_instance=lakebase_instance,
            primary_key=config.get('primary_key', ["id"])
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

