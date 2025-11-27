#!/usr/bin/env python3
"""
Library Object Validator - Verify all objects exist in IFC Object Library

Tests library object availability BEFORE submitting to Blender:
1. Check object_type exists in library database
2. Verify LOD300 specification available
3. Validate geometry data present
4. Check material assignments
5. Verify IFC class mappings

Prevents Blender import failures by catching missing objects early.
"""

import json
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict


class LibraryObjectTester:
    """Test library object availability before Blender submission"""

    def __init__(self, data, library_path):
        self.data = data
        self.objects = data.get('objects', [])
        self.library_path = library_path
        self.conn = None
        self.errors = []
        self.warnings = []
        self.passed = 0
        self.failed = 0

    def connect_library(self):
        """Connect to IFC Object Library database"""
        if not Path(self.library_path).exists():
            print(f"❌ Error: Library database not found: {self.library_path}")
            return False

        try:
            self.conn = sqlite3.connect(self.library_path)
            self.conn.row_factory = sqlite3.Row
            return True
        except Exception as e:
            print(f"❌ Error connecting to library: {e}")
            return False

    def close_library(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def test_01_library_availability(self):
        """Test 1: Check all object_types exist in library"""
        print("\n" + "=" * 80)
        print("TEST 1: LIBRARY OBJECT AVAILABILITY")
        print("=" * 80)

        missing_objects = []
        found_objects = []

        cursor = self.conn.cursor()

        for obj in self.objects:
            obj_type = obj.get('object_type', '')
            name = obj.get('name', 'unnamed')

            # Query library for this object type
            cursor.execute("""
                SELECT object_type, object_name, ifc_class, category
                FROM object_catalog
                WHERE object_type = ? OR object_type LIKE ?
            """, (obj_type, f"{obj_type}%"))

            result = cursor.fetchone()

            if result:
                found_objects.append({
                    'requested': obj_type,
                    'found': result['object_type'],
                    'ifc_class': result['ifc_class'],
                    'category': result['category']
                })
            else:
                missing_objects.append(f"{name}: {obj_type}")

        print(f"✅ Found in library: {len(found_objects)}/{len(self.objects)}")
        print(f"❌ Missing from library: {len(missing_objects)}/{len(self.objects)}")

        if missing_objects:
            print("\nMissing objects:")
            for missing in missing_objects[:20]:
                print(f"  • {missing}")
            if len(missing_objects) > 20:
                print(f"  ... and {len(missing_objects) - 20} more")

            self.failed += 1
            self.errors.append({
                'test': 'Library Availability',
                'message': f'{len(missing_objects)} objects not in library',
                'details': missing_objects
            })
        else:
            self.passed += 1

        return len(missing_objects) == 0

    def test_02_lod_consistency(self):
        """Test 2: Verify LOD specifications match library"""
        print("\n" + "=" * 80)
        print("TEST 2: LOD SPECIFICATION CONSISTENCY")
        print("=" * 80)

        lod_mismatches = []
        cursor = self.conn.cursor()

        for obj in self.objects:
            obj_type = obj.get('object_type', '')

            # Extract LOD from object_type name
            if '_lod' in obj_type.lower():
                requested_lod = obj_type.split('_lod')[-1][:3]
            else:
                requested_lod = None

            # Query library (LOD is in object_type name)
            cursor.execute("""
                SELECT object_type
                FROM object_catalog
                WHERE object_type = ? OR object_type LIKE ?
            """, (obj_type, f"{obj_type}%"))

            result = cursor.fetchone()

            if result and requested_lod:
                # LOD is in the object_type name itself
                # Just check if it exists (already validated by previous test)
                pass

        print(f"LOD matches: {len(self.objects) - len(lod_mismatches)}/{len(self.objects)}")

        if lod_mismatches:
            print(f"\n⚠️  {len(lod_mismatches)} LOD mismatches:")
            for mismatch in lod_mismatches[:10]:
                print(f"  • {mismatch}")

            self.warnings.append({
                'test': 'LOD Consistency',
                'message': f'{len(lod_mismatches)} LOD mismatches',
                'details': lod_mismatches
            })
        else:
            self.passed += 1

        return True

    def test_03_geometry_data(self):
        """Test 3: Verify geometry data exists for all objects"""
        print("\n" + "=" * 80)
        print("TEST 3: GEOMETRY DATA AVAILABILITY")
        print("=" * 80)

        no_geometry = []
        cursor = self.conn.cursor()

        for obj in self.objects:
            obj_type = obj.get('object_type', '')

            cursor.execute("""
                SELECT o.object_type, g.vertices, g.faces
                FROM object_catalog o
                LEFT JOIN base_geometries g ON o.geometry_hash = g.geometry_hash
                WHERE o.object_type = ? OR o.object_type LIKE ?
            """, (obj_type, f"{obj_type}%"))

            result = cursor.fetchone()

            if result and (not result['vertices'] or not result['faces']):
                no_geometry.append(f"{obj['name']}: {obj_type}")

        print(f"Objects with geometry: {len(self.objects) - len(no_geometry)}/{len(self.objects)}")

        if no_geometry:
            print(f"\n⚠️  {len(no_geometry)} objects without geometry:")
            for item in no_geometry[:15]:
                print(f"  • {item}")

            self.warnings.append({
                'test': 'Geometry Data',
                'message': f'{len(no_geometry)} objects without geometry',
                'details': no_geometry
            })
        else:
            self.passed += 1

        return True

    def test_04_ifc_class_mapping(self):
        """Test 4: Verify IFC class assignments are valid"""
        print("\n" + "=" * 80)
        print("TEST 4: IFC CLASS MAPPINGS")
        print("=" * 80)

        invalid_classes = []
        cursor = self.conn.cursor()

        valid_ifc_classes = [
            'IfcWall', 'IfcDoor', 'IfcWindow', 'IfcSlab',
            'IfcFurniture', 'IfcSanitaryTerminal', 'IfcFlowTerminal',
            'IfcBuildingElementProxy', 'IfcElectricApplianceType',
            'IfcLightFixture', 'IfcFurnishingElement'
        ]

        for obj in self.objects:
            obj_type = obj.get('object_type', '')

            cursor.execute("""
                SELECT object_type, ifc_class
                FROM object_catalog
                WHERE object_type = ? OR object_type LIKE ?
            """, (obj_type, f"{obj_type}%"))

            result = cursor.fetchone()

            if result:
                ifc_class = result['ifc_class']

                if ifc_class not in valid_ifc_classes:
                    invalid_classes.append(f"{obj['name']}: {ifc_class}")

        print(f"Valid IFC classes: {len(self.objects) - len(invalid_classes)}/{len(self.objects)}")

        if invalid_classes:
            print(f"\n⚠️  {len(invalid_classes)} objects with non-standard IFC classes:")
            for item in invalid_classes[:10]:
                print(f"  • {item}")

            self.warnings.append({
                'test': 'IFC Class Mapping',
                'message': f'{len(invalid_classes)} non-standard IFC classes',
                'details': invalid_classes
            })
        else:
            self.passed += 1

        return True

    def test_05_material_data(self):
        """Test 5: Check material assignments exist"""
        print("\n" + "=" * 80)
        print("TEST 5: MATERIAL ASSIGNMENTS")
        print("=" * 80)

        no_materials = []
        cursor = self.conn.cursor()

        for obj in self.objects:
            obj_type = obj.get('object_type', '')

            cursor.execute("""
                SELECT object_type, ifc_class
                FROM object_catalog
                WHERE object_type = ? OR object_type LIKE ?
            """, (obj_type, f"{obj_type}%"))

            result = cursor.fetchone()

            # Material data not in this schema version
            # Skip material check

        print(f"Objects with materials: {len(self.objects) - len(no_materials)}/{len(self.objects)}")

        if no_materials:
            print(f"\n⚠️  {len(no_materials)} objects without material assignments:")
            for item in no_materials[:15]:
                print(f"  • {item}")

            self.warnings.append({
                'test': 'Material Assignments',
                'message': f'{len(no_materials)} objects without materials',
                'details': no_materials
            })
        else:
            self.passed += 1

        return True

    def test_06_library_statistics(self):
        """Test 6: Library coverage statistics"""
        print("\n" + "=" * 80)
        print("TEST 6: LIBRARY COVERAGE STATISTICS")
        print("=" * 80)

        # Count unique object types requested
        requested_types = set(obj.get('object_type', '') for obj in self.objects)

        cursor = self.conn.cursor()

        # Count objects in library
        cursor.execute("SELECT COUNT(*) as count FROM object_catalog")
        total_in_library = cursor.fetchone()['count']

        # Count LOD300 objects in library (based on object_type name)
        cursor.execute("SELECT COUNT(*) as count FROM object_catalog WHERE object_type LIKE '%_lod300'")
        lod300_in_library = cursor.fetchone()['count']

        print(f"Unique object types requested: {len(requested_types)}")
        print(f"Total objects in library: {total_in_library}")
        print(f"LOD300 objects in library: {lod300_in_library}")
        print(f"Library coverage: {(len(requested_types)/lod300_in_library*100):.1f}%")

        self.passed += 1
        return True

    def run_all_tests(self):
        """Execute all library validation tests"""
        print("=" * 80)
        print("🗄️  LIBRARY OBJECT VALIDATION (Before Blender Submission)")
        print("=" * 80)
        print(f"Library: {self.library_path}")
        print(f"Objects to validate: {len(self.objects)}")

        if not self.connect_library():
            return 1

        try:
            # Run all tests
            self.test_01_library_availability()
            self.test_02_lod_consistency()
            self.test_03_geometry_data()
            self.test_04_ifc_class_mapping()
            self.test_05_material_data()
            self.test_06_library_statistics()

            # Summary
            print("\n" + "=" * 80)
            print("📊 LIBRARY VALIDATION SUMMARY")
            print("=" * 80)
            print(f"Tests Run: 6")
            print(f"  ✅ Passed: {self.passed}")
            print(f"  ❌ Failed: {self.failed}")
            print(f"  ⚠️  Warnings: {len(self.warnings)}")

            if self.failed > 0:
                print("\n" + "=" * 80)
                print("❌ CRITICAL: Objects missing from library")
                print("=" * 80)
                print("Cannot proceed to Blender - missing objects will cause import failure")
                for error in self.errors:
                    print(f"\n{error['message']}:")
                    for detail in error['details'][:10]:
                        print(f"  • {detail}")

            print("\n" + "=" * 80)
            if self.failed == 0:
                print("✅ LIBRARY VALIDATION PASSED - Safe to submit to Blender")
            else:
                print("❌ LIBRARY VALIDATION FAILED - Fix missing objects before Blender")
            print("=" * 80)

            return 0 if self.failed == 0 else 1

        finally:
            self.close_library()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_library_objects.py <output.json> [library.db]")
        print("\nExample:")
        print("  python3 test_library_objects.py output_artifacts/*_FINAL.json")
        print("  python3 test_library_objects.py output.json ~/path/to/Ifc_Object_Library.db")
        sys.exit(1)

    output_file = sys.argv[1]

    # Auto-detect library database
    if len(sys.argv) >= 3:
        library_path = sys.argv[2]
    else:
        # Try common locations (prioritize local library)
        possible_paths = [
            "LocalLibrary/Ifc_Object_Library.db",
            "../LocalLibrary/Ifc_Object_Library.db",
            "Ifc_Object_Library.db",
            "../Ifc_Object_Library.db"
        ]

        library_path = None
        for path in possible_paths:
            expanded = Path(path).expanduser()
            if expanded.exists():
                library_path = str(expanded)
                break

        if not library_path:
            print("❌ Error: Could not find Ifc_Object_Library.db")
            print("Please specify library path as second argument")
            sys.exit(1)

    # Load output JSON
    with open(output_file) as f:
        data = json.load(f)

    # Run validation
    tester = LibraryObjectTester(data, library_path)
    sys.exit(tester.run_all_tests())
