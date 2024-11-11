import subprocess
import sys


def main():
    try:
        # Run flake8 on the specified directories
        subprocess.run(
            ["flake8", "lambda_functions/", "tests/", "scripts/", "cdk/"], check=True
        )
        print("Linting completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Linting failed: {e}")
        sys.exit(1)
