"""
Database access for template library
Connects to template_library.db and retrieves template information
"""
import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class TemplateDatabase:
    """Interface to template_library.db"""

    def __init__(self, db_path: str):
        """
        Initialize connection to template database

        Args:
            db_path: Path to template_library.db file
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Template database not found: {db_path}")

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.cursor = self.conn.cursor()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def get_all_templates(self) -> List[Dict]:
        """Get all templates from database"""
        query = """
            SELECT
                template_id,
                template_name,
                ifc_class,
                category,
                instance_count,
                description
            FROM element_templates
            ORDER BY category, ifc_class
        """
        self.cursor.execute(query)
        return [dict(row) for row in self.cursor.fetchall()]

    def get_templates_by_category(self, category: str) -> List[Dict]:
        """Get templates for a specific category (discipline)"""
        query = """
            SELECT
                template_id,
                template_name,
                ifc_class,
                instance_count,
                description
            FROM element_templates
            WHERE category = ?
            ORDER BY ifc_class
        """
        self.cursor.execute(query, (category,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """Get detailed template information"""
        query = """
            SELECT *
            FROM element_templates
            WHERE template_id = ?
        """
        self.cursor.execute(query, (template_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_template_parameters(self, template_id: str) -> List[Dict]:
        """Get parameters for a template"""
        query = """
            SELECT
                param_name,
                param_type,
                avg_value,
                value_range_min,
                value_range_max,
                common_values,
                required
            FROM template_parameters
            WHERE template_id = ?
        """
        self.cursor.execute(query, (template_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_spatial_offsets(self, template_id: str) -> Dict:
        """Get spatial offset information for a template (placeholder - schema doesn't have z_height)"""
        # Note: Current schema doesn't have spatial offset columns
        # This would need to be added in a future version
        # For now, return defaults
        return {"z_offset": 0.0, "z_stddev": 0.0}

    def get_categories(self) -> List[str]:
        """Get list of all categories (disciplines) in database"""
        query = """
            SELECT DISTINCT category
            FROM element_templates
            ORDER BY category
        """
        self.cursor.execute(query)
        return [row["category"] for row in self.cursor.fetchall()]

    def get_furniture_templates(self) -> List[Dict]:
        """Get all furniture templates (IFC class contains 'Furniture')"""
        query = """
            SELECT
                template_id,
                template_name,
                ifc_class,
                instance_count
            FROM element_templates
            WHERE ifc_class LIKE '%Furniture%' OR ifc_class LIKE '%Furnishing%'
            ORDER BY instance_count DESC
        """
        self.cursor.execute(query)
        return [dict(row) for row in self.cursor.fetchall()]

    def search_templates(self, search_term: str) -> List[Dict]:
        """Search templates by name or IFC class"""
        query = """
            SELECT
                template_id,
                template_name,
                ifc_class,
                category,
                instance_count
            FROM element_templates
            WHERE
                template_name LIKE ? OR
                ifc_class LIKE ? OR
                description LIKE ?
            ORDER BY instance_count DESC
        """
        pattern = f"%{search_term}%"
        self.cursor.execute(query, (pattern, pattern, pattern))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_statistics(self) -> Dict:
        """Get overall template library statistics"""
        query_total = "SELECT COUNT(*) as total FROM element_templates"
        query_by_category = """
            SELECT category, COUNT(*) as count
            FROM element_templates
            GROUP BY category
        """
        query_total_instances = """
            SELECT SUM(instance_count) as total
            FROM element_templates
        """

        self.cursor.execute(query_total)
        total = self.cursor.fetchone()["total"]

        self.cursor.execute(query_by_category)
        by_category = {row["category"]: row["count"] for row in self.cursor.fetchall()}

        self.cursor.execute(query_total_instances)
        total_instances = self.cursor.fetchone()["total"]

        return {
            "total_templates": total,
            "by_category": by_category,
            "total_instances": total_instances if total_instances else 0
        }

    def get_mep_templates(self) -> List[Dict]:
        """Get all MEP templates (ACMV, ELEC, FP, SP, CW, LPG, etc.)"""
        mep_categories = ['ACMV', 'Electrical', 'Fire_Protection', 'Sprinkler', 'Chilled_Water', 'LPG']
        query = """
            SELECT
                template_id,
                template_name,
                ifc_class,
                category,
                instance_count
            FROM element_templates
            WHERE category IN ({})
            ORDER BY category, instance_count DESC
        """.format(','.join('?' * len(mep_categories)))

        self.cursor.execute(query, mep_categories)
        return [dict(row) for row in self.cursor.fetchall()]

    def get_template_for_space_type(self, space_type: str) -> List[Dict]:
        """
        Get recommended templates for a given space type
        (This is a heuristic-based mapping)
        """
        # Mapping of space types to relevant templates
        space_mappings = {
            "waiting_area": ["Furniture", "Bench", "Seating"],
            "restaurant": ["Furniture", "Table", "Chair"],
            "office": ["Furniture", "Desk", "Chair", "Workstation"],
            "toilet": ["Plumbing", "Sanitary"],
            "retail": ["Furniture", "Counter", "Display"],
            "warehouse": ["Storage"],
            "parking": ["Equipment"]
        }

        keywords = space_mappings.get(space_type.lower(), [])
        if not keywords:
            return []

        # Build query with multiple LIKE conditions
        conditions = " OR ".join(["ifc_class LIKE ?" for _ in keywords])
        query = f"""
            SELECT
                template_id,
                template_name,
                ifc_class,
                category,
                instance_count
            FROM element_templates
            WHERE {conditions}
            ORDER BY instance_count DESC
            LIMIT 10
        """

        patterns = [f"%{kw}%" for kw in keywords]
        self.cursor.execute(query, patterns)
        return [dict(row) for row in self.cursor.fetchall()]


def get_default_template_db_path() -> str:
    """Get default path to template database"""
    # Assumes this file is in TemplateConfigurator/database/
    configurator_dir = Path(__file__).parent.parent
    template_db = configurator_dir.parent / "Terminal1_Project" / "Templates" / "terminal_base_v1.0" / "template_library.db"
    return str(template_db)


# Example usage
if __name__ == "__main__":
    db_path = get_default_template_db_path()
    print(f"Looking for database at: {db_path}")

    if Path(db_path).exists():
        with TemplateDatabase(db_path) as db:
            stats = db.get_statistics()
            print(f"\nTemplate Library Statistics:")
            print(f"  Total templates: {stats['total_templates']}")
            print(f"  Total instances: {stats['total_instances']}")
            print(f"\nBy category:")
            for cat, count in stats['by_category'].items():
                print(f"    {cat}: {count} templates")

            print(f"\nFurniture templates:")
            furniture = db.get_furniture_templates()
            for f in furniture[:5]:
                print(f"  - {f['template_name']}: {f['instance_count']} instances")
    else:
        print(f"Database not found at: {db_path}")
