import json
import logging
import os

import boto3
from utils.notifications import NotificationService
from utils.rekognition import PlantDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize AWS clients
aws_region = os.getenv("AWS_REGION", "us-east-1")
logger.info(f"Using AWS_REGION: {aws_region}")
cloudwatch = boto3.client("cloudwatch", region_name=aws_region)
dynamodb = boto3.resource("dynamodb", region_name=aws_region)


def handler(event, context):
    logger.info("Event received: %s", json.dumps(event))

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        size = record["s3"]["object"].get("size", 0)  # Default size to 0 if not present
        logger.info(
            "Processing file from bucket: %s, key: %s, size: %s bytes",
            bucket,
            key,
            size,
        )

        # Initialize detection and notification services
        plant_detector = PlantDetector(bucket, key)
        notifier = NotificationService()

        if plant_detector.detect():
            logger.info("Plant detected in image %s", key)
            notifier.send_notification(key, 1)
        else:
            logger.info("No plant detected in image: %s", key)

    return {"statusCode": 200, "body": json.dumps({"message": "Process completed"})}