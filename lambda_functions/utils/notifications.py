import logging
import os

import boto3

logger = logging.getLogger()


class NotificationService:
    def __init__(self):
        """
        Initialize the NotificationService with an SNS client and topic ARN.
        """
        aws_region = os.getenv("AWS_REGION", "us-east-1")  # Default to us-east-1
        self.sns_client = boto3.client("sns", region_name=aws_region)
        self.topic_arn = os.getenv("SNS_TOPIC_ARN")

    def send_notification(self, object_key, plants_detected):
        """
        Send an SNS notification with the count of plants detected in an image.

        Parameters:
            object_key (str): The S3 object key for the processed image.
            plants_detected (int): The number of plants detected in the image.
        """
        if plants_detected > 0:
            message = (
                f"{plants_detected} plant(s) detected in image '{object_key}'. "
                "You can check the detailed analysis in the system."
            )
            try:
                # Publish the message to the SNS topic
                response = self.sns_client.publish(
                    TopicArn=self.topic_arn,
                    Message=message,
                    Subject="Plant Detection Alert",
                )
                logger.info(
                    "SNS notification sent successfully for '%s'. SNS response: %s",
                    object_key,
                    response,
                )
            except self.sns_client.exceptions.EndpointDisabledException as e:
                logger.error("SNS endpoint is disabled: %s", e)
            except self.sns_client.exceptions.InvalidParameterException as e:
                logger.error("Invalid parameter when sending SNS notification: %s", e)
            except Exception as e:
                logger.error("Error in sending SNS notification: %s", e)
        else:
            logger.info(
                "No plants detected in image '%s'. No notification sent.", object_key
            )
