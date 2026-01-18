import sqlite3
from pathlib import Path
p = Path('app.db')
print('db path', p.resolve())
if not p.exists():
    print('app.db not found')
    raise SystemExit(1)
conn = sqlite3.connect(str(p))
conn.row_factory = sqlite3.Row
print('\naccounts:')
for r in conn.execute('SELECT id,name,api_key,created_at FROM accounts').fetchall():
    print(dict(r))
print('\nstudents:')
for r in conn.execute('SELECT id,account_id,display_name,grade,created_at FROM students').fetchall():
    print(dict(r))
conn.close()
