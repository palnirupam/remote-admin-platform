#!/usr/bin/env python3
"""
Quick script to start the Web UI for Remote Admin Platform
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from remote_system.enhanced_server.enhanced_server import EnhancedServer
from remote_system.web_ui.rest_api import RESTAPIServer

def main():
    print("🚀 Starting Remote Admin Platform Web UI...")
    print("=" * 60)
    
    # Create enhanced server
    print("📡 Initializing Enhanced Server...")
    server = EnhancedServer(
        host="0.0.0.0",
        port=9999,
        db_path="./remote_system.db",
        use_tls=True
    )
    
    # Create REST API server
    print("🌐 Initializing REST API Server...")
    api_server = RESTAPIServer(
        core_server=server,
        port=8080,
        web_username="admin",
        web_password="admin"
    )
    
    # Start both servers
    print("\n✅ Starting servers...")
    server.start()
    api_server.start()
    
    print("\n" + "=" * 60)
    print("✅ Web UI is now running!")
    print("=" * 60)
    print("\n📊 Access the Web UI:")
    print("   URL: http://localhost:8080")
    print("   Username: admin")
    print("   Password: admin")
    print("\n📡 Server listening on:")
    print("   Host: 0.0.0.0")
    print("   Port: 9999")
    print("\n⚠️  Press Ctrl+C to stop the servers")
    print("=" * 60)
    
    try:
        # Keep the script running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down servers...")
        print("✅ Servers stopped successfully!")

if __name__ == "__main__":
    main()
