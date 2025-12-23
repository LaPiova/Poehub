#!/usr/bin/env python3
"""
Verification script for PoeHub installation
Checks if all dependencies are installed correctly
"""

import sys
import importlib

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    if package_name is None:
        package_name = module_name
    
    try:
        importlib.import_module(module_name)
        print(f"✓ {package_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name} is NOT installed")
        return False

def main():
    print("=" * 50)
    print("PoeHub Installation Verification")
    print("=" * 50)
    print()
    
    required_modules = [
        ("discord", "discord.py"),
        ("redbot.core", "Red-DiscordBot"),
        ("openai", "openai"),
        ("cryptography", "cryptography"),
        ("cryptography.fernet", "cryptography.fernet"),
    ]
    
    all_good = True
    
    print("Checking required dependencies:")
    print("-" * 50)
    
    for module, package in required_modules:
        if not check_import(module, package):
            all_good = False
    
    print("-" * 50)
    print()
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("✗ Python 3.8+ is required")
        all_good = False
    else:
        print("✓ Python version is compatible")
    
    print()
    print("=" * 50)
    
    if all_good:
        print("✓ All checks passed! PoeHub is ready to use.")
        print()
        print("Next steps:")
        print("1. Start your bot: ./start_bot.sh")
        print("2. In Discord: [p]addpath ~/red-cogs")
        print("3. In Discord: [p]load poehub")
        print("4. In Discord: [p]poeapikey <your_key>")
        return 0
    else:
        print("✗ Some dependencies are missing.")
        print()
        print("To install missing dependencies:")
        print("  pip install Red-DiscordBot openai cryptography")
        return 1

if __name__ == "__main__":
    sys.exit(main())

