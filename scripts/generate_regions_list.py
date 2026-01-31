#!/usr/bin/env python3
"""
Generate REGIONS_FULL_LIST.md from the cleaned database.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "regions.db"
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "REGIONS_FULL_LIST.md"


def generate_markdown(conn):
    """Generate markdown documentation from database."""
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM regions")
    total_count = cursor.fetchone()[0]

    # Get all regions sorted by sido -> sigungu -> emd
    cursor.execute("""
        SELECT code, sido, sigungu, emd, lat, lon, nx, ny, elevation, is_coastal, is_east_coast, is_west_coast, is_south_coast
        FROM regions
        ORDER BY sido, sigungu, emd
    """)
    regions = cursor.fetchall()

    # Build markdown content
    lines = []
    lines.append("# Weather Lens - Complete Regions List")
    lines.append("")
    lines.append(f"**Total Regions: {total_count:,}**")
    lines.append("")
    lines.append("All regions in the database, sorted by administrative hierarchy (Sido → Sigungu → Emd).")
    lines.append("")
    lines.append("## Data Fields")
    lines.append("")
    lines.append("- **Code**: Official region code")
    lines.append("- **Sido**: Province/Metropolitan city")
    lines.append("- **Sigungu**: City/County/District")
    lines.append("- **Emd**: Township/Neighborhood")
    lines.append("- **Lat/Lon**: Geographic coordinates (WGS84)")
    lines.append("- **NX/NY**: Korea Meteorological Administration grid coordinates")
    lines.append("- **Elev**: Elevation in meters")
    lines.append("- **Coastal Flags**: EC=East Coast, WC=West Coast, SC=South Coast")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by sido
    current_sido = None
    current_sigungu = None

    for code, sido, sigungu, emd, lat, lon, nx, ny, elevation, is_coastal, is_east_coast, is_west_coast, is_south_coast in regions:
        # New sido section
        if sido != current_sido:
            if current_sido is not None:
                lines.append("")
            lines.append(f"## {sido}")
            lines.append("")
            current_sido = sido
            current_sigungu = None

        # New sigungu section
        if sigungu != current_sigungu:
            if current_sigungu is not None:
                lines.append("")
            lines.append(f"### {sigungu}")
            lines.append("")
            lines.append("| Code | Emd | Lat | Lon | NX | NY | Elev | Coastal |")
            lines.append("|------|-----|-----|-----|----|----|------|---------|")
            current_sigungu = sigungu

        # Coastal flags
        coastal_flags = []
        if is_east_coast:
            coastal_flags.append("EC")
        if is_west_coast:
            coastal_flags.append("WC")
        if is_south_coast:
            coastal_flags.append("SC")
        coastal = ",".join(coastal_flags) if coastal_flags else ""

        # Format row
        lines.append(f"| {code} | {emd} | {lat:.4f} | {lon:.4f} | {nx} | {ny} | {elevation:.1f} | {coastal} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"**Total: {total_count:,} regions**")
    lines.append("")
    lines.append("*Generated from regions.db*")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main generation process."""
    print("Generating REGIONS_FULL_LIST.md...")

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return 1

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    try:
        # Generate markdown
        markdown = generate_markdown(conn)

        # Write to file
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(markdown, encoding='utf-8')

        print(f"✓ Generated {OUTPUT_PATH}")
        print(f"  File size: {len(markdown):,} bytes")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())
