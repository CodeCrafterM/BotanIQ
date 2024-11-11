import json
from pathlib import Path

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from aws_cdk.aws_lambda_event_sources import S3EventSource
from constructs import Construct


class PlantDetectionStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Read email addresses from configuration file
        config_path = Path("config/email_subscribers.json")
        with config_path.open() as config_file:
            config = json.load(config_file)
        email_subscribers = config.get("email_subscribers", [])

        # SNS topic for notifications
        sns_topic = sns.Topic(self, "PlantDetectionTopic")

        # Subscribe email addresses to the SNS topic
        for email in email_subscribers:
            sns_topic.add_subscription(subscriptions.EmailSubscription(email))

        # S3 bucket for frame storage with RemovalPolicy.DESTROY
        bucket = s3.Bucket(
            self,
            "CameraFramesBucket",
            removal_policy=RemovalPolicy.DESTROY,  # Ensure bucket is deleted
            auto_delete_objects=True,  # Automatically delete objects before bucket removal
        )

        # Lambda function for plant detection
        detection_lambda = _lambda.Function(
            self,
            "PlantDetectionLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="main_handler.handler",
            code=_lambda.Code.from_asset("lambda_functions"),
            environment={"SNS_TOPIC_ARN": sns_topic.topic_arn},
        )

        # Grant Rekognition permissions to the Lambda function
        detection_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["rekognition:DetectLabels"],
                resources=["*"],
            )
        )

        # S3 trigger to Lambda
        detection_lambda.add_event_source(
            S3EventSource(bucket, events=[s3.EventType.OBJECT_CREATED])
        )

        # Grant Lambda permissions to read from S3 and publish to SNS
        bucket.grant_read(detection_lambda)
        sns_topic.grant_publish(detection_lambda)

        # Attach policy to allow CloudWatch PutMetricData
        detection_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],  # You can scope this down further if needed
            )
        )

        # DynamoDB table for frame metadata
        table = dynamodb.Table(
            self,
            "FrameMetadataTable",
            partition_key=dynamodb.Attribute(
                name="frame_id", type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,  # Ensures the table is deleted during `cdk destroy`
        )

        #  Permissions to Lambda to write to the table
        table.grant_write_data(detection_lambda)

        # Pass table name to Lambda as environment variable
        detection_lambda.add_environment("DYNAMODB_TABLE_NAME", table.table_name)
