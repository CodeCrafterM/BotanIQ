import os
import sys

import boto3
import pytest


@pytest.fixture(scope="session", autouse=True)
def set_mocked_aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "mock_access_key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "mock_secret_key"
    os.environ["AWS_SESSION_TOKEN"] = "mock_session_token"
    os.environ["AWS_REGION"] = "us-east-1"
    boto3.setup_default_session(region_name="us-east-1")


# Add the lambda_functions directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lambda_functions"))
)
