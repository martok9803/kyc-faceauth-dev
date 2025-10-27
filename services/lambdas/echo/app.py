import os, json, time, boto3

DDB     = boto3.client("dynamodb")
TABLE   = os.environ.get("DDB_TABLE","")
BUCKET  = os.environ.get("BUCKET","")

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body)
    }

def handler(event, context):
    path = event.get("rawPath", "/")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    if path == "/ping" and method == "GET":
        return _resp(200, {"ok": True, "ts": int(time.time()), "bucket": BUCKET, "table": TABLE})

    try:
        body = json.loads(event.get("body") or "{}")
    except Exception:
        body = {}

    pk = f"echo#{int(time.time())}"
    DDB.put_item(
        TableName=TABLE,
        Item={"pk": {"S": pk}, "sk": {"S": "v1"}, "payload": {"S": json.dumps(body)[:1000]}}
    )
    return _resp(200, {"saved": pk, "echo": body})
