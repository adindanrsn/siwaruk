import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.utils import get_whatsapp_link

app = create_app()

def test_floating_wa():
    with app.app_context():
        print("=== TEST: FLOATING WHATSAPP BUTTON ===")

        # 1. Check generated URL for consultation
        link = get_whatsapp_link('consultation')
        print(f"Generated WA Consultation Link: {link}")
        assert "wa.me" in link
        assert "Halo%20Admin" in link or "Halo+Admin" in link or "Halo" in link
        assert "Saya%20ingin%20berkonsultasi" in link or "berkonsultasi" in link

        client = app.test_client()

        # 2. Test unauthenticated request (login page)
        res_unauth = client.get('/auth/login')
        assert res_unauth.status_code == 200
        assert b'floating-wa-btn' not in res_unauth.data
        print("[1] Unauthenticated / Login page: Floating button correctly HIDDEN.")

        # 3. Test authenticated request
        owner = User.query.filter_by(role='owner').first()
        if not owner:
            owner = User(username='test_owner_wa', full_name='Owner Test WA', role='owner')
            owner.set_password('Password123')
            db.session.add(owner)
            db.session.commit()

        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(owner)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(owner.id)

            res_auth = client.get('/')
            assert res_auth.status_code in [200, 302]

            if res_auth.status_code == 200:
                assert b'floating-wa-btn' in res_auth.data
                assert b'Hubungi Admin' in res_auth.data
                print("[2] Authenticated user / Dashboard page: Floating button correctly SHOWN.")
            else:
                res_dashboard = client.get('/auth/profil')
                assert b'floating-wa-btn' in res_dashboard.data
                print("[2] Authenticated user / Profil page: Floating button correctly SHOWN.")

        print("\n[SUCCESS] Floating WhatsApp Button tests passed cleanly!")

if __name__ == '__main__':
    test_floating_wa()
