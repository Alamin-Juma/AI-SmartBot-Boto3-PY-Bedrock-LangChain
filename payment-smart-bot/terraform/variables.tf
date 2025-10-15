variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "payment-smart-bot"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID or inference profile ID to use"
  type        = string
  default     = "us.meta.llama3-2-1b-instruct-v1:0"
}

variable "stripe_secret_key" {
  description = "Stripe API secret key (will be stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "lambda_memory_size" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PAY_PER_REQUEST or PROVISIONED)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "session_ttl_hours" {
  description = "Session TTL in hours (auto-delete old sessions)"
  type        = number
  default     = 1
}

variable "enable_bedrock_guardrails" {
  description = "Enable Bedrock Guardrails for content filtering"
  type        = bool
  default     = false
}

variable "api_throttle_rate" {
  description = "API Gateway throttle rate (requests per second)"
  type        = number
  default     = 10
}

variable "api_throttle_burst" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 20
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing for Lambda"
  type        = bool
  default     = true
}

variable "bedrock_token_threshold" {
  description = "Daily Bedrock token usage threshold for CloudWatch alarm"
  type        = number
  default     = 100000  # 100k tokens/day (~$1.50 at Llama 3.2 1B pricing)
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
