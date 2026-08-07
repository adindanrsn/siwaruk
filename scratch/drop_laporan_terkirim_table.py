import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db

app = create_app()

def drop_table():
    with app.app_context():
        print("=== STEP 1: DROPPING TABEL laporan_terkirim ===")
        with db.engine.connect() as conn:
            conn.execute(db.text("DROP TABLE IF EXISTS laporan_terkirim CASCADE;"))
            conn.commit()
        print("[SUCCESS] Tabel 'laporan_terkirim' berhasil dihapus dari database PostgreSQL!")

if __name__ == '__main__':
    drop_table()
