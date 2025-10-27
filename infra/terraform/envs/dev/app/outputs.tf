output "api_base_url" {
  value = aws_apigatewayv2_api.http.api_endpoint
}
output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}
output "ddb_table" {
  value = aws_dynamodb_table.sessions.name
}
output "lambda_echo" {
  value = aws_lambda_function.echo.function_name
}
output "ecr_repo" {
  value = aws_ecr_repository.echo.repository_url
}
