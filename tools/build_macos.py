#!/usr/bin/env python3
"""Build script for creating macOS application bundle with PyInstaller."""

import shutil
import subprocess
import sys
from pathlib import Path


def build_macos_app():
    """Build macOS .app bundle using PyInstaller."""
    
    # Clean previous builds
    dist_dir = Path("dist")
    build_dir = Path("build")
    spec_file = Path("sam_invoice.spec")
    
    if dist_dir.exists():
        print("Cleaning dist directory...")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print("Cleaning build directory...")
        shutil.rmtree(build_dir)
    
    if spec_file.exists():
        print("Removing old spec file...")
        spec_file.unlink()
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=Sam Invoice",
        "--windowed",  # macOS app bundle (no console)
        "--onedir",  # Create a directory containing an executable
        "--icon=logos/icon.icns" if Path("logos/icon.icns").exists() else "",
        "--osx-bundle-identifier=app.sam-invoice",
        "--add-data=sam_invoice/assets:sam_invoice/assets",
        "--add-data=sam_invoice/assets/styles:sam_invoice/assets/styles",
        # Include all necessary packages
        "--hidden-import=sam_invoice.models",
        "--hidden-import=sam_invoice.ui",
        "--hidden-import=sqlalchemy.sql.default_comparator",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=qtawesome",
        # Entry point
        "sam_invoice/app.py",
    ]
    
    # Remove empty strings from command
    cmd = [arg for arg in cmd if arg]
    
    print("Building macOS application...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Build successful!")
        print(f"Application created at: dist/Sam Invoice.app")
        print("\nTo run the application:")
        print("  open 'dist/Sam Invoice.app'")
        print("\nTo create a DMG installer, you can use:")
        print("  create-dmg 'dist/Sam Invoice.app' dist/")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n❌ PyInstaller not found. Install it with:")
        print("  uv add --dev pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    build_macos_app()
