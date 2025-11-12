#!/usr/bin/env python
"""
Script to create .env file from env.example with auto-generated SECRET_KEY.
"""
import os
import sys
from pathlib import Path
from django.core.management.utils import get_random_secret_key

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

def create_env_file():
    """Create .env file from env.example with generated SECRET_KEY."""
    
    env_example_path = BASE_DIR / "env.example"
    env_path = BASE_DIR / ".env"
    
    # Check if .env already exists
    if env_path.exists():
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled. .env file not modified.")
            return False
    
    # Read env.example
    if not env_example_path.exists():
        print(f"❌ Error: {env_example_path} not found!")
        return False
    
    with open(env_example_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Generate SECRET_KEY
    secret_key = get_random_secret_key()
    
    # Replace SECRET_KEY placeholder
    content = content.replace(
        "DJANGO_SECRET_KEY=your-secret-key-here",
        f"DJANGO_SECRET_KEY={secret_key}"
    )
    
    # Add development-friendly defaults
    content = content.replace(
        "EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend"
    )
    
    # Write .env file
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ .env file created successfully!")
    print(f"📁 Location: {env_path}")
    print(f"🔑 SECRET_KEY generated: {secret_key[:20]}...")
    print("\n⚠️  IMPORTANT:")
    print("   - Never commit .env to version control")
    print("   - Keep SECRET_KEY secret")
    print("   - Review and update settings as needed")
    
    return True

if __name__ == "__main__":
    try:
        create_env_file()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

