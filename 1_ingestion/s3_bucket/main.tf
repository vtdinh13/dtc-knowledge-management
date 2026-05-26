terraform {
  required_version = "~> 1.15.4"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
}

resource "aws_s3_bucket" "dtc_ingestion_bucket" {
  bucket = "dtc-ingestion-bucket"
}

resource "aws_iam_user" "dtc_ingestion_user" {
  name = "dtc-ingestion-user"
}

resource "aws_iam_policy" "dtc_ingestion_s3_policy" {
  name = "dtc-ingestion-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.dtc_ingestion_bucket.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.dtc_ingestion_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "dtc_ingestion_attach" {
  user       = aws_iam_user.dtc_ingestion_user.name
  policy_arn = aws_iam_policy.dtc_ingestion_s3_policy.arn
}

resource "aws_iam_access_key" "dtc_ingestion" {
  user = aws_iam_user.dtc_ingestion_user.name
}