-- SpecAlign MySQL / MariaDB adapter: canonical schema introspection (read-only).
-- Replace the table list in each IN (...) with the spec's tables. Output rows: kind | tbl | name | detail
-- (the same shape as adapters/postgres/introspection.sql, so `schema fingerprint` works unchanged).
SELECT 'column' AS kind, c.TABLE_NAME AS tbl, c.COLUMN_NAME AS name,
       CONCAT_WS(' ', c.COLUMN_TYPE, IF(c.IS_NULLABLE = 'NO', 'not null', 'null'),
                 IFNULL(CONCAT('default ', c.COLUMN_DEFAULT), ''), c.EXTRA) AS detail
FROM information_schema.COLUMNS c
WHERE c.TABLE_SCHEMA = DATABASE() AND c.TABLE_NAME IN ('files', 'file_locks')
UNION ALL
SELECT 'constraint', tc.TABLE_NAME, tc.CONSTRAINT_NAME,
       CONCAT(tc.CONSTRAINT_TYPE, ' ', IFNULL((SELECT GROUP_CONCAT(k.COLUMN_NAME ORDER BY k.ORDINAL_POSITION)
                                               FROM information_schema.KEY_COLUMN_USAGE k
                                               WHERE k.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
                                                 AND k.TABLE_NAME = tc.TABLE_NAME
                                                 AND k.CONSTRAINT_NAME = tc.CONSTRAINT_NAME), ''))
FROM information_schema.TABLE_CONSTRAINTS tc
WHERE tc.CONSTRAINT_SCHEMA = DATABASE() AND tc.TABLE_NAME IN ('files', 'file_locks')
UNION ALL
SELECT 'index', s.TABLE_NAME, s.INDEX_NAME,
       CONCAT(IF(s.NON_UNIQUE = 0, 'unique ', ''), GROUP_CONCAT(s.COLUMN_NAME ORDER BY s.SEQ_IN_INDEX))
FROM information_schema.STATISTICS s
WHERE s.TABLE_SCHEMA = DATABASE() AND s.TABLE_NAME IN ('files', 'file_locks')
GROUP BY s.TABLE_NAME, s.INDEX_NAME, s.NON_UNIQUE
UNION ALL
SELECT 'trigger', t.EVENT_OBJECT_TABLE, t.TRIGGER_NAME,
       CONCAT(t.ACTION_TIMING, ' ', t.EVENT_MANIPULATION, ' ', t.ACTION_STATEMENT)
FROM information_schema.TRIGGERS t
WHERE t.TRIGGER_SCHEMA = DATABASE() AND t.EVENT_OBJECT_TABLE IN ('files', 'file_locks')
ORDER BY 1, 2, 3;
