# IAM Role for Lambda Function
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-lambda-role-${var.environment}"
    }
  )
}

# Policy for CloudWatch Logs
resource "aws_iam_role_policy" "lambda_logging" {
  name = "${var.project_name}-lambda-logging-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-*"
      }
    ]
  })
}

# Policy for DynamoDB Access
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-dynamodb-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.sessions.arn
      }
    ]
  })
}

# Policy for Bedrock Access
resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${var.project_name}-lambda-bedrock-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:Converse",
          "bedrock:ConverseStream"
        ]
        # Allow access to inference profiles in source region and foundation models in all destination regions
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*"
        ]
      }
    ]
  })
}

# Policy for Secrets Manager Access
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${var.project_name}-lambda-secrets-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.stripe_key.arn
      }
    ]
  })
}

# Policy for KMS Decryption
resource "aws_iam_role_policy" "lambda_kms" {
  name = "${var.project_name}-lambda-kms-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.payment_bot.arn
      }
    ]
  })
}

# Policy for X-Ray Tracing (if enabled)
resource "aws_iam_role_policy" "lambda_xray" {
  count = var.enable_xray_tracing ? 1 : 0
  
  name = "${var.project_name}-lambda-xray-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for Bedrock Guardrails (optional, enabled via variable)
# Guardrails provide content filtering for PII, harmful content, etc.
# Cost: $0.15 per 1,000 text units
resource "aws_iam_role_policy" "lambda_guardrails" {
  count = var.enable_bedrock_guardrails ? 1 : 0
  
  name = "${var.project_name}-lambda-guardrails-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:ApplyGuardrail",
          "bedrock:GetGuardrail",
          "bedrock:ListGuardrails"
        ]
        Resource = "*"
      }
    ]
  })
}
