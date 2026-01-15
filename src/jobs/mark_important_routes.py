"""
Mark important routes based on major hub airports.

Routes between major hubs are flagged as important for daily flight data sync.
This limits API calls while covering high-value routes.
"""

from config.env_loader import engine
from sqlalchemy import text

# Major hub airports by region
HUBS = {
    # Lufthansa Group hubs (primary)
    "lufthansa": ["FRA", "MUC", "ZRH", "VIE", "BRU"],

    # Other major European hubs
    "europe": ["LHR", "CDG", "AMS", "MAD", "BCN", "FCO", "IST", "DUB", "CPH", "OSL", "ARN"],

    # Major US hubs (transatlantic routes)
    "usa": ["JFK", "LAX", "ORD", "ATL", "DFW", "MIA", "SFO", "BOS", "IAD", "EWR"],

    # Major Asian hubs (long-haul routes)
    "asia": ["NRT", "HND", "PEK", "PVG", "HKG", "SIN", "ICN", "BKK", "DXB", "DOH"],
}


def get_all_hubs() -> list:
    """Get flat list of all hub airports."""
    all_hubs = []
    for region_hubs in HUBS.values():
        all_hubs.extend(region_hubs)
    return list(set(all_hubs))


def mark_important_routes(dry_run: bool = False) -> dict:
    """
    Mark routes between major hubs as important.

    Args:
        dry_run: If True, only count affected routes without updating.

    Returns:
        Dict with stats: total_hubs, routes_marked, routes_already_important
    """
    hubs = get_all_hubs()
    hubs_tuple = tuple(hubs)

    print(f"[INFO] Using {len(hubs)} hub airports across {len(HUBS)} regions")

    with engine.connect() as conn:
        # Count routes that would be marked
        count_query = text("""
            SELECT COUNT(*) as cnt FROM routes
            WHERE departure_airport IN :hubs
              AND arrival_airport IN :hubs
              AND important = FALSE
        """)
        result = conn.execute(count_query, {"hubs": hubs_tuple})
        to_mark = result.scalar()

        # Count already important
        already_query = text("""
            SELECT COUNT(*) as cnt FROM routes
            WHERE important = TRUE
        """)
        result = conn.execute(already_query)
        already_important = result.scalar()

        if dry_run:
            print(f"[DRY RUN] Would mark {to_mark} routes as important")
            print(f"[DRY RUN] Already important: {already_important}")
        else:
            # Update routes
            update_query = text("""
                UPDATE routes
                SET important = TRUE
                WHERE departure_airport IN :hubs
                  AND arrival_airport IN :hubs
                  AND important = FALSE
            """)
            result = conn.execute(update_query, {"hubs": hubs_tuple})
            conn.commit()

            print(f"[SUCCESS] Marked {result.rowcount} routes as important")
            print(f"[INFO] Previously important: {already_important}")
            print(f"[INFO] Total important now: {already_important + result.rowcount}")

    return {
        "total_hubs": len(hubs),
        "routes_marked": to_mark if dry_run else result.rowcount,
        "routes_already_important": already_important,
    }


def reset_important_routes() -> int:
    """Reset all routes to not important (for re-running)."""
    with engine.connect() as conn:
        result = conn.execute(text("UPDATE routes SET important = FALSE WHERE important = TRUE"))
        conn.commit()
        print(f"[INFO] Reset {result.rowcount} routes to not important")
        return result.rowcount


def get_important_routes_stats() -> dict:
    """Get statistics about important routes."""
    with engine.connect() as conn:
        # Total routes
        total = conn.execute(text("SELECT COUNT(*) FROM routes")).scalar()

        # Important routes
        important = conn.execute(text("SELECT COUNT(*) FROM routes WHERE important = TRUE")).scalar()

        # Routes by region (approximate based on departure airport)
        hubs = get_all_hubs()
        hub_routes = conn.execute(
            text("""
                SELECT COUNT(*) FROM routes
                WHERE important = TRUE
                  AND departure_airport IN :hubs
            """),
            {"hubs": tuple(hubs)}
        ).scalar()

    return {
        "total_routes": total,
        "important_routes": important,
        "percentage": round(100 * important / total, 2) if total > 0 else 0,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mark important routes between major hubs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--reset", action="store_true", help="Reset all routes to not important")
    parser.add_argument("--stats", action="store_true", help="Show current statistics")
    args = parser.parse_args()

    if args.stats:
        stats = get_important_routes_stats()
        print(f"Total routes: {stats['total_routes']}")
        print(f"Important routes: {stats['important_routes']} ({stats['percentage']}%)")
    elif args.reset:
        reset_important_routes()
    else:
        mark_important_routes(dry_run=args.dry_run)
