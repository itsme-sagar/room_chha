from app import app
from utils.expiry_service import run_expiry_checks


def run():
    with app.app_context():

        result = run_expiry_checks()

        print("Expiry check completed:")
        print(result)


if __name__ == "__main__":
    run()