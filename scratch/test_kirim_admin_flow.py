import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.business import Business
from app.models.laporan_terkirim import LaporanTerkirim

app = create_app()

def test_kirim_admin():
    with app.app_context():
        print("=== E2E TEST: KIRIM KE ADMIN -> LAPORAN MASUK ===")

        # 1. Get or create Owner user & Business
        owner = User.query.filter_by(role='owner').first()
        assert owner is not None, "Owner user not found"
        owner.must_change_password = False
        db.session.commit()

        biz = Business.query.filter_by(owner_id=owner.id).first()
        if not biz:
            biz = Business(
                owner_id=owner.id,
                business_name="Warung Test Kirim",
                owner_name=owner.full_name,
                bidang_usaha="Kuliner"
            )
            db.session.add(biz)
            db.session.commit()

        # 2. Login as Owner
        client = app.test_client()
        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(owner)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(owner.id)
                sess['active_business_id'] = biz.id

            # Post Kirim ke Admin
            res_post = client.post('/laporan/kirim-ke-admin', data={
                'periode': 'bulan_ini'
            })

            print(f"[1] POST /laporan/kirim-ke-admin response code: {res_post.status_code}")
            json_data = res_post.get_json()
            assert res_post.status_code == 200
            assert json_data['status'] == 'success'
            report_id = json_data['id']

        # 3. Verify record in Database
        record = db.session.get(LaporanTerkirim, report_id)
        assert record is not None, "Record not found in DB!"
        print(f"[2] Record found in DB: ID={record.id}, Business='{record.business.business_name}', Status='{record.status}'")

        # 4. Login as Admin
        admin = User.query.filter_by(role='admin').first()
        assert admin is not None, "Admin user not found"
        admin.must_change_password = False
        db.session.commit()

        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(admin)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)

            # Get Admin Laporan Masuk
            res_admin_list = client.get('/admin/laporan-masuk')
            assert res_admin_list.status_code == 200
            print(f"[3] GET /admin/laporan-masuk response code: {res_admin_list.status_code}")
            assert str(record.periode_label).encode('utf-8') in res_admin_list.data or record.business.business_name.encode('utf-8') in res_admin_list.data
            print("    Submitted report IS present in Admin Laporan Masuk HTML!")

            # Get Detail Laporan
            res_detail = client.get(f'/admin/laporan-masuk/{report_id}/detail')
            assert res_detail.status_code == 200
            print(f"[4] GET /admin/laporan-masuk/{report_id}/detail response code: {res_detail.status_code}")

            # Get PDF Laporan
            res_pdf = client.get(f'/admin/laporan-masuk/{report_id}/pdf')
            assert res_pdf.status_code == 200
            print(f"[5] GET /admin/laporan-masuk/{report_id}/pdf response code: {res_pdf.status_code}")

            # Update Status to 'Sudah Ditinjau'
            res_update = client.post(f'/admin/laporan-masuk/{report_id}/update-status', data={
                'status': 'Sudah Ditinjau'
            }, follow_redirects=True)
            assert res_update.status_code == 200
            db.session.refresh(record)
            assert record.status == 'Sudah Ditinjau'
            print(f"[6] Updated status in DB to: '{record.status}'")

        print("\n[SUCCESS] Entire Kirim ke Admin -> Laporan Masuk E2E flow is fully working!")

if __name__ == '__main__':
    test_kirim_admin()
