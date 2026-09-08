from app import app
from utils.expiry_service import run_expiry_checks


with app.app_context():

    result = run_expiry_checks()

    print("\nExpiry check result:")
    print(result)