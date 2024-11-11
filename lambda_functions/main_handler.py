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
    frames_processed = 0
    total_plants_detected = 0

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

        frames_processed += 1  # Increment frames processed for each record

        # Detect multiple plants in the image
        detection_result = plant_detector.detect_multiple()
        plant_labels = detection_result["labels"]
        plants_detected = detection_result["total_instances"]  # Total count of plant instances
        total_plants_detected += plants_detected

        if plants_detected > 0:
            logger.info("Plants detected in image %s: %s", key, plant_labels)
            notifier.send_notification(key, plants_detected)
        else:
            logger.info("No plants detected in image: %s", key)

    return {"statusCode": 200, "body": json.dumps({"message": "Process completed"})}