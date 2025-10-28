# app.py
import os
import json
import base64
import uuid
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, Optional

### ---- config (defaults; tests/env may override) ----
DDB_TABLE = os.environ.get("DDB_TABLE", "kyc-dev-sessions")
BUCKET = os.environ.get("BUCKET", "kyc-dev-uploads")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "arn:aws:states:eu-central-1:123456789012:stateMachine:kyc-dev-pipeline")

### Ensure a region is present, moto and loc runs
os.environ.setdefault("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "eu-central-1"))
_region = boto3.session.Session().region_name or os.getenv("AWS_REGION") or "eu-central-1"

### Clients use the resolved region so moto works consistently (for now)
s3 = boto3.client("s3", region_name=_region)
ddb = boto3.client("dynamodb", region_name=_region)

### Optional / lazy clients
rek: Optional[boto3.client] = None
sfn: Optional[boto3.client] = None

def _get_rek():
    global rek
    if rek is None:
        rek = boto3.client("rekognition", region_name=_region)
    return rek

def _get_sfn():
    global sfn
    if sfn is None:
        sfn = boto3.client("stepfunctions", region_name=_region)
    return sfn

### ---- helpers ----
def _resp(code: int, body: Dict[str, Any] | str, extra_headers: Dict[str, str] | None = None):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": code,
        "headers": headers,
        "body": json.dumps(body) if not isinstance(body, str) else body,
    }

def _get_method(event) -> str:
    return (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    ).upper()

def _get_path(event) -> str:
    return event.get("rawPath") or event.get("path") or "/"

def _get_query(event) -> Dict[str, Any]:
    return event.get("queryStringParameters") or {}

def _get_json(event) -> Dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8", "ignore")
        except Exception:
            return {}
    try:
        return json.loads(body)
    except Exception:
        return {}

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _put_audit(kind: str, payload: Dict[str, Any]) -> None:
    """
    Write a compact, queryable audit record to DynamoDB.
    pk = fixed partition (service); sk = time-ordered with kind prefix.
    """
    try:
        item = {
            "pk": {"S": "echo#analyze"},  ### single-partition timeline ?
            "sk": {"S": f"{_utc_now_iso()}#{kind}#{uuid.uuid4()}"},
            "payload": {"S": json.dumps(payload)[:35000]},  ### keep under 400KB item limit pls
        }
        ddb.put_item(TableName=DDB_TABLE, Item=item)
    except Exception as e:
        ### keep API responsive even if audit fails
        print(f"[audit] put_item failed: {e}")

### ---- routes/handlers ----
def _handle_ping(event, context):
    return _resp(200, {
        "ok": True,
        "service": "echo",
        "bucket": BUCKET,
        "table": DDB_TABLE,
        ### report current env flags for visibility
        "rekognition": os.getenv("REKOGNITION_ENABLED", "false").lower() == "true",
        "utc": _utc_now_iso(),
    })

def _handle_presign_id(event, context):
    """
    POST /presign-id
    Returns a presigned PUT URL (field key: 'putUrl') and object key.
    """
    key = f"uploads/{uuid.uuid4()}.bin"
    expires = 300
    try:
        put_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expires,
        )
        return _resp(200, {"bucket": BUCKET, "key": key, "putUrl": put_url, "expires": expires})
    except Exception as e:
        return _resp(500, {"error": str(e)})

def _handle_echo(event, context):
    """
    POST /echo
    Echos the JSON body back.
    """
    payload = _get_json(event)
    return _resp(200, {"echo": payload or {}})

def _handle_analyze(event, context):
    """
    POST /analyze
    Body: { "sourceKey": "uploads/a.jpg", "targetKey": "uploads/b.jpg", "similarity": 90 }
    Reads feature flags dynamically from env to avoid import-time staleness.
    Audits every call to DynamoDB.
    """
    rekognition_enabled = os.getenv("REKOGNITION_ENABLED", "false").lower() == "true"
    start_sfn = os.getenv("START_SFN", "false").lower() == "true"

    data = _get_json(event)
    source_key = data.get("sourceKey")
    target_key = data.get("targetKey")
    threshold = float(data.get("similarity") or 80.0)

    if not source_key or not target_key:
        return _resp(400, {"error": "sourceKey and targetKey are required"})

    ### Simulated path (dev/local)
    if not rekognition_enabled:
        result = {
            "rekognition": False,
            "similarityThreshold": threshold,
            "matches": [{"similarity": 99.0, "boundingBox": {"Top": 0, "Left": 0, "Width": 1, "Height": 1}}],
            "unmatched": [],
        }
        _put_audit("simulated", {"sourceKey": source_key, "targetKey": target_key, "result": result})
        if start_sfn and STATE_MACHINE_ARN:
            try:
                _get_sfn().start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    input=json.dumps({"sourceKey": source_key, "targetKey": target_key, "simulated": True})
                )
                result["stepFunctionStarted"] = True
            except Exception as e:
                result["stepFunctionError"] = str(e)
        return _resp(200, result)

    ### Real Rekognition path
    try:
        response = _get_rek().compare_faces(
            SourceImage={"S3Object": {"Bucket": BUCKET, "Name": source_key}},
            TargetImage={"S3Object": {"Bucket": BUCKET, "Name": target_key}},
            SimilarityThreshold=threshold,
        )
        matches = [
            {
                "similarity": m.get("Similarity"),
                "boundingBox": m.get("Face", {}).get("BoundingBox"),
                "confidence": m.get("Face", {}).get("Confidence"),
            }
            for m in (response.get("FaceMatches") or [])
        ]
        unmatched = response.get("UnmatchedFaces") or []
        result = {
            "rekognition": True,
            "similarityThreshold": threshold,
            "matches": matches,
            "unmatchedCount": len(unmatched),
        }
        _put_audit("rekognition", {
            "sourceKey": source_key,
            "targetKey": target_key,
            "threshold": threshold,
            "matches": matches,
            "unmatchedCount": len(unmatched),
        })

        if start_sfn and STATE_MACHINE_ARN:
            try:
                _get_sfn().start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    input=json.dumps({
                        "sourceKey": source_key,
                        "targetKey": target_key,
                        "matches": matches,
                        "unmatchedCount": len(unmatched),
                    })
                )
                result["stepFunctionStarted"] = True
            except Exception as e:
                result["stepFunctionError"] = str(e)

        return _resp(200, result)
    except Exception as e:
        return _resp(500, {"error": str(e)})

### ---- entrypoint ----
def handler(event, context):
    method = _get_method(event)
    path = _get_path(event)

    if method == "OPTIONS":
        return _resp(200, {"ok": True})

    if path == "/ping" and method == "GET":
        return _handle_ping(event, context)

    if path == "/presign-id" and method == "POST":
        return _handle_presign_id(event, context)

    if path == "/echo" and method == "POST":
        return _handle_echo(event, context)

    if path == "/analyze" and method == "POST":
        return _handle_analyze(event, context)

    return _resp(404, {"error": "Not found", "path": path, "method": method})
