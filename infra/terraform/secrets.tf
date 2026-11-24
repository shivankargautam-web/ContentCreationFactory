resource "random_password" "jwt" {
  length  = 64
  special = false
}

# Fernet keys are 32 url-safe base64-encoded bytes.
resource "random_id" "fernet" {
  byte_length = 32
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/app"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
}

# Provider keys (OpenAI, ElevenLabs, YouTube OAuth) are placeholders; set real values out of band:
#   aws secretsmanager put-secret-value --secret-id <arn> --secret-string file://secrets.json
resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    DATABASE_URL          = "postgresql+asyncpg://acf:${random_password.db.result}@${aws_db_instance.this.address}:5432/acf"
    JWT_SECRET_KEY        = random_password.jwt.result
    TOKEN_ENCRYPTION_KEY  = replace(replace(random_id.fernet.b64_std, "+", "-"), "/", "_")
    OPENAI_API_KEY        = ""
    ELEVENLABS_API_KEY    = ""
    YOUTUBE_CLIENT_ID     = ""
    YOUTUBE_CLIENT_SECRET = ""
    META_APP_ID           = ""
    META_APP_SECRET       = ""
  })
  lifecycle {
    ignore_changes = [secret_string]
  }
}
