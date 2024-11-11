import subprocess
import sys


def main():
    try:
        # Format with Black
        subprocess.run(
            ["black", "lambda_functions/", "tests/", "scripts/", "cdk/"], check=True
        )
        # Sort imports with isort
        subprocess.run(
            ["isort", "lambda_functions/", "tests/", "scripts/", "cdk/"], check=True
        )
        print("Formatting completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during formatting: {e}")
        sys.exit(1)
