-- SpecAlign Postgres adapter: canonical schema introspection (read-only).
-- Replace the array literal with the spec's tables (the §0 Card `tables` label / §5). Run through the DB tool and
-- save the result rows as a JSON array; `python -m specalign schema fingerprint --input rows.json` hashes them.
-- One row per column, constraint, index and trigger: kind | tbl | name | detail
WITH t(tbl) AS (SELECT unnest(ARRAY['files','file_locks']::text[]))
SELECT 'column' AS kind, c.table_name AS tbl, c.column_name AS name,
       concat_ws(' ', c.data_type, CASE WHEN c.is_nullable = 'NO' THEN 'not null' ELSE 'null' END,
                 COALESCE('default ' || c.column_default, ''),
                 COALESCE('len ' || c.character_maximum_length::text, '')) AS detail
FROM information_schema.columns c JOIN t ON t.tbl = c.table_name WHERE c.table_schema = 'public'
UNION ALL
SELECT 'constraint', cl.relname, con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con JOIN pg_class cl ON cl.oid = con.conrelid JOIN pg_namespace n ON n.oid = cl.relnamespace
JOIN t ON t.tbl = cl.relname WHERE n.nspname = 'public'
UNION ALL
SELECT 'index', i.tablename, i.indexname, i.indexdef
FROM pg_indexes i JOIN t ON t.tbl = i.tablename WHERE i.schemaname = 'public'
UNION ALL
SELECT 'trigger', cl.relname, tg.tgname, pg_get_triggerdef(tg.oid)
FROM pg_trigger tg JOIN pg_class cl ON cl.oid = tg.tgrelid JOIN t ON t.tbl = cl.relname WHERE NOT tg.tgisinternal
ORDER BY 1, 2, 3;
