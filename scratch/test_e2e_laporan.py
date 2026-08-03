import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.business import Business
from app.models.laporan_terkirim import LaporanTerkirim

app = create_app()

def run_e2e_test():
    with app.app_context():
        print("=== RUNNING E2E REPORT SUBMISSION & ADMIN MANAGEMENT TEST ===")

        # Find owner user and admin user
        owner = User.query.filter_by(role='owner').first()
        admin = User.query.filter_by(role='admin').first()

        if not owner:
            print("ERROR: No owner user found in DB")
            return
        if not admin:
            print("ERROR: No admin user found in DB")
            return

        # Find active business for owner
        biz = Business.query.filter_by(owner_id=owner.id).first()
        if not biz:
            print("ERROR: No business found for owner")
            return

        print(f"Owner: {owner.username} (ID: {owner.id})")
        print(f"Business: {biz.business_name} (ID: {biz.id})")
        print(f"Admin: {admin.username} (ID: {admin.id})")

        client = app.test_client()

        # 1. Login as owner
        with client.session_transaction() as sess:
            sess['_user_id'] = str(owner.id)
            sess['_fresh'] = True
            sess['active_business_id'] = biz.id

        # 2. POST /laporan/kirim-ke-admin
        res = client.post('/laporan/kirim-ke-admin', data={
            'periode': 'bulan_ini',
            'start_date': '2026-08-01',
            'end_date': '2026-08-31'
        })

        print(f"\n[1] Kirim ke Admin Status Code: {res.status_code}")
        data = res.get_json()
        print(f"[1] Response Data: {data}")

        assert res.status_code == 200
        assert data['status'] == 'success'
        assert 'wa_url' in data
        assert 'Laporan' in data['message']

        laporan_id = data['id']
        record = LaporanTerkirim.query.get(laporan_id)
        assert record is not None
        assert record.business_id == biz.id
        assert record.sender_id == owner.id
        assert record.status == 'Belum Ditinjau'
        print(f"[2] DB Record created successfully: ID {record.id}, Status: {record.status}")

        # Check file exists on disk
        full_pdf_path = os.path.join(app.instance_path, record.file_path)
        assert os.path.exists(full_pdf_path)
        print(f"[3] PDF File saved on disk: {full_pdf_path} ({os.path.getsize(full_pdf_path)} bytes)")

        # 3. Login as Admin properly using Flask-Login
        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(admin)

            # Re-set session in client context
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True

            # 4. GET /admin/laporan-masuk
            res_list = client.get('/admin/laporan-masuk')
            print(f"\n[4] Admin Laporan Masuk List Code: {res_list.status_code}")
            assert res_list.status_code == 200
            assert biz.business_name.encode('utf-8') in res_list.data

            # 5. GET /admin/laporan-masuk/<id>/detail
            res_detail = client.get(f'/admin/laporan-masuk/{laporan_id}/detail')
            print(f"[5] Admin Detail Laporan Code: {res_detail.status_code}")
            assert res_detail.status_code == 200
            assert biz.business_name.encode('utf-8') in res_detail.data

            # 6. GET /admin/laporan-masuk/<id>/pdf
            res_pdf = client.get(f'/admin/laporan-masuk/{laporan_id}/pdf')
            print(f"[6] Admin PDF View Code: {res_pdf.status_code}, Content-Type: {res_pdf.content_type}")
            assert res_pdf.status_code == 200
            assert 'application/pdf' in res_pdf.content_type

            # 7. POST /admin/laporan-masuk/<id>/update-status -> 'Sudah Ditinjau'
            res_update = client.post(f'/admin/laporan-masuk/{laporan_id}/update-status', data={
                'status': 'Sudah Ditinjau'
            })
            print(f"[7] Update Status Code: {res_update.status_code}")
            record_updated = db.session.get(LaporanTerkirim, laporan_id)
            assert record_updated.status == 'Sudah Ditinjau'
            print(f"[7] Updated DB Record Status: {record_updated.status}")

        print("\n=== ALL E2E TESTS PASSED SUCCESSFULLY! ===")

if __name__ == '__main__':
    run_e2e_test()
