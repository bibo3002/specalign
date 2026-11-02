-- SpecAlign SQLite adapter: canonical schema introspection (read-only).
-- SQLite keeps the exact DDL in sqlite_master, so one row per object is enough: kind | tbl | name | detail.
-- Replace the table list with the spec's tables. Columns and constraints live inside the table's CREATE statement.
SELECT 'table' AS kind, name AS tbl, name AS name, sql AS detail
FROM sqlite_master WHERE type = 'table' AND name IN ('files', 'file_locks')
UNION ALL
SELECT 'index', tbl_name, name, COALESCE(sql, 'auto index')
FROM sqlite_master WHERE type = 'index' AND tbl_name IN ('files', 'file_locks')
UNION ALL
SELECT 'trigger', tbl_name, name, sql
FROM sqlite_master WHERE type = 'trigger' AND tbl_name IN ('files', 'file_locks')
ORDER BY 1, 2, 3;
