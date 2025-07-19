#!/bin/bash
# Setup Development Certificate Authority for mTLS
# Part of the migration from API_KEY to mTLS + JWT authentication

set -e  # Exit on any error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
CERTS_DIR="./certs"
CA_KEY="$CERTS_DIR/ca.key"
CA_CERT="$CERTS_DIR/ca.pem"

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

function log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

function print_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --clean        Remove existing certificates before generating"
    echo "  --jwt-only     Only generate JWT signing keys (no mTLS certs)"
    echo "  --help         Show this help"
    echo ""
    echo "This script sets up a development Certificate Authority and generates"
    echo "certificates for all Gaia microservices to enable mTLS authentication."
}

# Parse command line arguments
CLEAN=false
JWT_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --jwt-only)
            JWT_ONLY=true
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Check prerequisites
if ! command -v openssl &> /dev/null; then
    log_error "OpenSSL is not installed. Please install it first."
    exit 1
fi

# Clean if requested
if [[ "$CLEAN" == "true" ]]; then
    log_step "Cleaning existing certificates..."
    rm -rf "$CERTS_DIR"
fi

# Create certificates directory
log_step "Creating certificates directory..."
mkdir -p "$CERTS_DIR"

# Service list
SERVICES=("gateway" "auth-service" "asset-service" "chat-service" "web-service")

# Generate JWT signing keys
log_step "Generating JWT signing keys..."
if [[ ! -f "$CERTS_DIR/jwt-signing.key" ]]; then
    openssl genrsa -out "$CERTS_DIR/jwt-signing.key" 2048
    openssl rsa -in "$CERTS_DIR/jwt-signing.key" -pubout -out "$CERTS_DIR/jwt-signing.pub"
    log_info "✅ JWT signing keys generated"
else
    log_info "JWT signing keys already exist"
fi

if [[ "$JWT_ONLY" == "true" ]]; then
    log_info "🎉 JWT keys setup complete!"
    exit 0
fi

# Generate CA if it doesn't exist
if [[ ! -f "$CA_KEY" ]] || [[ ! -f "$CA_CERT" ]]; then
    log_step "Generating development Certificate Authority..."
    
    # Generate CA private key
    openssl genrsa -out "$CA_KEY" 4096
    
    # Generate CA certificate
    openssl req -new -x509 -key "$CA_KEY" -out "$CA_CERT" -days 365 \
        -subj "/C=US/ST=California/L=San Francisco/O=Gaia Development/CN=Gaia Development CA"
    
    log_info "✅ Development CA created"
else
    log_info "Development CA already exists"
fi

# Generate certificates for each service
for service in "${SERVICES[@]}"; do
    log_step "Generating certificates for $service..."
    
    SERVICE_DIR="$CERTS_DIR/$service"
    mkdir -p "$SERVICE_DIR"
    
    # Skip if certificate already exists
    if [[ -f "$SERVICE_DIR/cert.pem" ]] && [[ -f "$SERVICE_DIR/key.pem" ]]; then
        log_info "Certificate for $service already exists"
        continue
    fi
    
    # Generate private key
    openssl genrsa -out "$SERVICE_DIR/key.pem" 2048
    
    # Create certificate config
    cat > "$SERVICE_DIR/cert.conf" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = California
L = San Francisco
O = Gaia Development
CN = $service

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $service
DNS.2 = $service.internal
DNS.3 = localhost
IP.1 = 127.0.0.1
EOF
    
    # Generate certificate signing request
    openssl req -new -key "$SERVICE_DIR/key.pem" -out "$SERVICE_DIR/csr.pem" \
        -config "$SERVICE_DIR/cert.conf"
    
    # Sign certificate with CA
    openssl x509 -req -in "$SERVICE_DIR/csr.pem" -CA "$CA_CERT" -CAkey "$CA_KEY" \
        -out "$SERVICE_DIR/cert.pem" -days 365 -CAcreateserial \
        -extensions v3_req -extfile "$SERVICE_DIR/cert.conf"
    
    # Clean up temporary files
    rm "$SERVICE_DIR/csr.pem" "$SERVICE_DIR/cert.conf"
    
    log_info "✅ Certificate generated for $service"
done

# Create a combined CA bundle for clients
log_step "Creating CA bundle..."
cp "$CA_CERT" "$CERTS_DIR/ca-bundle.pem"

# Display summary
log_info "🎉 Development certificates setup complete!"
echo ""
log_info "Certificate locations:"
echo "  CA Certificate: $CA_CERT"
echo "  JWT Signing Key: $CERTS_DIR/jwt-signing.key"
echo ""
log_info "Service certificates:"
for service in "${SERVICES[@]}"; do
    echo "  $service:"
    echo "    Certificate: $CERTS_DIR/$service/cert.pem"
    echo "    Private Key: $CERTS_DIR/$service/key.pem"
done
echo ""
log_info "Next steps:"
echo "  1. Start services with: docker compose up"
echo "  2. Services will automatically use these certificates"
echo "  3. Test with: ./scripts/test-jwt-auth.sh"