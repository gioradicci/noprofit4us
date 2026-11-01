# Database migrations

This project has no migration framework: tables are created with
`Base.metadata.create_all()` only when `FORCE_DB_SETUP=true`. Scripts in this
folder are therefore **manual, one-off SQL** to be run against an existing
database (PostgreSQL / Supabase).

## 2026-10-31 — `stock_movements.loan_id`

Links each `LOAN`, `LOAN_RETURN` and `LOAN_DELIVERY` movement to the
`gadget_loans` row it belongs to. Required by the per-gadget movements timeline.

### Apply order

The backend maps the new column, and SQLAlchemy selects every mapped column, so
the schema change must land **before** the new backend is deployed.

1. **Schema** (required, blocking):
   `2026_10_31_add_loan_id_to_stock_movements.sql`
   - Adds `loan_id INTEGER NULL` with `ON DELETE SET NULL`, plus the index
     `ix_stock_movements_loan_id`.
   - Rollback statements are at the bottom of the file.
2. **Dry run** (read-only, recommended):
   `2026_10_31_backfill_stock_movement_loan_ids_dry_run.sql`
   - Shows how many rows are already linked, the best `LOAN` candidate for each
     unlinked row, and the movements that will stay unlinked.
   - Contains only `SELECT` statements: it writes nothing.
3. **Deploy** the backend containing the `StockMovement.loan_id` mapping.
4. **Backfill**:
   `2026_10_31_backfill_stock_movement_loan_ids.sql`
   - Idempotent `DO` block; only rows with `loan_id IS NULL` are touched.
   - Ends with linked/unlinked counts, the manual review list and a capacity
     sanity check.

### Important notes

- **New databases**: `create_all()` already creates the column and the index.
  Do not run the DDL script against a fresh database.
- **SQLite (local development)**: `DO` blocks are not supported. Recreate the
  local database (or run the two `ALTER TABLE` / `CREATE INDEX` statements noted
  in the DDL file) and skip the backfill: a disposable dev database does not
  need historical correlation.
- **Unrecoverable cases**: when the same assignee received the same gadget in
  multiple loans, historical returns cannot be attributed with certainty. The
  backfill leaves those rows `NULL`; the timeline reports them as
  `heuristic`/`none` instead of guessing.
- **Rollback**: the backfill rollback (`SET loan_id = NULL`) is at the bottom of
  the backfill file; the schema rollback is at the bottom of the DDL file.
