#!/bin/bash

# Quick Start Script for Payment Smart Bot Frontend
# This script sets up and runs the Streamlit application

set -e

echo "🚀 Payment Smart Bot Frontend - Quick Start"
echo "=========================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $python_version detected"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate || source venv/Scripts/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo "✅ Dependencies installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your API endpoint:"
    echo "   nano .env"
    echo ""
    read -p "Press Enter to continue (you can configure API in the UI later)..."
else
    echo "✅ .env file found"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Starting Payment Smart Bot Frontend..."
echo "=========================================="
echo ""
echo "📱 The app will open in your browser"
echo "🌐 Default URL: http://localhost:8501"
echo ""
echo "💡 Tip: Configure your API endpoint in the sidebar"
echo "🧪 Test Mode: Use card 4242424242424242"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run Streamlit
streamlit run payment_bot_frontend.py
