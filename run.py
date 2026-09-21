import os
import sys
from app import create_app, db

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    with app.app_context():
        # Ensure database tables are created
        db.create_all()

    if "--seed" in sys.argv:
        from scripts.seed_demo_data import seed_all
        with app.app_context():
            seed_all()
        print("Demo personas seeded successfully!")
        sys.exit(0)

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
