# ─────────────────────────────────────────────────────────────
# main.tf — Práctica del Módulo 7
#
# ⚠️  ESTE ARCHIVO TIENE PROBLEMAS A PROPÓSITO.
#     Sirve para que el escáner de IaC (Checkov) encuentre
#     hallazgos reales. La versión corregida está en main_seguro.tf
#
# Nota: no hace falta cuenta de AWS. Checkov analiza el ARCHIVO,
# no la infraestructura: nunca se ejecuta terraform apply acá.
# ─────────────────────────────────────────────────────────────

provider "aws" {
  region = "us-east-1"
}

# ── PROBLEMA 1 — Bucket sin cifrado y sin versionado ──
# Checkov: CKV_AWS_19, CKV_AWS_21
resource "aws_s3_bucket" "datos" {
  bucket = "mi-bucket-de-prueba-modulo7"

  # Falta: server_side_encryption_configuration
  # Falta: versioning
  # Falta: tags obligatorias  ← esto también es un problema de FinOps
}

# ── PROBLEMA 2 — Bucket accesible públicamente ──
# Checkov: CKV_AWS_20
resource "aws_s3_bucket_acl" "datos_acl" {
  bucket = aws_s3_bucket.datos.id
  acl    = "public-read"
}

# ── PROBLEMA 3 — Security group abierto al mundo entero ──
# Checkov: CKV_AWS_24 (SSH abierto a 0.0.0.0/0)
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Security group de la app"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # ← cualquiera en internet puede intentar entrar
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── PROBLEMA 4 — Instancia sobredimensionada y sin etiquetas ──
# No es un hallazgo de seguridad: es un problema de FinOps.
# Sin tags no sabés de quién es este recurso ni a qué proyecto cobrárselo.
resource "aws_instance" "api" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "m5.4xlarge"   # 16 vCPU · 64 GB para una API chica

  # Falta: tags
  # Falta: metadata_options con http_tokens = "required" (IMDSv2)
}
