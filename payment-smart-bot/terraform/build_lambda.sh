#!/bin/bash
# Build script for Lambda deployment package
# This script installs dependencies and creates a deployment package

set -e  # Exit on error

echo "🔨 Building Lambda deployment package..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAMBDA_DIR="$SCRIPT_DIR/../lambda"
BUILD_DIR="$SCRIPT_DIR/lambda_build"
OUTPUT_ZIP="$SCRIPT_DIR/lambda_function.zip"

# Clean up previous build
echo "🧹 Cleaning up previous build..."
rm -rf "$BUILD_DIR"
rm -f "$OUTPUT_ZIP"

# Create build directory
echo "📁 Creating build directory..."
mkdir -p "$BUILD_DIR"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r "$LAMBDA_DIR/requirements.txt" -t "$BUILD_DIR" --quiet

# Copy Lambda function code
echo "📄 Copying Lambda function code..."
cp "$LAMBDA_DIR/payment_handler.py" "$BUILD_DIR/"

# Remove unnecessary files to reduce package size
echo "🗑️  Removing unnecessary files..."
cd "$BUILD_DIR"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Create ZIP file
echo "📦 Creating deployment package..."
zip -r "$OUTPUT_ZIP" . -q

# Get package size
PACKAGE_SIZE=$(du -h "$OUTPUT_ZIP" | cut -f1)
echo ""
echo "✅ Lambda deployment package created successfully!"
echo "📊 Package size: $PACKAGE_SIZE"
echo "📍 Location: $OUTPUT_ZIP"
echo ""

# Clean up build directory
rm -rf "$BUILD_DIR"

echo "🎉 Build complete!"
