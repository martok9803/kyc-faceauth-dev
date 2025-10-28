# test_audit.py
import os
import json
import boto3
from moto import mock_aws
from app import handler

os.environ.setdefault("AWS_REGION", "eu-central-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-central-1")

def _seed_env(rekognition_enabled: bool):
    os.environ["DDB_TABLE"] = "kyc-dev-sessions"
    os.environ["BUCKET"] = "kyc-dev-uploads"
    os.environ["REKOGNITION_ENABLED"] = "true" if rekognition_enabled else "false"

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
def test_analyze_audit_written_simulated():
    _seed_env(rekognition_enabled=False)

    ### infra
    ddb = boto3.client("dynamodb", region_name="eu-central-1")
    ddb.create_table(
        TableName=os.environ["DDB_TABLE"],
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName":"pk","AttributeType":"S"},{"AttributeName":"sk","AttributeType":"S"}],
        KeySchema=[{"AttributeName":"pk","KeyType":"HASH"},{"AttributeName":"sk","KeyType":"RANGE"}],
    )
    _create_bucket_region_safe(os.environ["BUCKET"], "eu-central-1")

    ### call
    evt = {
        "rawPath": "/analyze",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"sourceKey": "uploads/a.jpg", "targetKey": "uploads/b.jpg"})
    }
    r = handler(evt, None)
    assert r["statusCode"] == 200

    ### ensure an audit record exists 
    resp = ddb.query(
        TableName=os.environ["DDB_TABLE"],
        KeyConditionExpression="pk = :pk",
        ExpressionAttributeValues={":pk": {"S": "echo#analyze"}},
        ScanIndexForward=False,  ### latest first
        Limit=1,
    )
    items = resp.get("Items") or []
    assert len(items) == 1
    assert items[0]["pk"]["S"] == "echo#analyze"
    assert items[0]["sk"]["S"].split("#")[1] in ("simulated", "rekognition")
    assert "payload" in items[0]
