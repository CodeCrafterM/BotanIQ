import logging
import os

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

    def detect_multiple(self):
        """
        Detect multiple plant-related labels in the image and count the total instances.

        Returns:
            list: A list of plant-related labels and the total count of plant instances.
        """
        try:
            # Call Rekognition to detect labels
            response = self.rekognition_client.detect_labels(
                Image={
                    "S3Object": {"Bucket": self.bucket_name, "Name": self.object_key}
                },
                MaxLabels=50,  # Increased for comprehensive detection
                MinConfidence=70,  # Adjusted threshold for better coverage
            )
            logger.info(
                "Rekognition response for image '%s': %s", self.object_key, response
            )

            # Extract plant-related labels
            plant_labels = []
            total_instances = 0

            for label in response.get("Labels", []):
                # Check if the label is plant-related
                if label["Name"].lower() in [
                    "plant",
                    "leaf",
                    "potted plant",
                    "herbs",
                    "herbal",
                ]:
                    plant_labels.append(
                        {
                            "Name": label["Name"],
                            "Confidence": label["Confidence"],
                            "Instances": len(
                                label.get("Instances", [])
                            ),  # Count bounding boxes (plants)
                        }
                    )
                    # Sum up all bounding box instances
                    total_instances += len(label.get("Instances", []))

            logger.info("Detected plant-related labels: %s", plant_labels)
            logger.info("Total plant instances detected: %d", total_instances)

            return {"labels": plant_labels, "total_instances": total_instances}

        except self.rekognition_client.exceptions.InvalidS3ObjectException as e:
            logger.error("Invalid S3 object for image '%s': %s", self.object_key, e)
            return {"labels": [], "total_instances": 0}

        except self.rekognition_client.exceptions.InvalidParameterException as e:
            logger.error(
                "Invalid parameter passed for image '%s': %s", self.object_key, e
            )
            return {"labels": [], "total_instances": 0}

        except self.rekognition_client.exceptions.AccessDeniedException as e:
            logger.error(
                "Access denied for Rekognition or S3 object '%s': %s",
                self.object_key,
                e,
            )
            return {"labels": [], "total_instances": 0}

        except (ClientError, BotoCoreError) as e:
            logger.error(
                "General error in Rekognition detect_labels for '%s': %s",
                self.object_key,
                e,
            )
            return {"labels": [], "total_instances": 0}

        except Exception as e:
            logger.error(
                "Unexpected error in Rekognition detect_labels for '%s': %s",
                self.object_key,
                e,
            )
            return {"labels": [], "total_instances": 0}
