output "cf_domain" { value = aws_cloudfront_distribution.web.domain_name }
output "cf_id" { value = aws_cloudfront_distribution.web.id }
output "s3_bucket" { value = aws_s3_bucket.web.bucket }
