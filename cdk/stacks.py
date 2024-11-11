from aws_cdk import Stack, aws_s3 as s3, aws_lambda as _lambda, aws_sns as sns
from constructs import Construct

class PlantDetectionStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # S3 bucket for image storage
        bucket = s3.Bucket(self, "CameraFramesBucket")

        # Lambda function for processing images
        detection_lambda = _lambda.Function(self, "PlantDetectionLambda",
                                            runtime=_lambda.Runtime.PYTHON_3_8,
                                            handler="main_handler.handler",
                                            code=_lambda.Code.from_asset("lambda_functions"))

        # SNS topic for notifications
        notification_topic = sns.Topic(self, "PlantDetectionTopic")