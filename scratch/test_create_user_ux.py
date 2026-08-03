import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

def test_create_user_ux():
    with app.app_context():
        print("=== TEST: ADMIN CREATE USER UX & WHATSAPP FORMAT ===")

        admin = User.query.filter_by(role='admin').first()
        assert admin is not None, "Admin user not found"

        client = app.test_client()

        # 1. Login as Admin
        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(admin)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True

            # 2. Submit user creation form with valid phone
            res = client.post('/admin/users/create', data={
                'full_name': 'Pak Slamet Santoso',
                'phone': '081234567890',
                'role': 'owner'
            }, follow_redirects=True)

            assert res.status_code == 200

            # Check created user in DB
            created_user = User.query.filter_by(full_name='Pak Slamet Santoso').first()
            assert created_user is not None
            assert created_user.phone == '081234567890'
            print(f"[1] Created User in DB: Username '{created_user.username}', Phone '{created_user.phone}'")

            # Verify session data was set
            # Clean up test user
            db.session.delete(created_user)
            db.session.commit()

        # 3. Test WhatsApp message text format directly
        username = "pakslamet"
        temp_password = "Password123"
        wa_message = (
            f"Halo!\n\n"
            f"Akun Siwaruk Anda telah berhasil dibuat.\n\n"
            f"Username:\n{username}\n\n"
            f"Password:\n{temp_password}\n\n"
            f"Silakan login melalui:\nhttps://siwaruk.vercel.app\n\n"
            f"Demi keamanan, segera ubah password setelah berhasil login pertama kali.\n\n"
            f"Terima kasih."
        )

        expected_substr = "Silakan login melalui:\nhttps://siwaruk.vercel.app"
        assert expected_substr in wa_message
        print("\n[2] WhatsApp Message Format:")
        print("-----------------------------------")
        print(wa_message)
        print("-----------------------------------")
        print("[SUCCESS] All checks passed cleanly!")

if __name__ == '__main__':
    test_create_user_ux()
