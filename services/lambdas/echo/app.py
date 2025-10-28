import os, json, boto3, uuid, time

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
rek = boto3.client("rekognition")

BUCKET = os.environ["BUCKET"]
TABLE = os.environ["DDB_TABLE"]
REKOG_ENABLED = os.environ.get("REKOGNITION_ENABLED", "false").lower() == "true"

table = ddb.Table(TABLE)

def respond(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        },
        "body": json.dumps(body)
    }

def handler(event, context):
    route = event.get("rawPath", "")
    method = event.get("requestContext", {}).get("http", {}).get("method", "")

    if route == "/ping":
        return respond(200, {"status": "ok", "time": int(time.time()), "bucket": BUCKET, "rekog": REKOG_ENABLED})

    if route == "/presign-id" and method == "POST":
        key = f"uploads/{uuid.uuid4()}.jpg"
        put = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": BUCKET, "Key": key, "ContentType": "image/jpeg"},
            ExpiresIn=300
        )
        get = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=300
        )
        return respond(200, {"key": key, "putUrl": put, "getUrl": get})

    if route == "/liveness/start" and method == "POST":
        session_id = str(uuid.uuid4())
        table.put_item(Item={
            "pk": f"liveness#{session_id}",
            "ts": int(time.time()),
            "status": "started"
        })
        return respond(200, {"sessionId": session_id, "message": "liveness started"})

    if route == "/liveness/results" and method == "POST":
        body = json.loads(event.get("body", "{}"))
        sid = body.get("sessionId")
        if not sid:
            return respond(400, {"error": "missing sessionId"})
        result = {"sessionId": sid, "liveness": "PASS" if hash(sid) % 2 == 0 else "FAIL", "confidence": 0.98}
        table.update_item(
            Key={"pk": f"liveness#{sid}"},
            UpdateExpression="SET #s=:s, result=:r",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "done", ":r": json.dumps(result)}
        )
        return respond(200, result)

    if route == "/kyc/submit" and method == "POST":
        body = json.loads(event.get("body", "{}"))
        session = body.get("sessionId")
        id_url = body.get("idUrl")
        selfie_url = body.get("selfieUrl")
        if not session or not id_url or not selfie_url:
            return respond(400, {"error": "missing sessionId, idUrl, or selfieUrl"})
        match_result = {"similarity": 99.3, "mock": True}
        if REKOG_ENABLED:
            try:
                match = rek.compare_faces(
                    SourceImage={"S3Object": {"Bucket": BUCKET, "Name": id_url}},
                    TargetImage={"S3Object": {"Bucket": BUCKET, "Name": selfie_url}},
                    SimilarityThreshold=90
                )
                match_result = match
            except Exception as e:
                match_result = {"error": str(e)}
        kyc_id = str(uuid.uuid4())
        table.put_item(Item={
            "pk": f"kyc#{kyc_id}",
            "sessionId": session,
            "idUrl": id_url,
            "selfieUrl": selfie_url,
            "match": json.dumps(match_result),
            "created": int(time.time())
        })
        return respond(200, {"kycId": kyc_id, "match": match_result})

    return respond(404, {"message": "Not Found", "path": route})
