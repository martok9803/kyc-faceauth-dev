terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.60.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "${var.project}-${var.env}"
}

resource "aws_s3_bucket" "web" {
  bucket        = "${local.name_prefix}-web"
  force_destroy = true
  tags = {
    Project     = var.project
    Environment = var.env
    Owner       = var.owner
  }
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "web" {
  bucket = aws_s3_bucket.web.id
  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${local.name_prefix}-oac"
  description                       = "Access control for ${aws_s3_bucket.web.bucket}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  comment             = "${local.name_prefix}-web"
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = aws_s3_bucket.web.id
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = aws_s3_bucket.web.id
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Project     = var.project
    Environment = var.env
    Owner       = var.owner
  }
}

# bucket policy that allows ONLY this CloudFront distribution to read objects
resource "aws_s3_bucket_policy" "cf_access" {
  bucket = aws_s3_bucket.web.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowCloudFrontReadFromOAC",
        Effect    = "Allow",
        Principal = { "Service" : "cloudfront.amazonaws.com" },
        Action    = ["s3:GetObject"],
        Resource  = "arn:aws:s3:::${aws_s3_bucket.web.bucket}/*",
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.web.arn
          }
        }
      }
    ]
  })
  depends_on = [aws_cloudfront_distribution.web] # ensure exact ARN exists
}
