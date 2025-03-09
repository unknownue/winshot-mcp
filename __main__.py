#!/usr/bin/env python3
"""
Main entry point for Winshot MCP

This script provides a unified entry point for both the server and client components.
"""

import argparse
import asyncio
import sys

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Winshot MCP - Window Screenshot Integration for Cursor")
    parser.add_argument("component", choices=["server", "client"], help="Component to run (server or client)")
    parser.add_argument("--port", type=int, default=8765, help="Port for the server (server component only)")
    
    args = parser.parse_args()
    
    if args.component == "server":
        # Import and run the server
        from server.mcp_server import main as server_main
        sys.argv = [sys.argv[0]]  # Reset argv to avoid conflicts with server's argument parser
        if args.port != 8765:
            sys.argv.extend(["--port", str(args.port)])
        server_main()
    
    elif args.component == "client":
        # Import and run the client
        from client.demo import main as client_main
        asyncio.run(client_main())

if __name__ == "__main__":
    main() 