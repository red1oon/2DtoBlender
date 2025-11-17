-- Fix Material Mode: Copy material_rgba from material_assignments to elements_meta
--
-- PROBLEM: Bonsai Material mode reads from elements_meta.material_rgba
--          but 2Dto3D populates material_assignments table instead
--
-- SOLUTION: Copy rgba values to elements_meta.material_rgba column

BEGIN TRANSACTION;

-- Update elements_meta.material_rgba from material_assignments
UPDATE elements_meta
SET material_rgba = (
    SELECT ma.rgba
    FROM material_assignments ma
    WHERE ma.guid = elements_meta.guid
    LIMIT 1
)
WHERE EXISTS (
    SELECT 1
    FROM material_assignments ma
    WHERE ma.guid = elements_meta.guid
);

-- Verify the fix
SELECT
    'After fix:' as status,
    COUNT(*) as total_elements,
    COUNT(material_rgba) as with_rgba,
    ROUND(COUNT(material_rgba) * 100.0 / COUNT(*), 1) as percentage
FROM elements_meta;

COMMIT;
