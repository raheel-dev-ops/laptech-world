from app import app, db, User

with app.app_context():

    duplicate = User.query.filter_by(username="admin").first()

    if duplicate:
        db.session.delete(duplicate)
        db.session.commit()
        print("Duplicate admin account deleted successfully.")
    else:
        print("No admin account found — nothing to delete.")
