"""
HephAIstos - Autonomous Coding Assistant
Entry point for the application.
"""

import os
import sys
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    required_vars = ["GROQ_API_KEY", "EXA_API_KEY", "OPENAI_API_KEY"]
    
    missing_required = [var for var in required_vars if not os.getenv(var)]
    
    if missing_required:
        print("Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        print("\nPlease check your .env file or set these environment variables.")
        print("Example .env file:")
        print("GROQ_API_KEY=your_groq_api_key_here")
        return 1
    
    try:
        from hephaistus.ui.cli import cli
        cli()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return 0
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())