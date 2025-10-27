resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "echo" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  payload_format_version = "2.0"
  integration_uri        = aws_lambda_function.echo.invoke_arn
}

resource "aws_apigatewayv2_route" "ping" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /ping"
  target    = "integrations/${aws_apigatewayv2_integration.echo.id}"
}
resource "aws_apigatewayv2_route" "echo" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /echo"
  target    = "integrations/${aws_apigatewayv2_integration.echo.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGWInvokeEcho"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.echo.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_apigatewayv2_stage" "live" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_route" "presign" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /presign-id"
  target    = "integrations/${aws_apigatewayv2_integration.echo.id}"
}

resource "aws_apigatewayv2_route" "liveness_start" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /liveness/start"
  target    = "integrations/${aws_apigatewayv2_integration.echo.id}"
}

resource "aws_apigatewayv2_route" "kyc_submit" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /kyc/submit"
  target    = "integrations/${aws_apigatewayv2_integration.echo.id}"
}

