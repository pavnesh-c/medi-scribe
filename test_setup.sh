#!/bin/bash

echo "🚀 Testing Medi-Scribe Setup"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start the containers
echo "📦 Building and starting containers..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Test backend health
echo "🔍 Testing backend health..."
if curl -s http://localhost:5000/api/v1/health | grep -q "ok"; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    docker-compose logs backend
    exit 1
fi

# Test database connection
echo "🔍 Testing database connection..."
if docker-compose exec backend flask db current | grep -q "head"; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed"
    docker-compose logs db
    exit 1
fi

# Test frontend
echo "🔍 Testing frontend..."
if curl -s http://localhost:3000 | grep -q "Medi-Scribe"; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend check failed"
    docker-compose logs frontend
    exit 1
fi

echo "✨ All tests passed! The application is running at:"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:5000/api/v1"
echo "Database: localhost:3306"

# Keep containers running for manual testing
echo "📝 You can now test the application manually."
echo "To stop the containers, run: docker-compose down" 