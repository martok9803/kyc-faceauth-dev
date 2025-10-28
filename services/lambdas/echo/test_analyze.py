# test_analyze.py
import os
import json
import boto3
from moto import mock_aws
from botocore.stub import Stubber
import app  # import the module to override its rek client
from app import handler

# Ensure region for moto/boto3
os.environ.setdefault("AWS_REGION", "eu-central-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")

def _seed_env(rekognition_enabled: bool):
    os.environ["DDB_TABLE"] = "kyc-dev-sessions"
    os.environ["BUCKET"] = "kyc-dev-uploads"
    os.environ["STATE_MACHINE_ARN"] = "arn:aws:states:eu-central-1:123456789012:stateMachine:kyc-dev-pipeline"
    os.environ["REKOGNITION_ENABLED"] = "true" if rekognition_enabled else "false"
    os.environ["START_SFN"] = "false"  # keep off for unit test

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
def test_analyze_simulated_when_disabled():
    _seed_env(rekognition_enabled=False)

    # Create mocked infra
    boto3.client("dynamodb", region_name="eu-central-1").create_table(
        TableName=os.environ["DDB_TABLE"],
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName":"pk","AttributeType":"S"},{"AttributeName":"sk","AttributeType":"S"}],
        KeySchema=[{"AttributeName":"pk","KeyType":"HASH"},{"AttributeName":"sk","KeyType":"RANGE"}],
    )
    _create_bucket_region_safe(os.environ["BUCKET"], "eu-central-1")

    event = {
        "rawPath": "/analyze",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"sourceKey": "uploads/a.jpg", "targetKey": "uploads/b.jpg", "similarity": 85})
    }
    r = handler(event, None)
    assert r["statusCode"] == 200
    body = json.loads(r["body"])
    assert body["rekognition"] is False
    assert body["matches"]

@mock_aws
def test_analyze_with_stubbed_rekognition():
    _seed_env(rekognition_enabled=True)

    # Create mocked infra
    boto3.client("dynamodb", region_name="eu-central-1").create_table(
        TableName=os.environ["DDB_TABLE"],
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName":"pk","AttributeType":"S"},{"AttributeName":"sk","AttributeType":"S"}],
        KeySchema=[{"AttributeName":"pk","KeyType":"HASH"},{"AttributeName":"sk","KeyType":"RANGE"}],
    )
    _create_bucket_region_safe(os.environ["BUCKET"], "eu-central-1")

    # Build a real rek client + stub responses, then inject into app.rek
    rek_client = boto3.client("rekognition", region_name="eu-central-1")
    stubber = Stubber(rek_client)
    expected_params = {
        "SourceImage": {"S3Object": {"Bucket": os.environ["BUCKET"], "Name": "uploads/a.jpg"}},
        "TargetImage": {"S3Object": {"Bucket": os.environ["BUCKET"], "Name": "uploads/b.jpg"}},
        "SimilarityThreshold": 80.0,
    }
    stub_response = {
        "SourceImageFace": {"BoundingBox": {"Top": 0.1, "Left": 0.1, "Width": 0.3, "Height": 0.3}, "Confidence": 99.0},
        "FaceMatches": [
            {
                "Similarity": 92.5,
                "Face": {
                    "BoundingBox": {"Top": 0.12, "Left": 0.12, "Width": 0.28, "Height": 0.28},
                    "Confidence": 98.0,
                },
            }
        ],
        "UnmatchedFaces": [],
    }
    stubber.add_response("compare_faces", stub_response, expected_params)
    stubber.activate()

    # Inject the stubbed client into the app module
    app.rek = rek_client

    event = {
        "rawPath": "/analyze",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"sourceKey": "uploads/a.jpg", "targetKey": "uploads/b.jpg"})  # threshold defaults to 80.0
    }
    r = handler(event, None)
    assert r["statusCode"] == 200
    body = json.loads(r["body"])
    assert body["rekognition"] is True
    assert body["matches"][0]["similarity"] == 92.5
    assert body["unmatchedCount"] == 0
