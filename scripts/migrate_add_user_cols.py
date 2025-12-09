#!/usr/bin/env python3
"""
Migration helper: ensure `users` table has `phone` and `address` columns.

Usage:
  python3 scripts/migrate_add_user_cols.py --db kazprice.db --backup

Options:
  --db PATH      Path to SQLite database file (default: kazprice.db)
  --backup       Make a timestamped backup copy before applying changes

Behavior:
- If the `users` table does not exist, the script exits with a message.
- For each missing column (`phone`, `address`) the script runs
  `ALTER TABLE users ADD COLUMN <name> TEXT;` and commits.
- The operation is idempotent: running multiple times is safe.
"""

import argparse
import os
import sqlite3
import shutil
import datetime
import sys


def parse_args():
    p = argparse.ArgumentParser(description='Ensure users table has phone and address columns')
    p.add_argument('--db', default='kazprice.db', help='Path to sqlite database file')
    p.add_argument('--backup', action='store_true', help='Create a backup copy before migrating')
    return p.parse_args()


def backup_db(db_path):
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return None
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, dest)
    print(f"Backup created: {dest}")
    return dest


def ensure_columns(db_path):
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check if users table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        print('Table `users` does not exist in the database. Run db_init.sql to create schema first.')
        conn.close()
        return 2

    # Get column names
    cur.execute('PRAGMA table_info(users)')
    cols = [r[1] for r in cur.fetchall()]
    print('Existing users columns:', cols)

    to_add = []
    if 'phone' not in cols:
        to_add.append('phone')
    if 'address' not in cols:
        to_add.append('address')

    if not to_add:
        print('No columns to add. Schema is up-to-date.')
        conn.close()
        return 0

    for col in to_add:
        sql = f'ALTER TABLE users ADD COLUMN {col} TEXT'
        print('Executing:', sql)
        try:
            cur.execute(sql)
        except sqlite3.DatabaseError as e:
            print('Error executing:', sql)
            print(e)
            conn.close()
            return 3

    conn.commit()
    print('Migration applied. Added columns:', to_add)
    conn.close()
    return 0


def main():
    args = parse_args()
    db = args.db

    if args.backup:
        bk = backup_db(db)
        if not bk:
            print('Backup failed or skipped. Aborting migration.')
            sys.exit(1)

    code = ensure_columns(db)
    sys.exit(code)


if __name__ == '__main__':
    main()
