# demo_local.py
import os
import json
import boto3
from moto import mock_aws
from botocore.stub import Stubber

### test env
os.environ.setdefault("AWS_REGION", "eu-central-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")
os.environ.setdefault("DDB_TABLE", "kyc-dev-sessions")
os.environ.setdefault("BUCKET", "kyc-dev-uploads")
os.environ.setdefault("STATE_MACHINE_ARN", "arn:aws:states:eu-central-1:123456789012:stateMachine:kyc-dev-pipeline")

# import after env is set
import app  # noqa: E402
from app import handler  # noqa: E402


def _create_bucket_region_safe(bucket_name: str, region: str = "eu-central-1"):
    s3c = boto3.client("s3", region_name=region)
    if region == "us-east-1":
        s3c.create_bucket(Bucket=bucket_name)
    else:
        s3c.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )


@mock_aws
def main():
    region = os.environ["AWS_REGION"]
    ddb = boto3.client("dynamodb", region_name=region)
    s3 = boto3.client("s3", region_name=region)

    ### mockedd infra DDB+s3
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
    _create_bucket_region_safe(os.environ["BUCKET"], region)

    ### two “imageZ” — any bytes are fine for the stub
    s3.put_object(Bucket=os.environ["BUCKET"], Key="uploads/a.jpg", Body=b"A")
    s3.put_object(Bucket=os.environ["BUCKET"], Key="uploads/b.jpg", Body=b"B")

    ### ---- 1) /ping ----
    ping_evt = {"rawPath": "/ping", "requestContext": {"http": {"method": "GET"}}}
    print("\n--- GET /ping")
    print(json.dumps(handler(ping_evt, None), indent=2))

    ### ---- 2) /presign-id ----
    presign_evt = {"rawPath": "/presign-id", "requestContext": {"http": {"method": "POST"}}}
    print("\n--- POST /presign-id")
    print(json.dumps(handler(presign_evt, None), indent=2))

    ### ---- 3) /analyze (simulated, no Rekognition call) ----
    os.environ["REKOGNITION_ENABLED"] = "false"
    analyze_evt = {
        "rawPath": "/analyze",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"sourceKey": "uploads/a.jpg", "targetKey": "uploads/b.jpg", "similarity": 85}),
    }
    print("\n--- POST /analyze (simulated)")
    print(json.dumps(handler(analyze_evt, None), indent=2))

    ### ---- 4) /analyze (rekognition stubbed) ----
    os.environ["REKOGNITION_ENABLED"] = "true"
    rek_client = boto3.client("rekognition", region_name=region)
    stubber = Stubber(rek_client)
    expected_params = {
        "SourceImage": {"S3Object": {"Bucket": os.environ["BUCKET"], "Name": "uploads/a.jpg"}},
        "TargetImage": {"S3Object": {"Bucket": os.environ["BUCKET"], "Name": "uploads/b.jpg"}},
        "SimilarityThreshold": 80.0,  # default when not provided
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

    ### inject stubbed client so app._get_rek() uses gud tek
    app.rek = rek_client

    analyze_evt2 = {
        "rawPath": "/analyze",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"sourceKey": "uploads/a.jpg", "targetKey": "uploads/b.jpg"}),
    }
    print("\n--- POST /analyze (rekognition stubbed)")
    print(json.dumps(handler(analyze_evt2, None), indent=2))

    ### ---- 5) show latest audit row in DynamoDB ----
    print("\n--- DynamoDB latest audit")
    resp = ddb.query(
        TableName=os.environ["DDB_TABLE"],
        KeyConditionExpression="pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "echo#analyze"}},
        ScanIndexForward=False,
        Limit=1,
    )
    print(json.dumps(resp.get("Items"), indent=2))


if __name__ == "__main__":
    main()
