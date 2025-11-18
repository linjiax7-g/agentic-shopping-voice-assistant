#!/bin/bash

# Voice Assistant Frontend Startup Script

echo "==================================="
echo "Voice Assistant Frontend"
echo "==================================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "Warning: .env.local not found!"
    if [ -f "env.local.example" ]; then
        cp env.local.example .env.local
        echo "Created .env.local from example"
    fi
    echo ""
fi

echo "Starting Next.js development server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "Make sure backend is running at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm run dev

