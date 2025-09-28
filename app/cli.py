#!/usr/bin/env python3
"""
Command-line interface for Research Magnet.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_setup():
    """Test the basic setup without external dependencies."""
    print("🔍 Testing Research Magnet setup...\n")
    
    try:
        # Test basic Python modules
        import json
        import datetime
        print("✓ Basic Python modules imported successfully")
        
        # Test our app modules (without external deps)
        from app.config import Settings
        print("✓ App config module imported successfully")
        
        # Test our models (without external deps)
        from app.models import ResearchRun, DataSource, ResearchItem
        print("✓ App models imported successfully")
        
        # Test our schemas (without external deps)
        from app.schemas import ResearchRun as ResearchRunSchema
        print("✓ App schemas imported successfully")
        
        print("\n🎉 All core modules imported successfully!")
        print("📦 Next step: Install dependencies with 'pip install -e .'")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 This is expected if dependencies aren't installed yet.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_database():
    """Test database setup."""
    print("\n🗄️ Testing database setup...")
    
    try:
        # Check if database file exists
        db_path = Path("research_magnet.db")
        if db_path.exists():
            print("✓ Database file exists")
        else:
            print("ℹ️ Database file will be created on first run")
        
        # Check if migrations directory exists
        migrations_dir = Path("alembic/versions")
        if migrations_dir.exists():
            migration_files = list(migrations_dir.glob("*.py"))
            if migration_files:
                print(f"✓ Found {len(migration_files)} migration file(s)")
            else:
                print("ℹ️ No migration files found")
        else:
            print("❌ Migrations directory not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def show_instructions():
    """Show setup instructions."""
    print("\n📋 Setup Instructions:")
    print("1. Create virtual environment:")
    print("   python3.11 -m venv venv")
    print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
    print()
    print("2. Install dependencies:")
    print("   pip install -e .")
    print()
    print("3. Copy environment template:")
    print("   cp env.sample .env")
    print()
    print("4. Configure API keys in .env file")
    print()
    print("5. Run the application:")
    print("   uvicorn app.main:app --reload")
    print()
    print("6. Access the API documentation at: http://localhost:8000/docs")

def start_server():
    """Start the FastAPI server."""
    print("🚀 Starting Research Magnet server...")
    print("📡 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

def run_ingestion():
    """Run a quick ingestion test."""
    print("🔍 Running ingestion test...")
    print("ℹ️ This will test data collection from all sources")
    print()
    
    try:
        import requests
        import json
        
        # Test sources status
        print("📊 Checking sources status...")
        response = requests.get("http://localhost:8000/ingest/sources/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Sources status: {status}")
        else:
            print(f"❌ Failed to check sources: {response.status_code}")
            return
        
        # Run ingestion
        print("\n📥 Running ingestion (1 day, low thresholds)...")
        response = requests.get(
            "http://localhost:8000/ingest/run?days=1&min_score=5&min_comments=2", 
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ingestion completed!")
            print(f"📊 Total items: {result['total_items']}")
            print(f"📈 Source stats: {result['source_stats']}")
        else:
            print(f"❌ Ingestion failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running with: python -m app.cli start")
    except Exception as e:
        print(f"❌ Error running ingestion: {e}")

def main():
    """Main CLI entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test-setup":
            success = test_setup()
            success &= test_database()
            
            if success:
                print("\n✅ Setup verification completed successfully!")
                show_instructions()
            else:
                print("\n❌ Setup verification failed. Please check the errors above.")
                sys.exit(1)
        
        elif command == "start":
            start_server()
        
        elif command == "ingest":
            run_ingestion()
        
        elif command == "run-research":
            print("🚀 Starting research pipeline...")
            print("ℹ️ This feature will be implemented in Phase 1")
            # TODO: Implement research pipeline
        
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: test-setup, start, ingest, run-research")
            sys.exit(1)
    else:
        print("Research Magnet CLI")
        print("Available commands:")
        print("  test-setup    - Test the basic setup")
        print("  start         - Start the FastAPI server")
        print("  ingest        - Run a quick ingestion test")
        print("  run-research  - Run the research pipeline")
        print()
        print("Usage: python -m app.cli <command>")
        print()
        print("Quick start:")
        print("  1. python -m app.cli test-setup")
        print("  2. python -m app.cli start")
        print("  3. python -m app.cli ingest  # In another terminal")

if __name__ == "__main__":
    main()
