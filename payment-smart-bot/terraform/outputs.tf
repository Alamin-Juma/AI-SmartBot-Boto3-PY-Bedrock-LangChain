output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/chat"
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.payment_handler.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.payment_handler.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB sessions table name"
  value       = aws_dynamodb_table.sessions.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB sessions table ARN"
  value       = aws_dynamodb_table.sessions.arn
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN for Stripe key"
  value       = aws_secretsmanager_secret.stripe_key.arn
  sensitive   = true
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.payment_bot.key_id
}

output "kms_key_arn" {
  description = "KMS key ARN"
  value       = aws_kms_key.payment_bot.arn
}

output "cloudwatch_log_group_lambda" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "cloudwatch_log_group_api" {
  description = "CloudWatch log group for API Gateway"
  value       = aws_cloudwatch_log_group.api_gateway_logs.name
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.payment_api.id
}

output "api_gateway_stage" {
  description = "API Gateway stage name"
  value       = aws_api_gateway_stage.main.stage_name
}

output "iam_role_arn" {
  description = "IAM role ARN for Lambda"
  value       = aws_iam_role.lambda_role.arn
}

output "curl_test_command" {
  description = "Sample curl command to test the API"
  value = <<-EOT
    curl -X POST ${aws_api_gateway_stage.main.invoke_url}/chat \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-123", "message": "I want to make a payment"}'
  EOT
}

output "bedrock_token_alarm_name" {
  description = "CloudWatch alarm name for Bedrock token usage monitoring"
  value       = aws_cloudwatch_metric_alarm.bedrock_token_usage.alarm_name
}

output "bedrock_token_threshold" {
  description = "Daily token usage threshold that triggers the alarm"
  value       = var.bedrock_token_threshold
}
