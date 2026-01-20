#!/usr/bin/env python3
"""
Interactive Database Transfer Script for DST Airlines
Transfers data between local and production Supabase PostgreSQL databases.
Handles table dependencies, foreign keys, and provides various sync modes.
"""

import os
import sys
from datetime import datetime
from urllib.parse import quote_plus
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

# Add parent to path for config imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Table dependency order (for correct insertion sequence)
TABLE_ORDER = [
    "countries",      # no deps
    "aircrafts",      # no deps
    "airlines",       # no deps
    "cities",         # depends on countries
    "airports",       # depends on cities, countries
    "routes",         # depends on airports
    "bts_flight_history",       # no FK deps (but part of flight data)
    "lufthansa_flight_history", # depends on routes, airlines, aircrafts
    "historical_flights",       # depends on all flight tables + airports, airlines, aircrafts
    "weather_hourly_cache",     # no deps
    "owm_api_quota",            # no deps
]

# Flight-related tables (main focus)
FLIGHT_TABLES = [
    "routes",
    "bts_flight_history",
    "lufthansa_flight_history",
    "historical_flights",
]

# Reference tables needed for flight data integrity
REFERENCE_TABLES = [
    "countries",
    "aircrafts",
    "airlines",
    "cities",
    "airports",
]

FK_VIOLATION_CODE = "23503"

# Logging setup
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
CURRENT_LOG_FILE = None

def log_error(context: str, error: Exception, row_data: dict = None):
    """Log error to file, creating it if needed"""
    global CURRENT_LOG_FILE
    
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        
    if CURRENT_LOG_FILE is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        CURRENT_LOG_FILE = os.path.join(LOG_DIR, f"transfer_errors_{timestamp}.log")
        
    try:
        with open(CURRENT_LOG_FILE, "a") as f:
            ts = datetime.now().isoformat()
            f.write(f"[{ts}] {context}\n")
            f.write(f"Error: {str(error)}\n")
            if row_data:
                f.write(f"Row data: {row_data}\n")
            f.write("-" * 50 + "\n")
    except Exception as e:
        print(c(f"  ⚠ Failed to write to log file: {e}", Colors.RED))


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def c(text: str, color: str) -> str:
    """Colorize text for terminal output"""
    return f"{color}{text}{Colors.END}"


def build_db_url(host: str, port: int, db: str, user: str, password: str) -> str:
    """Build PostgreSQL connection URL with encoded password"""
    return f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{db}"


def get_env_config():
    """Load config from .env file"""
    from config.env_loader import load_env
    load_env()
    return {
        'host': os.getenv("PG_HOST", "").strip("'\""),
        'port': int(os.getenv("PG_PORT", 5432)),
        'db': os.getenv("PG_DB", "postgres"),
        'user': os.getenv("PG_USER", "").strip("'\""),
        'password': os.getenv("PG_PASSWORD", "").strip("'\""),
    }


def prompt_db_config(name: str, defaults: dict = None) -> dict:
    """Interactive prompt for database configuration"""
    print(c(f"\n{'='*50}", Colors.HEADER))
    print(c(f"  Configure {name} Database", Colors.BOLD))
    print(c(f"{'='*50}", Colors.HEADER))

    defaults = defaults or {}

    host = input(f"  Host [{defaults.get('host', '')}]: ").strip() or defaults.get('host', '')
    port = input(f"  Port [{defaults.get('port', 5432)}]: ").strip() or defaults.get('port', 5432)
    db = input(f"  Database [{defaults.get('db', 'postgres')}]: ").strip() or defaults.get('db', 'postgres')
    user = input(f"  User [{defaults.get('user', '')}]: ").strip() or defaults.get('user', '')
    password = input(f"  Password: ").strip() or defaults.get('password', '')

    return {
        'host': host.strip("'\""),
        'port': int(port),
        'db': db,
        'user': user.strip("'\""),
        'password': password.strip("'\""),
    }


def test_connection(config: dict, name: str) -> Optional[object]:
    """Test database connection and return engine if successful"""
    url = build_db_url(**config)
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(c(f"  ✓ {name} connection OK", Colors.GREEN))
        return engine
    except Exception as e:
        print(c(f"  ✗ {name} connection FAILED: {e}", Colors.RED))
        return None


def get_table_counts(engine, tables: list = None) -> dict:
    """Get row counts for tables"""
    tables = tables or TABLE_ORDER
    counts = {}
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table in tables:
        if table in existing_tables:
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    counts[table] = result.scalar() or 0
            except Exception:
                counts[table] = -1  # Error reading
        else:
            counts[table] = None  # Table doesn't exist
    return counts


def display_comparison(src_counts: dict, dst_counts: dict):
    """Display side-by-side comparison of table counts"""
    print(c("\n" + "="*70, Colors.HEADER))
    print(c("  Table Comparison (Source → Destination)", Colors.BOLD))
    print(c("="*70, Colors.HEADER))
    print(f"  {'Table':<30} {'Source':>12} {'Dest':>12} {'Diff':>10}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*10}")

    for table in TABLE_ORDER:
        src = src_counts.get(table)
        dst = dst_counts.get(table)

        src_str = str(src) if src is not None else "N/A"
        dst_str = str(dst) if dst is not None else "N/A"

        if src is not None and dst is not None:
            diff = src - dst
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            color = Colors.GREEN if diff > 0 else (Colors.YELLOW if diff == 0 else Colors.RED)
        else:
            diff_str = "-"
            color = Colors.YELLOW

        # Highlight flight tables
        if table in FLIGHT_TABLES:
            table_display = c(f"► {table}", Colors.CYAN)
        else:
            table_display = f"  {table}"

        print(f"  {table_display:<40} {src_str:>12} {dst_str:>12} {c(diff_str, color):>20}")

    print()


def select_tables_interactive(src_counts: dict) -> list:
    """Interactive table selection menu"""
    print(c("\n" + "="*50, Colors.HEADER))
    print(c("  Select Transfer Mode", Colors.BOLD))
    print(c("="*50, Colors.HEADER))
    print("""
  [1] Flight data only (routes, flight history tables)
      - Includes reference data for FK integrity

  [2] All flight + reference data
      - countries, airlines, aircrafts, cities, airports
      - routes, all flight history tables

  [3] Full database sync
      - All tables including cache

  [4] Custom selection
      - Choose specific tables

  [0] Cancel
""")

    choice = input("  Select option [1]: ").strip() or "1"

    if choice == "0":
        return []
    elif choice == "1":
        # Flight data + needed references
        return REFERENCE_TABLES + FLIGHT_TABLES
    elif choice == "2":
        return REFERENCE_TABLES + FLIGHT_TABLES
    elif choice == "3":
        return TABLE_ORDER
    elif choice == "4":
        return select_custom_tables(src_counts)
    else:
        print(c("  Invalid option, using flight data only", Colors.YELLOW))
        return REFERENCE_TABLES + FLIGHT_TABLES


def select_custom_tables(src_counts: dict) -> list:
    """Custom table selection"""
    print(c("\n  Available tables:", Colors.CYAN))
    for i, table in enumerate(TABLE_ORDER, 1):
        count = src_counts.get(table, 0)
        marker = "►" if table in FLIGHT_TABLES else " "
        print(f"    {marker}[{i:2}] {table:<30} ({count:,} rows)")

    print("\n  Enter table numbers (comma-separated) or 'all':")
    selection = input("  > ").strip().lower()

    if selection == "all":
        return TABLE_ORDER

    try:
        indices = [int(x.strip()) - 1 for x in selection.split(",")]
        selected = [TABLE_ORDER[i] for i in indices if 0 <= i < len(TABLE_ORDER)]

        # Auto-add dependencies
        selected = resolve_dependencies(selected)
        return selected
    except (ValueError, IndexError):
        print(c("  Invalid selection", Colors.RED))
        return []


def resolve_dependencies(tables: list) -> list:
    """Ensure dependency tables are included and ordered correctly"""
    deps = {
        "cities": ["countries"],
        "airports": ["countries", "cities"],
        "routes": ["airports"],
        "lufthansa_flight_history": ["routes", "airlines", "aircrafts"],
        "historical_flights": ["airports", "airlines", "aircrafts", "bts_flight_history", "lufthansa_flight_history"],
    }

    resolved = set(tables)

    # Add all dependencies recursively
    changed = True
    while changed:
        changed = False
        for table in list(resolved):
            for dep in deps.get(table, []):
                if dep not in resolved:
                    resolved.add(dep)
                    changed = True

    # Return in correct order
    return [t for t in TABLE_ORDER if t in resolved]


def select_sync_mode() -> str:
    """Select synchronization mode"""
    print(c("\n" + "="*50, Colors.HEADER))
    print(c("  Select Sync Mode", Colors.BOLD))
    print(c("="*50, Colors.HEADER))
    print("""
  [1] Upsert (recommended)
      - Insert new records, skip existing (by primary key)

  [2] Replace
      - Truncate destination table, insert all from source
      - WARNING: Deletes existing data in destination!

  [3] Append only
      - Only insert, may fail on duplicates

  [0] Cancel
""")

    choice = input("  Select mode [1]: ").strip() or "1"

    modes = {"1": "upsert", "2": "replace", "3": "append", "0": "cancel"}
    return modes.get(choice, "upsert")


def select_date_filter() -> Optional[dict]:
    """Optional date filter for flight history tables"""
    print(c("\n" + "="*50, Colors.HEADER))
    print(c("  Date Filter (for flight history)", Colors.BOLD))
    print(c("="*50, Colors.HEADER))
    print("""
  [1] All data (no filter)
  [2] Last 7 days
  [3] Last 30 days
  [4] Last 90 days
  [5] Custom date range
  [0] Cancel
""")

    choice = input("  Select option [1]: ").strip() or "1"

    if choice == "0":
        return {"cancel": True}
    elif choice == "1":
        return None
    elif choice == "2":
        return {"days": 7}
    elif choice == "3":
        return {"days": 30}
    elif choice == "4":
        return {"days": 90}
    elif choice == "5":
        start = input("  Start date (YYYY-MM-DD): ").strip()
        end = input("  End date (YYYY-MM-DD) [today]: ").strip() or datetime.now().strftime("%Y-%m-%d")
        return {"start": start, "end": end}

    return None


def build_date_filter(table: str, date_filter: dict) -> str:
    """Build SQL WHERE clause for date filtering"""
    if not date_filter:
        return ""

    date_columns = {
        "lufthansa_flight_history": "departure_schedule_date",
        "weather_hourly_cache": "hour_local",
    }

    col = date_columns.get(table)
    if not col:
        return ""

    if "days" in date_filter:
        return f"WHERE {col} >= CURRENT_DATE - INTERVAL '{date_filter['days']} days'"
    elif "start" in date_filter:
        return f"WHERE {col} >= '{date_filter['start']}' AND {col} <= '{date_filter['end']}'"

    return ""


def get_primary_keys(engine, table: str) -> list:
    """Get primary key columns for a table"""
    inspector = inspect(engine)
    pk_info = inspector.get_pk_constraint(table)
    return pk_info.get("constrained_columns", [])


def transfer_table(src_engine, dst_engine, table: str, mode: str,
                   date_filter: dict = None, batch_size: int = 1000) -> dict:
    """Transfer data for a single table"""
    stats = {"inserted": 0, "skipped": 0, "errors": 0}

    # Build query with optional date filter
    where_clause = build_date_filter(table, date_filter)
    query = f"SELECT * FROM {table} {where_clause}"

    print(c(f"\n  Reading from source: {table}...", Colors.CYAN))
    try:
        df = pd.read_sql(query, src_engine)
    except Exception as e:
        msg = f"Error reading source table {table}"
        print(c(f"    ✗ {msg}: {e}", Colors.RED))
        log_error(msg, e)
        stats["errors"] = 1
        return stats

    total_rows = len(df)
    if total_rows == 0:
        print(c(f"    No data to transfer", Colors.YELLOW))
        return stats

    print(f"    Found {total_rows:,} rows")

    if mode == "replace":
        # Truncate destination first
        print(c(f"    Truncating destination table...", Colors.YELLOW))
        try:
            with dst_engine.begin() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception as e:
            msg = f"Error truncating table {table}"
            print(c(f"    ✗ {msg}: {e}", Colors.RED))
            log_error(msg, e)
            stats["errors"] = 1
            return stats

    # Prepare for insertion
    metadata = MetaData()
    try:
        dst_table = Table(table, metadata, autoload_with=dst_engine)
    except Exception as e:
        msg = f"Table {table} not found in destination"
        print(c(f"    ✗ {msg}: {e}", Colors.RED))
        log_error(msg, e)
        stats["errors"] = 1
        return stats

    pk_cols = get_primary_keys(dst_engine, table)

    # Process in batches
    print(f"    Inserting in batches of {batch_size}...")

    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        batch = df.iloc[start:end].to_dict(orient="records")

        try:
            if mode == "upsert" and pk_cols:
                # Use INSERT ... ON CONFLICT DO NOTHING
                stmt = pg_insert(dst_table).values(batch).on_conflict_do_nothing(
                    index_elements=pk_cols
                )
            else:
                stmt = pg_insert(dst_table).values(batch).on_conflict_do_nothing()

            with dst_engine.begin() as conn:
                result = conn.execute(stmt)
                stats["inserted"] += result.rowcount if hasattr(result, 'rowcount') else len(batch)

            # Progress indicator
            pct = int((end / total_rows) * 100)
            print(f"\r    Progress: {pct:3}% ({end:,}/{total_rows:,})", end="", flush=True)

        except IntegrityError as e:
            # Fallback to row-by-row insertion
            print(f"\n    Batch failed, falling back to row-by-row...")
            for row in batch:
                try:
                    stmt = pg_insert(dst_table).values(row).on_conflict_do_nothing()
                    with dst_engine.begin() as conn:
                        conn.execute(stmt)
                    stats["inserted"] += 1
                except IntegrityError:
                    stats["skipped"] += 1
                except Exception as row_err:
                    stats["errors"] += 1
                    log_error(f"Error inserting row in {table}", row_err, row)
        except Exception as e:
            msg = f"Batch error in {table}"
            print(c(f"\n    ✗ {msg}: {e}", Colors.RED))
            log_error(msg, e)
            stats["errors"] += 1

    print()  # Newline after progress
    return stats


def run_transfer(src_engine, dst_engine, tables: list, mode: str, date_filter: dict = None):
    """Execute the full transfer process"""
    print(c("\n" + "="*70, Colors.HEADER))
    print(c("  Starting Transfer", Colors.BOLD))
    print(c("="*70, Colors.HEADER))
    print(f"  Tables: {len(tables)}")
    print(f"  Mode: {mode}")
    print(f"  Date filter: {date_filter or 'None'}")

    # Confirmation
    confirm = input(c("\n  Proceed with transfer? [y/N]: ", Colors.YELLOW)).strip().lower()
    if confirm != "y":
        print(c("  Transfer cancelled", Colors.RED))
        return

    all_stats = {}
    start_time = datetime.now()

    for table in tables:
        print(c(f"\n{'─'*50}", Colors.BLUE))
        print(c(f"  Table: {table}", Colors.BOLD))

        stats = transfer_table(src_engine, dst_engine, table, mode, date_filter)
        all_stats[table] = stats

        print(f"    Inserted: {stats['inserted']:,}")
        print(f"    Skipped: {stats['skipped']:,}")
        if stats['errors']:
            print(c(f"    Errors: {stats['errors']}", Colors.RED))

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print(c("\n" + "="*70, Colors.HEADER))
    print(c("  Transfer Summary", Colors.BOLD))
    print(c("="*70, Colors.HEADER))

    total_inserted = sum(s['inserted'] for s in all_stats.values())
    total_skipped = sum(s['skipped'] for s in all_stats.values())
    total_errors = sum(s['errors'] for s in all_stats.values())

    print(f"  Duration: {elapsed:.1f} seconds")
    print(f"  Total inserted: {total_inserted:,}")
    print(f"  Total skipped: {total_skipped:,}")
    
    if total_errors > 0:
        print(c(f"  Total errors: {total_errors}", Colors.RED))
        if CURRENT_LOG_FILE:
            print(c(f"  Details logged to: {CURRENT_LOG_FILE}", Colors.YELLOW))
    else:
        print(c(f"  Total errors: {total_errors}", Colors.GREEN))

    # Final counts
    print(c("\n  Final destination counts:", Colors.CYAN))
    final_counts = get_table_counts(dst_engine, tables)
    for table in tables:
        count = final_counts.get(table, 0)
        print(f"    {table:<30} {count:>10,} rows")


def main():
    """Main interactive script"""
    print(c("""
╔══════════════════════════════════════════════════════════════════╗
║           DST Airlines Database Transfer Tool                    ║
║         Transfer data between PostgreSQL databases               ║
╚══════════════════════════════════════════════════════════════════╝
    """, Colors.HEADER))

    # Load default config
    try:
        default_config = get_env_config()
        print(c("  Loaded config from .env file", Colors.GREEN))
    except Exception:
        default_config = {}
        print(c("  No .env config found, manual entry required", Colors.YELLOW))

    # Configure source database
    print(c("\n  Configure SOURCE database (where to read FROM):", Colors.BOLD))
    use_env = input("  Use .env config as source? [Y/n]: ").strip().lower()

    if use_env != "n" and default_config:
        src_config = default_config
        print(c(f"    Using: {src_config['host']}", Colors.CYAN))
    else:
        src_config = prompt_db_config("Source")

    # Configure destination database
    print(c("\n  Configure DESTINATION database (where to write TO):", Colors.BOLD))
    dst_config = prompt_db_config("Destination")

    # Test connections
    print(c("\n  Testing connections...", Colors.CYAN))
    src_engine = test_connection(src_config, "Source")
    dst_engine = test_connection(dst_config, "Destination")

    if not src_engine or not dst_engine:
        print(c("\n  Cannot proceed without both connections", Colors.RED))
        return

    # Get and display table counts
    print(c("\n  Analyzing databases...", Colors.CYAN))
    src_counts = get_table_counts(src_engine)
    dst_counts = get_table_counts(dst_engine)

    display_comparison(src_counts, dst_counts)

    # Select tables
    tables = select_tables_interactive(src_counts)
    if not tables:
        print(c("\n  No tables selected, exiting", Colors.YELLOW))
        return

    print(c(f"\n  Selected tables ({len(tables)}):", Colors.CYAN))
    for t in tables:
        print(f"    • {t}")

    # Select sync mode
    mode = select_sync_mode()
    if mode == "cancel":
        print(c("\n  Cancelled", Colors.YELLOW))
        return

    # Date filter for flight history
    date_filter = None
    if any(t in tables for t in ["lufthansa_flight_history", "weather_hourly_cache"]):
        date_filter = select_date_filter()
        if date_filter and date_filter.get("cancel"):
            print(c("\n  Cancelled", Colors.YELLOW))
            return

    # Execute transfer
    run_transfer(src_engine, dst_engine, tables, mode, date_filter)

    print(c("\n  Done!\n", Colors.GREEN))


if __name__ == "__main__":
    main()
