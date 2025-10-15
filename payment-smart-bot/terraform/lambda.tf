# Build Lambda deployment package with dependencies
# Run: python build_lambda.py before terraform apply

# Lambda Function
resource "aws_lambda_function" "payment_handler" {
  filename         = "${path.module}/lambda_function.zip"
  function_name    = "${var.project_name}-handler-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "payment_handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/lambda_function.zip")
  runtime         = "python3.11"
  
  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout
  
  environment {
    variables = {
      BEDROCK_MODEL_ID    = var.bedrock_model_id
      DYNAMODB_TABLE      = aws_dynamodb_table.sessions.name
      STRIPE_SECRET_ARN   = aws_secretsmanager_secret.stripe_key.arn
      # AWS_REGION is automatically set by Lambda - don't override it
      ENVIRONMENT         = var.environment
      SESSION_TTL_HOURS   = var.session_ttl_hours
    }
  }
  
  # X-Ray tracing
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }
  
  # VPC configuration (optional - uncomment if needed for security)
  # vpc_config {
  #   subnet_ids         = var.lambda_subnet_ids
  #   security_group_ids = [aws_security_group.lambda_sg.id]
  # }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-handler-${var.environment}"
    }
  )
  
  depends_on = [
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_dynamodb,
    aws_iam_role_policy.lambda_bedrock,
    aws_iam_role_policy.lambda_secrets,
    aws_iam_role_policy.lambda_kms
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.payment_handler.function_name}"
  retention_in_days = var.cloudwatch_log_retention_days
  # Don't use KMS encryption for CloudWatch Logs - causes permission issues
  # kms_key_id        = aws_kms_key.payment_bot.arn
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-lambda-logs-${var.environment}"
    }
  )
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.payment_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.payment_api.execution_arn}/*/*"
}

# CloudWatch Alarm for Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This alarm monitors Lambda function errors"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = aws_lambda_function.payment_handler.function_name
  }
  
  # Optional: Add SNS topic for notifications
  # alarm_actions = [aws_sns_topic.alerts.arn]
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-lambda-errors-alarm-${var.environment}"
    }
  )
}

# CloudWatch Alarm for Lambda Duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-lambda-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "25000"  # 25 seconds (close to timeout)
  alarm_description   = "This alarm monitors Lambda function duration"
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = aws_lambda_function.payment_handler.function_name
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-lambda-duration-alarm-${var.environment}"
    }
  )
}
