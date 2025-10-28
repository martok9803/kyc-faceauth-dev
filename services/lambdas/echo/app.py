#!/usr/bin/env python3
import json, os, time, uuid
import boto3
from botocore.exceptions import ClientError

# ---- AWS clients
s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")

# ---- Environment
BUCKET = os.environ["BUCKET"]          # set in Lambda env
TABLE  = os.environ["DDB_TABLE"]       # set in Lambda env
REKOG_ENABLED = os.environ.get("REKOGNITION_ENABLED", "false").lower() == "true"

table = ddb.Table(TABLE)


def respond(status: int, body: dict):
    """Standard JSON response with CORS headers."""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    try:
        route = event.get("rawPath") or event.get("path") or ""
        method = (
            event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")
            or ""
        ).upper()

        if method == "OPTIONS":
            return respond(200, {"ok": True})

        # ---- Health
        if route == "/ping" and method == "GET":
            return respond(
                200,
                {
                    "status": "ok",
                    "time": int(time.time()),
                    "bucket": BUCKET,
                    "table": TABLE,
                },
            )

        # ---- Presign (upload an ID/selfie)
        if route == "/presign-id" and method == "POST":
            key = f"uploads/{uuid.uuid4()}.jpg"
            put_url = s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": BUCKET, "Key": key, "ContentType": "image/jpeg"},
                ExpiresIn=300,
            )
            get_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": key},
                ExpiresIn=300,
            )
            return respond(200, {"key": key, "putUrl": put_url, "getUrl": get_url})

        # ---- Start liveness (mock)
        if route == "/liveness/start" and method == "POST":
            session_id = str(uuid.uuid4())
            table.put_item(
                Item={
                    "pk": f"liveness#{session_id}",
                    "sk": "META",  # required sort key
                    "ts": str(int(time.time())),
                    "status": "started",
                }
            )
            return respond(200, {"sessionId": session_id, "message": "liveness started (mock)"})

        # ---- Liveness results (mock)
        if route == "/liveness/results" and method == "POST":
            body_raw = event.get("body") or "{}"
            try:
                data = json.loads(body_raw)
            except Exception:
                data = {}
            sid = data.get("sessionId")
            if not sid:
                return respond(400, {"error": "missing sessionId"})

            passed = (hash(sid) % 2 == 0)
            result = {
                "sessionId": sid,
                "liveness": "PASS" if passed else "FAIL",
                "confidence": "0.98",
            }

            # alias reserved attribute name "result" -> "#r"
            table.update_item(
                Key={"pk": f"liveness#{sid}", "sk": "META"},
                UpdateExpression="SET #s = :s, #r = :r",
                ExpressionAttributeNames={
                    "#s": "status",
                    "#r": "result",
                },
                ExpressionAttributeValues={
                    ":s": "done",
                    ":r": json.dumps(result),
                },
            )
            return respond(200, result)

        # ---- KYC submit (mock compare)
        if route == "/kyc/submit" and method == "POST":
            body_raw = event.get("body") or "{}"
            try:
                data = json.loads(body_raw)
            except Exception:
                data = {}

            session = data.get("sessionId")
            id_url = data.get("idUrl")
            selfie_url = data.get("selfieUrl")
            if not session or not id_url or not selfie_url:
                return respond(400, {"error": "missing sessionId, idUrl, or selfieUrl"})

            match = (hash(id_url + selfie_url) % 3 != 0)
            kyc_id = str(uuid.uuid4())

            table.put_item(
                Item={
                    "pk": f"kyc#{session}",  # group records under the session
                    "sk": "META",            # required sort key
                    "kycId": kyc_id,
                    "sessionId": session,
                    "idUrl": id_url,
                    "selfieUrl": selfie_url,
                    "match": str(bool(match)),
                    "created": str(int(time.time())),
                }
            )
            return respond(200, {"kycId": kyc_id, "match": match})

        # ---- Not found
        return respond(404, {"error": "Not Found", "path": route, "method": method})

    except ClientError as ce:
        print(f"[ClientError] {ce}")
        return respond(500, {"error": "AWS client error", "detail": str(ce)})
    except Exception as e:
        print(f"[Unhandled] {e}")
        return respond(500, {"error": "Internal Server Error"})
