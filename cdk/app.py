# Entry point for AWS CDK

import aws_cdk as cdk
from stacks import PlantDetectionStack

app = cdk.App()
PlantDetectionStack(app, "PlantDetectionStack")
app.synth()