# API Gateway REST API
resource "aws_api_gateway_rest_api" "payment_api" {
  name        = "${var.project_name}-api-${var.environment}"
  description = "Payment Smart Bot API"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-api-${var.environment}"
    }
  )
}

# API Gateway Resource: /chat
resource "aws_api_gateway_resource" "chat" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  parent_id   = aws_api_gateway_rest_api.payment_api.root_resource_id
  path_part   = "chat"
}

# POST /chat method
resource "aws_api_gateway_method" "chat_post" {
  rest_api_id   = aws_api_gateway_rest_api.payment_api.id
  resource_id   = aws_api_gateway_resource.chat.id
  http_method   = "POST"
  authorization = "NONE"  # Change to "AWS_IAM" or add API key for production
  
  request_parameters = {
    "method.request.header.Content-Type" = true
  }
}

# Integration with Lambda
resource "aws_api_gateway_integration" "chat_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.payment_api.id
  resource_id             = aws_api_gateway_resource.chat.id
  http_method             = aws_api_gateway_method.chat_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.payment_handler.invoke_arn
}

# CORS: OPTIONS method for /chat
resource "aws_api_gateway_method" "chat_options" {
  rest_api_id   = aws_api_gateway_rest_api.payment_api.id
  resource_id   = aws_api_gateway_resource.chat.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "chat_options" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  resource_id = aws_api_gateway_resource.chat.id
  http_method = aws_api_gateway_method.chat_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "chat_options_200" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  resource_id = aws_api_gateway_resource.chat.id
  http_method = aws_api_gateway_method.chat_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
  
  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "chat_options" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  resource_id = aws_api_gateway_resource.chat.id
  http_method = aws_api_gateway_method.chat_options.http_method
  status_code = aws_api_gateway_method_response.chat_options_200.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
  
  depends_on = [aws_api_gateway_integration.chat_options]
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.payment_api.id
  
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.chat.id,
      aws_api_gateway_method.chat_post.id,
      aws_api_gateway_integration.chat_lambda.id,
    ]))
  }
  
  lifecycle {
    create_before_destroy = true
  }
  
  depends_on = [
    aws_api_gateway_integration.chat_lambda,
    aws_api_gateway_integration.chat_options
  ]
}

# API Gateway Stage
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.payment_api.id
  stage_name    = var.environment
  
  # Enable CloudWatch logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
  
  # Enable X-Ray tracing
  xray_tracing_enabled = var.enable_xray_tracing
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-api-stage-${var.environment}"
    }
  )
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = var.cloudwatch_log_retention_days
  # Don't use KMS encryption for CloudWatch Logs - causes permission issues
  # kms_key_id        = aws_kms_key.payment_bot.arn
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-api-logs-${var.environment}"
    }
  )
}

# API Gateway Usage Plan (Rate Limiting)
resource "aws_api_gateway_usage_plan" "main" {
  name        = "${var.project_name}-usage-plan-${var.environment}"
  description = "Usage plan for payment bot API"
  
  api_stages {
    api_id = aws_api_gateway_rest_api.payment_api.id
    stage  = aws_api_gateway_stage.main.stage_name
  }
  
  throttle_settings {
    rate_limit  = var.api_throttle_rate
    burst_limit = var.api_throttle_burst
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-usage-plan-${var.environment}"
    }
  )
}

# Optional: API Key (uncomment if needed)
# resource "aws_api_gateway_api_key" "main" {
#   name    = "${var.project_name}-api-key-${var.environment}"
#   enabled = true
#   
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.project_name}-api-key-${var.environment}"
#     }
#   )
# }
# 
# resource "aws_api_gateway_usage_plan_key" "main" {
#   key_id        = aws_api_gateway_api_key.main.id
#   key_type      = "API_KEY"
#   usage_plan_id = aws_api_gateway_usage_plan.main.id
# }
