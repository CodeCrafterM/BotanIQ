import json
import logging
import os
from datetime import datetime
from decimal import Decimal

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


# Recursive function to convert floats to Decimal
def convert_to_decimal(data):
    if isinstance(data, list):
        return [convert_to_decimal(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, float):
        return Decimal(str(data))  # Convert float to Decimal
    else:
        return data


# Helper function to save metadata to DynamoDB
def save_frame_metadata(bucket, key, size, plants_detected, plant_labels):
    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    if not table_name:
        logger.error("DYNAMODB_TABLE_NAME environment variable is not set.")
        raise ValueError("DYNAMODB_TABLE_NAME environment variable is required.")

    table = dynamodb.Table(table_name)  # Initialize table dynamically
    frame_id = f"{bucket}/{key}"
    timestamp = datetime.utcnow().isoformat()

    item = {
        "frame_id": frame_id,
        "bucket": bucket,
        "key": key,
        "size": size,
        "plants_detected": plants_detected,
        "plant_labels": plant_labels,
        "timestamp": timestamp,
    }

    try:
        # Convert all float values in the item to Decimal
        item = convert_to_decimal(item)
        table.put_item(Item=item)
        logger.info("Frame metadata saved to DynamoDB: %s", item)
    except Exception as e:
        logger.error("Error saving metadata to DynamoDB: %s", e)
        raise


# Recursive function to convert floats to Decimal
def convert_to_decimal(data):
    if isinstance(data, list):
        return [convert_to_decimal(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, float):
        return Decimal(str(data))  # Convert float to Decimal
    else:
        return data


# Helper function to save metadata to DynamoDB
def save_frame_metadata(bucket, key, size, plants_detected, plant_labels):
    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    if not table_name:
        logger.error("DYNAMODB_TABLE_NAME environment variable is not set.")
        raise ValueError("DYNAMODB_TABLE_NAME environment variable is required.")

    table = dynamodb.Table(table_name)  # Initialize table dynamically
    frame_id = f"{bucket}/{key}"
    timestamp = datetime.utcnow().isoformat()

    item = {
        "frame_id": frame_id,
        "bucket": bucket,
        "key": key,
        "size": size,
        "plants_detected": plants_detected,
        "plant_labels": plant_labels,
        "timestamp": timestamp,
    }

    try:
        # Convert all float values in the item to Decimal
        item = convert_to_decimal(item)
        table.put_item(Item=item)
        logger.info("Frame metadata saved to DynamoDB: %s", item)
    except Exception as e:
        logger.error("Error saving metadata to DynamoDB: %s", e)
        raise


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
        plants_detected = detection_result[
            "total_instances"
        ]  # Total count of plant instances
        total_plants_detected += plants_detected

        if plants_detected > 0:
            logger.info("Plants detected in image %s: %s", key, plant_labels)
            notifier.send_notification(key, plants_detected)
        else:
            logger.info("No plants detected in image: %s", key)

        # Publish frame metadata to DynamoDB
        save_frame_metadata(bucket, key, size, plants_detected, plant_labels)

    # Publish CloudWatch metrics
    try:
        cloudwatch.put_metric_data(
            Namespace="PlantDetectionAnalytics",
            MetricData=[
                {
                    "MetricName": "FramesProcessed",
                    "Value": frames_processed,
                    "Unit": "Count",
                },
                {
                    "MetricName": "PlantsDetected",
                    "Value": total_plants_detected,
                    "Unit": "Count",
                },
            ],
        )
        logger.info("CloudWatch metrics published successfully.")
    except Exception as e:
        logger.error("Failed to publish CloudWatch metrics: %s", e)

    return {"statusCode": 200, "body": json.dumps({"message": "Process completed"})}

