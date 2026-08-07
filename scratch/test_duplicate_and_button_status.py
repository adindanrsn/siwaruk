import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.business import Business
from app.models.laporan_terkirim import LaporanTerkirim

app = create_app()

def test_duplicate_and_status():
    with app.app_context():
        print("=== TEST: DUPLICATE GUARD & BUTTON STATUS DISPLAY ===")

        owner = User.query.filter_by(role='owner').first()
        assert owner is not None
        owner.must_change_password = False
        db.session.commit()

        biz = Business.query.filter_by(owner_id=owner.id).first()
        assert biz is not None

        client = app.test_client()
        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(owner)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(owner.id)
                sess['active_business_id'] = biz.id

            # 1. Post report for 'bulan_ini'
            res1 = client.post('/laporan/kirim-ke-admin', data={'periode': 'bulan_ini'})
            # Note: might be 200 (if first time) or 400 (if already sent in previous test)
            if res1.status_code == 200:
                print("[1] First submission successful!")
            else:
                print(f"[1] First submission status code: {res1.status_code}")

            # 2. Duplicate submission attempt for 'bulan_ini' MUST be blocked with 400
            res2 = client.post('/laporan/kirim-ke-admin', data={'periode': 'bulan_ini'})
            assert res2.status_code == 400
            json2 = res2.get_json()
            assert json2['status'] == 'error'
            print(f"[2] Duplicate submission blocked successfully with 400 Bad Request!")

            # 3. GET /laporan/ (index page) must render '✅ Sudah Dikirim' and status details
            res_index = client.get('/laporan/?periode=bulan_ini')
            assert res_index.status_code == 200
            html = res_index.data.decode('utf-8')

            assert '✅ Sudah Dikirim' in html
            print("[3] Button disabled status ('Sudah Dikirim'): FOUND in HTML")

            assert 'kirimStatusBanner' in html
            assert 'Dikirim:' in html
            print("[4] Submission date & status banner: FOUND in HTML")

        print("\n[SUCCESS] All duplicate submission guards and button status displays passed!")

if __name__ == '__main__':
    test_duplicate_and_status()
