#!/bin/bash

# Gaia Platform Setup Script
# This script helps set up the Gaia Platform development environment

set -e

echo "🚀 Setting up Gaia Platform..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the Gaia Platform root directory"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please update with your configuration values."
else
    echo "📝 .env file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data/kb
mkdir -p data/wiki
mkdir -p tests
mkdir -p logs

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Error: docker-compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "🔧 Building Docker images..."
docker-compose build

echo "🗄️  Setting up database..."
docker-compose up -d db nats

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Test database connection
echo "🔍 Testing database connection..."
docker-compose exec -T db psql -U postgres -d llm_platform -c "SELECT 1;" > /dev/null 2>&1 || {
    echo "⚠️  Database not ready yet, waiting longer..."
    sleep 20
    docker-compose exec -T db psql -U postgres -d llm_platform -c "SELECT 1;" > /dev/null 2>&1 || {
        echo "❌ Error: Could not connect to database"
        exit 1
    }
}

echo "✅ Database is ready"

# Test NATS connection
echo "🔍 Testing NATS connection..."
timeout 10 docker-compose exec -T nats nats-server --version > /dev/null 2>&1 || {
    echo "⚠️  NATS may not be fully ready, but continuing..."
}

echo "✅ NATS is ready"

echo "🎯 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update your .env file with proper configuration values"
echo "2. Start all services: docker-compose up"
echo "3. Test the gateway: curl http://localhost:8666/health"
echo ""
echo "Available services:"
echo "- Gateway (main entry): http://localhost:8666"
echo "- Database: localhost:5432"
echo "- NATS: localhost:4222 (monitoring: http://localhost:8222)"
echo ""
echo "Development commands:"
echo "- Start services: docker-compose up"
echo "- View logs: docker-compose logs -f [service-name]"
echo "- Stop services: docker-compose down"
echo "- Rebuild: docker-compose build"
echo "- Run tests: docker-compose run test"
