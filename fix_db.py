from app import create_app, db
from app.models import ContactRequest

app = create_app()

with app.app_context():
    print("Checking database tables...")
    # This will create any tables that are defined in models but missing in DB
    db.create_all()
    print("Database tables updated. 'contact_request' should now exist.")
