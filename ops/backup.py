"""Consistent SQLite backup; run on the server, never copy an active DB file."""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

source=Path(sys.argv[1] if len(sys.argv)>1 else '/opt/trading-control-room/data/control_room.db')
folder=source.parent/'backups'
folder.mkdir(parents=True,exist_ok=True)
target=folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.db')
with sqlite3.connect(f'file:{source}?mode=ro',uri=True) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
for old in sorted(folder.glob('*.db'))[:-14]:
    old.unlink()
print(target)
