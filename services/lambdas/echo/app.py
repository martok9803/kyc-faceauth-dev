import os, json, time, uuid
import boto3

DDB  = boto3.client("dynamodb")
S3   = boto3.client("s3")
SFN  = boto3.client("stepfunctions")
REKO = boto3.client("rekognition")

TABLE   = os.environ.get("DDB_TABLE","")
BUCKET  = os.environ.get("BUCKET","")
STATE_MACHINE_ARN  = os.environ.get("STATE_MACHINE_ARN","")
REKOGNITION_ENABLED = os.environ.get("REKOGNITION_ENABLED","false").lower() == "true"

def _resp(code, body, headers=None):
    h = {"content-type":"application/json"}
    if headers: h.update(headers)
    return {"statusCode": code, "headers": h, "body": json.dumps(body)}

def handler(event, context):
    path = event.get("rawPath","/")
    method = event.get("requestContext",{}).get("http",{}).get("method","GET")

    if path == "/ping" and method == "GET":
        return _resp(200, {"ok": True, "ts": int(time.time()), "bucket": BUCKET, "table": TABLE})

    if path == "/echo" and method == "POST":
        try:
            body = json.loads(event.get("body") or "{}")
        except Exception:
            body = {}
        pk = f"echo#{int(time.time())}"
        DDB.put_item(
            TableName=TABLE,
            Item={"pk":{"S":pk},"sk":{"S":"v1"},"payload":{"S":json.dumps(body)[:1000]}}
        )
        return _resp(200, {"saved": pk, "echo": body})

    if path == "/presign-id" and method == "POST":
        key = f"uploads/{uuid.uuid4().hex}.jpg"
        put_url = S3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": BUCKET, "Key": key, "ContentType": "image/jpeg"},
            ExpiresIn=600
        )
        get_url = S3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=600
        )
        return _resp(200, {"bucket": BUCKET, "key": key, "putUrl": put_url, "getUrl": get_url})

    if path == "/liveness/start" and method == "POST":
        if not REKOGNITION_ENABLED:
            return _resp(200, {"sessionId": f"mock-{uuid.uuid4().hex}", "mode": "mock"})
        resp = REKO.create_face_liveness_session()
        return _resp(200, {"sessionId": resp["SessionId"], "mode": "rekognition"})

    if path == "/kyc/submit" and method == "POST":
        body = json.loads(event.get("body") or "{}")
        if not STATE_MACHINE_ARN:
            return _resp(500, {"error":"STATE_MACHINE_ARN not set"})
        execution_input = {
            "userId": body.get("userId","unknown"),
            "idImageKey": body.get("idImageKey",""),
            "livenessSessionId": body.get("livenessSessionId",""),
            "policy": body.get("policy", {"minSimilarity": 85})
        }
        name = f"kyc-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        out = SFN.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=name,
            input=json.dumps(execution_input)
        )
        return _resp(200, {"kycRequestId": name, "executionArn": out["executionArn"]})

    return _resp(404, {"error":"Not found"})
