#!/bin/bash
# Deploy Gaia Platform to Fly.io Staging Environment

set -e

echo "🚀 Deploying Gaia Platform to Fly.io Staging..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_status() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "fly.staging.toml" ]; then
    print_error "fly.staging.toml not found. Make sure you're in the Gaia project root."
    exit 1
fi

# Deploy services in dependency order
print_status "Deploying NATS Message Broker"
flyctl deploy --config fly.nats.toml --app gaia-nats-staging --build-arg SERVICE=nats || {
    print_warning "NATS deployment failed, creating new app..."
    flyctl apps create gaia-nats-staging --org aeonia-dev
    flyctl deploy --config fly.nats.toml --app gaia-nats-staging --build-arg SERVICE=nats
}
print_success "NATS deployed"

print_status "Deploying Auth Service"
flyctl deploy --config fly.auth.toml --app gaia-auth-staging --build-arg SERVICE=auth || {
    print_warning "Auth service deployment failed, creating new app..."
    flyctl apps create gaia-auth-staging --org aeonia-dev
    flyctl deploy --config fly.auth.toml --app gaia-auth-staging --build-arg SERVICE=auth
}
print_success "Auth Service deployed"

print_status "Deploying Asset Service"
flyctl deploy --config fly.asset.toml --app gaia-asset-staging --build-arg SERVICE=asset || {
    print_warning "Asset service deployment failed, creating new app..."
    flyctl apps create gaia-asset-staging --org aeonia-dev
    flyctl deploy --config fly.asset.toml --app gaia-asset-staging --build-arg SERVICE=asset
}
print_success "Asset Service deployed"

print_status "Deploying Chat Service"
flyctl deploy --config fly.chat.toml --app gaia-chat-staging --build-arg SERVICE=chat || {
    print_warning "Chat service deployment failed, creating new app..."
    flyctl apps create gaia-chat-staging --org aeonia-dev
    flyctl deploy --config fly.chat.toml --app gaia-chat-staging --build-arg SERVICE=chat
}
print_success "Chat Service deployed"

print_status "Deploying Gateway Service"
flyctl deploy --config fly.staging.toml --app gaia-gateway-staging || {
    print_warning "Gateway deployment failed, creating new app..."
    flyctl apps create gaia-gateway-staging --org aeonia-dev
    flyctl deploy --config fly.staging.toml --app gaia-gateway-staging
}
print_success "Gateway Service deployed"

print_status "Deployment Summary"
echo "🌐 Staging URLs:"
echo "  Gateway:  https://gaia-gateway-staging.fly.dev"
echo "  Auth:     https://gaia-auth-staging.fly.dev"
echo "  Asset:    https://gaia-asset-staging.fly.dev"
echo "  Chat:     https://gaia-chat-staging.fly.dev"
echo "  NATS:     https://gaia-nats-staging.fly.dev"

print_status "Running Health Checks"
sleep 10  # Give services time to start

echo "Testing Gateway health..."
curl -s https://gaia-gateway-staging.fly.dev/health | jq . || print_warning "Gateway health check failed"

echo "Testing Auth service health..."
curl -s https://gaia-auth-staging.fly.dev/health | jq . || print_warning "Auth health check failed"

echo "Testing Chat service health..."
curl -s https://gaia-chat-staging.fly.dev/health | jq . || print_warning "Chat health check failed"

echo "Testing Asset service health..."
curl -s https://gaia-asset-staging.fly.dev/health | jq . || print_warning "Asset health check failed"

print_success "Gaia Platform Staging Deployment Complete!"
echo ""
echo "🎯 Next Steps:"
echo "  1. Test the API: curl https://gaia-gateway-staging.fly.dev/health"
echo "  2. Run integration tests with staging endpoints"
echo "  3. Deploy to production when ready: ./scripts/deploy-prod.sh"