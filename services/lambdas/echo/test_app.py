# test_app.py
from datetime import datetime, timezone
import warnings
import os
import json
import boto3
from moto import mock_aws
from app import handler

### Quiet down botocore's internal utcnow deprecation warnings in test output (might be a bad idea for prd)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="botocore.auth")

### Ensure region for moto/boto3
os.environ.setdefault("AWS_REGION", "eu-central-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")

def _seed():
    os.environ["DDB_TABLE"] = "kyc-dev-sessions"
    os.environ["BUCKET"] = "kyc-dev-uploads"
    os.environ["STATE_MACHINE_ARN"] = "arn:aws:states:eu-central-1:123456789012:stateMachine:kyc-dev-pipeline"
    os.environ["REKOGNITION_ENABLED"] = "false"

def _create_bucket_region_safe(bucket_name: str, region: str = "eu-central-1"):
    s3 = boto3.client("s3", region_name=region)
    if region == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )

@mock_aws
def test_ping():
    _seed()
    ### DynamoDB table
    boto3.client("dynamodb", region_name="eu-central-1").create_table(
        TableName=os.environ["DDB_TABLE"],
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    )
    ### S3 bucket (region-safe)
    _create_bucket_region_safe(os.environ["BUCKET"], "eu-central-1")

    resp = handler({"rawPath": "/ping", "requestContext": {"http": {"method": "GET"}}}, None)
    assert resp["statusCode"] == 200

@mock_aws
def test_presign_and_echo():
    _seed()
    ddb = boto3.client("dynamodb", region_name="eu-central-1")
    ddb.create_table(
        TableName=os.environ["DDB_TABLE"],
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    )
    ### S3 bucket 
    _create_bucket_region_safe(os.environ["BUCKET"], "eu-central-1")

    r = handler({"rawPath": "/presign-id", "requestContext": {"http": {"method": "POST"}}}, None)
    assert r["statusCode"] == 200 and "putUrl" in json.loads(r["body"])

    r = handler(
        {
            "rawPath": "/echo",
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"hello": "world"}),
        },
        None,
    )
    assert r["statusCode"] == 200
