"""
Ngrok Deployment and Tunnel Helper
----------------------------------
Configures Werkzeug ProxyFix to securely trust proxy headers (X-Forwarded-Proto, X-Forwarded-Host),
ensuring HTTPS cookies and URLs function seamlessly through public Ngrok tunnels.

Usage:
  1. Start this script: python scripts/run_with_ngrok.py
  2. In a separate terminal: ngrok http 5000
"""

import os
import sys
from werkzeug.middleware.proxy_fix import ProxyFix

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from scripts.seed_demo_data import seed_all

def main():
    print("=" * 70)
    print(" Personal Finance Advisor Bot — Ngrok Deployment Mode")
    print("=" * 70)
    print("\n[SECURITY NOTICE]:")
    print(" - Ngrok URLs are public. Use ONLY demo data (never real personal finances).")
    print(" - Session cookies and HTTPS headers are secured via ProxyFix.")
    print(" - When running for public demos, ensure debug=False and use strong SECRET_KEY.\n")

    # Force production-style secure cookies when deployed on public tunnel
    os.environ["SESSION_COOKIE_SECURE"] = "True"
    app = create_app("production")

    # Apply ProxyFix for ngrok headers (1 proxy hop)
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    with app.app_context():
        db.create_all()
        # Seed demo personas if database is empty
        from app.models import User
        if User.query.count() == 0:
            print("No users found. Auto-seeding 4 demo personas...")
            seed_all()

    print("[SUCCESS] Local server starting on http://127.0.0.1:5000")
    print("[NEXT STEP] In another terminal, run: ngrok http 5000")
    print("=" * 70)

    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    main()
