#!/usr/bin/env python3
"""
Database Comparator - Compare Generated vs Original Database

This script compares the generated database (from DXF) with the original
database (from manual 3D modeling) to validate template accuracy.

Usage:
    python database_comparator.py [generated_db] [original_db] [output_report]

Example:
    python database_comparator.py \
        Generated_Terminal1.db \
        ~/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \
        validation_report.md
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class DatabaseComparator:
    """Compare two databases with identical schemas."""

    def __init__(self, generated_db: str, original_db: str):
        self.generated_db = Path(generated_db)
        self.original_db = Path(original_db)

        if not self.generated_db.exists():
            raise FileNotFoundError(f"Generated database not found: {self.generated_db}")
        if not self.original_db.exists():
            raise FileNotFoundError(f"Original database not found: {self.original_db}")

        self.generated_conn = sqlite3.connect(str(self.generated_db))
        self.generated_conn.row_factory = sqlite3.Row

        self.original_conn = sqlite3.connect(str(self.original_db))
        self.original_conn.row_factory = sqlite3.Row

    def get_element_counts(self, conn: sqlite3.Connection) -> Dict[str, int]:
        """Get element counts by discipline."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT discipline, COUNT(*) as count
            FROM elements_meta
            GROUP BY discipline
            ORDER BY discipline
        """)
        return {row['discipline']: row['count'] for row in cursor.fetchall()}

    def get_ifc_class_distribution(self, conn: sqlite3.Connection, discipline: str = None) -> Dict[str, int]:
        """Get IFC class distribution, optionally filtered by discipline."""
        cursor = conn.cursor()
        if discipline:
            cursor.execute("""
                SELECT ifc_class, COUNT(*) as count
                FROM elements_meta
                WHERE discipline = ?
                GROUP BY ifc_class
                ORDER BY count DESC
            """, (discipline,))
        else:
            cursor.execute("""
                SELECT ifc_class, COUNT(*) as count
                FROM elements_meta
                GROUP BY ifc_class
                ORDER BY count DESC
            """)
        return {row['ifc_class']: row['count'] for row in cursor.fetchall()}

    def get_total_elements(self, conn: sqlite3.Connection) -> int:
        """Get total element count."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM elements_meta")
        return cursor.fetchone()['count']

    def calculate_accuracy(self, generated: int, original: int) -> float:
        """Calculate accuracy percentage."""
        if original == 0:
            return 0.0
        return (generated / original) * 100.0

    def compare_disciplines(self) -> Dict[str, Dict]:
        """Compare element counts by discipline."""
        generated_counts = self.get_element_counts(self.generated_conn)
        original_counts = self.get_element_counts(self.original_conn)

        all_disciplines = set(generated_counts.keys()) | set(original_counts.keys())

        results = {}
        for discipline in sorted(all_disciplines):
            gen_count = generated_counts.get(discipline, 0)
            orig_count = original_counts.get(discipline, 0)
            accuracy = self.calculate_accuracy(gen_count, orig_count)

            results[discipline] = {
                'generated': gen_count,
                'original': orig_count,
                'accuracy': accuracy,
                'missing': orig_count - gen_count,
                'extra': max(0, gen_count - orig_count)
            }

        return results

    def compare_ifc_classes(self, discipline: str = None) -> Dict[str, Dict]:
        """Compare IFC class distribution."""
        generated_dist = self.get_ifc_class_distribution(self.generated_conn, discipline)
        original_dist = self.get_ifc_class_distribution(self.original_conn, discipline)

        all_classes = set(generated_dist.keys()) | set(original_dist.keys())

        results = {}
        for ifc_class in sorted(all_classes):
            gen_count = generated_dist.get(ifc_class, 0)
            orig_count = original_dist.get(ifc_class, 0)
            accuracy = self.calculate_accuracy(gen_count, orig_count)

            results[ifc_class] = {
                'generated': gen_count,
                'original': orig_count,
                'accuracy': accuracy,
                'missing': orig_count - gen_count
            }

        return results

    def generate_report(self, output_file: str = None):
        """Generate validation report."""
        report_lines = []

        def add_line(line: str = ""):
            report_lines.append(line)

        # Header
        add_line("=" * 80)
        add_line("DATABASE COMPARISON REPORT")
        add_line("=" * 80)
        add_line()
        add_line(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        add_line()
        add_line(f"Generated Database: {self.generated_db}")
        add_line(f"Original Database:  {self.original_db}")
        add_line()

        # Overall statistics
        add_line("=" * 80)
        add_line("OVERALL STATISTICS")
        add_line("=" * 80)
        add_line()

        gen_total = self.get_total_elements(self.generated_conn)
        orig_total = self.get_total_elements(self.original_conn)
        total_accuracy = self.calculate_accuracy(gen_total, orig_total)

        add_line(f"Total Elements (Generated): {gen_total:,}")
        add_line(f"Total Elements (Original):  {orig_total:,}")
        add_line(f"Overall Accuracy:           {total_accuracy:.1f}%")
        add_line()

        # Discipline comparison
        add_line("=" * 80)
        add_line("COMPARISON BY DISCIPLINE")
        add_line("=" * 80)
        add_line()

        discipline_results = self.compare_disciplines()

        add_line(f"{'Discipline':<12} {'Generated':>10} {'Original':>10} {'Accuracy':>10} {'Missing':>10} {'Status':<10}")
        add_line("-" * 80)

        for discipline, data in discipline_results.items():
            accuracy = data['accuracy']
            status = "✓ PASS" if accuracy >= 70 else "✗ FAIL"
            add_line(f"{discipline:<12} {data['generated']:>10,} {data['original']:>10,} {accuracy:>9.1f}% {data['missing']:>10,} {status:<10}")

        add_line()

        # Detailed IFC class comparison for each discipline
        add_line("=" * 80)
        add_line("DETAILED IFC CLASS COMPARISON")
        add_line("=" * 80)
        add_line()

        for discipline in sorted(discipline_results.keys()):
            add_line(f"Discipline: {discipline}")
            add_line("-" * 80)
            add_line()

            ifc_results = self.compare_ifc_classes(discipline)

            if not ifc_results:
                add_line("  (No elements in this discipline)")
                add_line()
                continue

            add_line(f"  {'IFC Class':<40} {'Generated':>10} {'Original':>10} {'Accuracy':>10}")
            add_line("  " + "-" * 76)

            for ifc_class, data in sorted(ifc_results.items(), key=lambda x: x[1]['original'], reverse=True):
                if data['original'] > 0:  # Only show classes that exist in original
                    add_line(f"  {ifc_class:<40} {data['generated']:>10,} {data['original']:>10,} {data['accuracy']:>9.1f}%")

            add_line()

        # Success criteria
        add_line("=" * 80)
        add_line("SUCCESS CRITERIA EVALUATION")
        add_line("=" * 80)
        add_line()

        criteria = [
            ("Overall accuracy > 70%", total_accuracy >= 70, f"{total_accuracy:.1f}%"),
            ("All disciplines present", len(discipline_results) >= 8, f"{len(discipline_results)}/8 disciplines"),
        ]

        discipline_accuracy_avg = sum(d['accuracy'] for d in discipline_results.values()) / len(discipline_results)
        criteria.append(("Average discipline accuracy > 70%", discipline_accuracy_avg >= 70, f"{discipline_accuracy_avg:.1f}%"))

        for criterion, passed, value in criteria:
            status = "✓ PASS" if passed else "✗ FAIL"
            add_line(f"{status} {criterion:<40} {value}")

        add_line()

        # Overall assessment
        all_passed = all(passed for _, passed, _ in criteria)

        add_line("=" * 80)
        if all_passed:
            add_line("✓ VALIDATION SUCCESSFUL - Templates work!")
        else:
            add_line("✗ VALIDATION FAILED - Templates need refinement")
        add_line("=" * 80)
        add_line()

        # Generate report
        report = "\n".join(report_lines)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"Report saved to: {output_file}")

        print(report)

        return report

    def close(self):
        """Close database connections."""
        self.generated_conn.close()
        self.original_conn.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python database_comparator.py <generated_db> <original_db> [output_report]")
        print()
        print("Example:")
        print("  python database_comparator.py \\")
        print("      Generated_Terminal1.db \\")
        print("      ~/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \\")
        print("      validation_report.md")
        sys.exit(1)

    generated_db = sys.argv[1]
    original_db = sys.argv[2]
    output_report = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        comparator = DatabaseComparator(generated_db, original_db)
        comparator.generate_report(output_report)
        comparator.close()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
