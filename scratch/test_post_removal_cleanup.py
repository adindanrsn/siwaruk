import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.business import Business

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

def run_tests():
    print("=== GLOBAL VERIFICATION TEST AFTER FEATURE REMOVAL ===")
    with app.app_context():
        owner = User.query.filter_by(role='owner').first()
        admin = User.query.filter_by(role='admin').first()

        if not owner or not admin:
            print("[SKIP] Database users missing for testing.")
            return

        # Set passwords for test login
        owner.set_password('password123')
        owner.must_change_password = False
        admin.set_password('password123')
        admin.must_change_password = False
        db.session.commit()

        print(f"Testing with Owner: {owner.username}, Admin: {admin.username}")

        # 1. Test Owner Flow
        with app.test_client() as client:
            # Login Page GET
            res_login_page = client.get('/auth/login')
            assert res_login_page.status_code == 200, f"Login GET failed: {res_login_page.status_code}"
            print("[PASS] 1. Login page (200 OK)")

            # POST Login as Owner
            res_login_post = client.post('/auth/login', data={'username': owner.username, 'password': 'password123'}, follow_redirects=True)
            assert res_login_post.status_code == 200, f"Owner login POST failed: {res_login_post.status_code}"
            print(f"[PASS] 2. Owner ({owner.username}) login successful!")

            # Dashboard GET
            res_dash = client.get('/dashboard/')
            assert res_dash.status_code == 200, f"Dashboard GET failed: {res_dash.status_code}"
            print("[PASS] 3. Dashboard page for Owner (200 OK)")

            # Laporan Page GET
            res_laporan = client.get('/laporan/')
            assert res_laporan.status_code == 200, f"Laporan GET failed: {res_laporan.status_code}"
            html_laporan = res_laporan.data.decode('utf-8')
            assert 'Kirim ke Admin' not in html_laporan, "Kirim ke Admin button still present in Laporan HTML!"
            assert 'Unduh PDF' in html_laporan, "Unduh PDF button missing from Laporan HTML!"
            assert 'Unduh Excel' in html_laporan, "Unduh Excel button missing from Laporan HTML!"
            print("[PASS] 4. Laporan page for Owner (200 OK, 'Kirim ke Admin' removed, Exports present)")

            # Unduh PDF Export GET
            res_pdf = client.get('/laporan/export/pdf?periode=bulan_ini')
            assert res_pdf.status_code == 200, f"Export PDF failed: {res_pdf.status_code}"
            assert res_pdf.mimetype == 'application/pdf', f"Export PDF returned {res_pdf.mimetype}!"
            print("[PASS] 5. Unduh PDF Export (200 OK, application/pdf)")

            # Unduh Excel Export GET
            res_excel = client.get('/laporan/export/excel?periode=bulan_ini')
            assert res_excel.status_code == 200, f"Export Excel failed: {res_excel.status_code}"
            print("[PASS] 6. Unduh Excel Export (200 OK)")

            # Transaksi Page GET
            res_tx = client.get('/transaksi/pemasukan')
            assert res_tx.status_code == 200, f"Transaksi GET failed: {res_tx.status_code}"
            print("[PASS] 7. Transaksi Pemasukan page (200 OK)")

            # Usaha Page GET (/usaha/kelola and /usaha/pengaturan)
            res_biz = client.get('/usaha/kelola')
            assert res_biz.status_code == 200, f"Usaha Kelola GET failed: {res_biz.status_code}"
            res_biz_cfg = client.get('/usaha/pengaturan')
            assert res_biz_cfg.status_code == 200, f"Usaha Pengaturan GET failed: {res_biz_cfg.status_code}"
            print("[PASS] 8. Usaha Kelola & Pengaturan pages (200 OK)")

            # Profil Page GET
            res_prof = client.get('/auth/profil')
            assert res_prof.status_code == 200, f"Profil GET failed: {res_prof.status_code}"
            print("[PASS] 9. Profil page (200 OK)")

        # 2. Test Admin Flow
        with app.test_client() as client:
            # POST Login as Admin
            res_admin_login = client.post('/auth/login', data={'username': admin.username, 'password': 'password123'}, follow_redirects=True)
            assert res_admin_login.status_code == 200, f"Admin login POST failed: {res_admin_login.status_code}"
            print(f"[PASS] 10. Admin ({admin.username}) login successful!")

            # Admin Dashboard GET
            res_admin_dash = client.get('/dashboard/')
            assert res_admin_dash.status_code == 200, f"Admin Dashboard GET failed: {res_admin_dash.status_code}"
            html_admin = res_admin_dash.data.decode('utf-8')
            assert 'Laporan Masuk' not in html_admin, "Laporan Masuk link still present in Admin Navbar HTML!"
            print("[PASS] 11. Admin Dashboard page (200 OK, 'Laporan Masuk' removed from Navbar)")

            # Verify Removed Route /admin/laporan-masuk returns 404
            res_removed = client.get('/admin/laporan-masuk')
            assert res_removed.status_code == 404, f"Removed route /admin/laporan-masuk returned {res_removed.status_code} instead of 404!"
            print("[PASS] 12. Removed route /admin/laporan-masuk returns 404 Not Found")

        # 3. Model & Codebase Verification
        try:
            from app.models import LaporanTerkirim
            raise AssertionError("LaporanTerkirim symbol still exists in app.models!")
        except ImportError:
            print("[PASS] 13. LaporanTerkirim model completely absent from app.models")

    print("\n[ALL 13 TESTS PASSED SUCCESSFULLY!]")

if __name__ == '__main__':
    run_tests()
