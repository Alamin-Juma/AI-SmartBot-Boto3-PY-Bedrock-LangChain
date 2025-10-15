# DynamoDB Table for Session Management
resource "aws_dynamodb_table" "sessions" {
  name         = "${var.project_name}-sessions-${var.environment}"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "sessionId"
  
  attribute {
    name = "sessionId"
    type = "S"
  }
  
  # TTL to auto-delete expired sessions
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  # Point-in-time recovery for production
  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }
  
  # Server-side encryption with KMS
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.payment_bot.arn
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-sessions-${var.environment}"
    }
  )
}

# KMS Key for encryption
resource "aws_kms_key" "payment_bot" {
  description             = "KMS key for Payment Smart Bot encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-kms-${var.environment}"
    }
  )
}

resource "aws_kms_alias" "payment_bot" {
  name          = "alias/${var.project_name}-${var.environment}"
  target_key_id = aws_kms_key.payment_bot.key_id
}

# Secrets Manager for Stripe API Key
resource "aws_secretsmanager_secret" "stripe_key" {
  name                    = "${var.project_name}/stripe-key-${var.environment}"
  description             = "Stripe API secret key for payment processing"
  kms_key_id             = aws_kms_key.payment_bot.id
  recovery_window_in_days = 7
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-stripe-secret-${var.environment}"
    }
  )
}

resource "aws_secretsmanager_secret_version" "stripe_key" {
  secret_id     = aws_secretsmanager_secret.stripe_key.id
  secret_string = jsonencode({
    STRIPE_SECRET_KEY = var.stripe_secret_key
  })
}
