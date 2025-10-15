# Payment Smart Bot - Terraform Configuration
# Provisions all AWS resources: Lambda, API Gateway, DynamoDB, Secrets Manager, IAM, CloudWatch

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
  
  # Optional: Use S3 backend for state management
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "payment-smart-bot/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "PaymentSmartBot"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "Alamin-Juma"
    }
  }
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# CloudWatch Alarm for Bedrock Token Usage
# Alerts when daily token consumption exceeds threshold
resource "aws_cloudwatch_metric_alarm" "bedrock_token_usage" {
  alarm_name          = "${var.project_name}-bedrock-token-usage-${var.environment}"
  alarm_description   = "Alert when Bedrock input token usage exceeds daily threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "InputTokenCount"
  namespace           = "AWS/Bedrock"
  period              = "86400"  # Daily (24 hours)
  statistic           = "Sum"
  threshold           = var.bedrock_token_threshold
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ModelId = var.bedrock_model_id
  }
  
  alarm_actions = []  # Add SNS topic ARN here for notifications
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-bedrock-token-alarm-${var.environment}"
      Component = "Monitoring"
    }
  )
}

data "aws_region" "current" {}
