import logging
import os
import sys
import time

from boto3.session import Session
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# Initialize AWS session
def initialize_session():
    """
    Initialize AWS session dynamically. Use environment variables in CI,
    and fallback to a default profile locally.
    """
    try:
        # Use default session if running in CI/CD
        if os.environ.get("CI", "false") == "true":
            aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            aws_region = os.environ.get("AWS_REGION", "us-east-1")

            if not aws_access_key_id or not aws_secret_access_key:
                raise RuntimeError("AWS credentials are missing in CI environment.")

            session = Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region,
            )
        else:
            # Use local AWS profile for development
            session = Session(profile_name="AdministratorAccess-329599627779")

        # Verify session by attempting to fetch a service client
        session.client("sts").get_caller_identity()
        return session
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise RuntimeError("AWS credentials are not properly configured.") from e


# Initialize session
session = initialize_session()

# Initialize AWS clients
s3_client = session.client("s3", region_name="us-east-1")
dynamodb = session.resource("dynamodb", region_name="us-east-1")
sns_client = session.client("sns", region_name="us-east-1")
cloudformation = session.client("cloudformation", region_name="us-east-1")

# Get the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_stack_outputs(stack_name):
    """Fetch stack outputs using CloudFormation."""
    logger.info("Fetching stack outputs for %s", stack_name)
    response = cloudformation.describe_stacks(StackName=stack_name)
    outputs = response["Stacks"][0]["Outputs"]
    return {output["OutputKey"]: output["OutputValue"] for output in outputs}


def upload_image_to_s3(bucket, image_path, key):
    """Upload a test image to the S3 bucket."""
    with open(image_path, "rb") as image_file:
        s3_client.put_object(Bucket=bucket, Key=key, Body=image_file)
    logger.info(f"Uploaded {key} to S3 bucket {bucket}")


def check_dynamodb_entry(table_name, key):
    """Check if the metadata is stored in DynamoDB."""
    table = dynamodb.Table(table_name)
    max_retries = 5
    for attempt in range(max_retries):
        response = table.scan()
        items = response.get("Items", [])
        for item in items:
            if item.get("key") == key:
                logger.info(f"DynamoDB entry found: {item}")
                return item
        logger.info(
            f"Attempt {attempt + 1}/{max_retries}: Metadata not found yet, retrying..."
        )
        time.sleep(5)
    raise Exception("DynamoDB entry not found after retries.")


# TODO
def check_sns_notification():
    """Stub function to validate SNS notification."""
    logger.info("Checking SNS notification... (Not implemented)")
    return True


def cleanup(bucket, key):
    """Clean up resources after the test."""
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted {key} from S3 bucket {bucket}")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def main():
    """Main entry point for the E2E test."""
    # Fetch stack outputs
    stack_outputs = get_stack_outputs("PlantDetectionStack")
    s3_bucket = stack_outputs["S3BucketName"]
    dynamodb_table = stack_outputs["DynamoDBTableName"]

    # Configuration
    unique_key = f"camera_frames/plant-demo-{int(time.time())}.png"
    test_image_path = os.path.join(SCRIPT_DIR, "camera_frames", "plant-demo.png")

    try:
        # Step 1: Upload test image to S3
        upload_image_to_s3(s3_bucket, test_image_path, unique_key)

        # Step 2: Verify DynamoDB entry
        dynamodb_entry = check_dynamodb_entry(dynamodb_table, unique_key)
        assert dynamodb_entry["plants_detected"] > 0, "No plants detected!"

        # Step 3: Validate SNS Notification (if applicable)
        assert check_sns_notification(), "No SNS notification received!"

        logger.info("E2E Test Passed!")
    except Exception as e:
        logger.error(f"E2E Test Failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup resources
        cleanup(s3_bucket, unique_key)


if __name__ == "__main__":
    main()
