from app import app, User

with app.app_context():

    users = User.query.all()

    if not users:
        print("No users found in database.")
    else:
        print("Registered accounts:")
        print("-" * 40)
        for user in users:
            print(f"ID: {user.id}   Username: {user.username}   Email: {user.email or 'not set'}")
