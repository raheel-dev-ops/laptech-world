from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():

    admin = User.query.filter_by(username="admin").first()

    if admin:
        admin.password = generate_password_hash("admin123")
        db.session.commit()
        print("Admin password reset to: admin123")
    else:
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("New admin created with password: admin123")