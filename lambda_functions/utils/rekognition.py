import os
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class PlantDetector:
    def __init__(self, bucket_name, object_key):
        """
        Initialize PlantDetector with S3 bucket and object key.
        """
        self.bucket_name = bucket_name
        self.object_key = object_key
        aws_region = os.getenv("AWS_REGION", "us-east-1")  # Default to us-east-1
        self.rekognition_client = boto3.client("rekognition", region_name=aws_region)

    def detect(self):
        """
        Detect if a plant is present in the image using Rekognition.
        """
        try:
            response = self.rekognition_client.detect_labels(
                Image={
                    "S3Object": {"Bucket": self.bucket_name, "Name": self.object_key}
                },
                MaxLabels=10,
                MinConfidence=80,
            )
            logger.info("Rekognition response: %s", response)

            # Check for "Plant" in the detected labels
            for label in response.get("Labels", []):
                if label["Name"].lower() == "plant":
                    logger.info("Plant detected in Rekognition labels.")
                    return True
            logger.info("No plant found in Rekognition labels.")
            return False
        except (ClientError, BotoCoreError) as e:
            logger.error("Error in Rekognition detect_labels: %s", e)
            return False