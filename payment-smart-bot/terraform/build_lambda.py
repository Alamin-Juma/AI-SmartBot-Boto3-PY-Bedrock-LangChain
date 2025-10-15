#!/usr/bin/env python3
"""
Build Lambda deployment package with dependencies
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

def main():
    print("🔨 Building Lambda deployment package...")
    
    # Get directories
    script_dir = Path(__file__).parent.absolute()
    lambda_dir = script_dir.parent / "lambda"
    build_dir = script_dir / "lambda_build"
    output_zip = script_dir / "lambda_function.zip"
    
    # Clean up previous build
    print("🧹 Cleaning up previous build...")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if output_zip.exists():
        output_zip.unlink()
    
    # Create build directory
    print("📁 Creating build directory...")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Install dependencies
    print("📦 Installing Python dependencies...")
    requirements_file = lambda_dir / "requirements.txt"
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-t", str(build_dir), "--quiet"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        print(e.stderr.decode())
        return 1
    
    # Copy Lambda function code
    print("📄 Copying Lambda function code...")
    shutil.copy(lambda_dir / "payment_handler.py", build_dir / "payment_handler.py")
    
    # Remove unnecessary files
    print("🗑️  Removing unnecessary files...")
    for root, dirs, files in os.walk(build_dir):
        # Remove __pycache__ directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests', '.pytest_cache', '*.dist-info']]
        
        # Remove .pyc files
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
    
    # Create ZIP file
    print("📦 Creating deployment package...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, build_dir)
                zipf.write(file_path, arcname)
    
    # Get package size
    package_size = output_zip.stat().st_size / (1024 * 1024)  # MB
    print("")
    print("✅ Lambda deployment package created successfully!")
    print(f"📊 Package size: {package_size:.2f} MB")
    print(f"📍 Location: {output_zip}")
    print("")
    
    # Clean up build directory
    shutil.rmtree(build_dir)
    
    print("🎉 Build complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
