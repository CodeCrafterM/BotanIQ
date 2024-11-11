import json

import boto3
import pytest
from moto import mock_aws
from utils.rekognition import PlantDetector

from lambda_functions.main_handler import handler


@pytest.fixture
def s3_event():
    """
    Simulated S3 event payload for testing.
    """
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test-image.jpg"},
                }
            }
        ]
    }


@pytest.fixture
def setup_environment(monkeypatch):
    """
    Fixture to set up environment variables for testing.
    """
    monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:test-topic")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "TestTable")


@mock_aws
def test_handler(s3_event, setup_environment, monkeypatch):
    """
    Test the Lambda handler with mocked AWS services.
    """
    # Mock S3 setup
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test-bucket"
    object_key = "test-image.jpg"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(
        Bucket=bucket_name, Key=object_key, Body=b"dummy image content"
    )

    # Mock DynamoDB setup
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table_name = "TestTable"
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "frame_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "frame_id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)

    # Mock PlantDetector
    def mock_detect_multiple(self):
        return {
            "labels": [{"Name": "Plant", "Confidence": 99.0}],
            "total_instances": 1,  # Mock one plant detected
        }

    # Use monkeypatch to mock the detect_multiple method in the PlantDetector class
    monkeypatch.setattr(PlantDetector, "detect_multiple", mock_detect_multiple)

    # Mock SNS setup
    sns_client = boto3.client("sns", region_name="us-east-1")
    topic_arn = sns_client.create_topic(Name="test-topic")["TopicArn"]

    # Add SNS topic ARN to environment variables
    monkeypatch.setenv("SNS_TOPIC_ARN", topic_arn)

    # Mock publish method
    def mock_publish(TopicArn, Message, Subject):
        # Validate that the correct topic and message are being used
        assert TopicArn == topic_arn
        assert "Plant detected" in Message
        assert Subject == "Plant Detection Alert"
        return {"MessageId": "mock-message-id"}

    monkeypatch.setattr(sns_client, "publish", mock_publish)

    # Invoke the handler function
    response = handler(s3_event, None)

    # Validate the response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Process completed"

    # Validate DynamoDB data
    stored_items = table.scan()["Items"]
    assert len(stored_items) == 1
    assert stored_items[0]["frame_id"] == f"{bucket_name}/{object_key}"
    assert (
        stored_items[0]["plants_detected"] == 1
    )  # Based on mocked Rekognition response
