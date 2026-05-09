"""
REST API Server Module for Remote System Enhancement

This module provides HTTP REST API endpoints for web-based agent management.
Implements Flask-based API with authentication, command routing, and history retrieval.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.8, 16.3
"""

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from functools import wraps
from typing import Dict, Any, Optional, Callable
import json
import base64
import threading
import time
import os
from datetime import datetime


class RESTAPIServer:
    """
    REST API Server for Remote System Management
    
    Provides HTTP endpoints for web interface to interact with
    the enhanced server and manage agents.
    """
    
    def __init__(self, core_server, port: int = 8080, 
                 web_username: str = "admin", web_password: str = None):
        """
        Initialize REST API server
        
        Args:
            core_server: EnhancedServer instance for command routing
            port: Port number for HTTP server
            web_username: Username for web authentication
            web_password: Password for web authentication
        
        Requirements: 11.8, 16.3
        """
        self.core_server = core_server
        self.port = port
        self.web_username = web_username
        
        # Generate a secure random password if none provided
        if web_password is None:
            import secrets
            web_password = secrets.token_urlsafe(16)
            print(f"[WARNING] No web_password provided. Generated: {web_password}")
            print("[WARNING] Set a persistent password in config for production use.")
        self.web_password = web_password
        
        # Create Flask app
        self.app = Flask(__name__, static_folder='static', static_url_path='')
        CORS(self.app)  # Enable CORS for web UI
        
        # Server state
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup all API routes"""
        
        @self.app.route('/')
        def index():
            """Serve the main web UI page"""
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            return send_from_directory(static_dir, 'index.html')
        
        @self.app.route('/<path:path>')
        def serve_static(path):
            """Serve static files"""
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            if os.path.exists(os.path.join(static_dir, path)):
                return send_from_directory(static_dir, path)
            return send_from_directory(static_dir, 'index.html')
        
        @self.app.route('/api/agents', methods=['GET'])
        @self._require_auth
        def get_agents():
            """
            GET /api/agents - Return list of active agents
            
            Requirements: 11.1, 11.2
            """
            try:
                agents = self.core_server.get_active_agents()
                return jsonify({
                    'success': True,
                    'agents': agents,
                    'count': len(agents)
                }), 200
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/agents/<agent_id>/command', methods=['POST'])
        @self._require_auth
        def send_command(agent_id: str):
            """
            POST /api/agents/<agent_id>/command - Send command to agent
            
            Request body: {"command": {...}}
            
            Requirements: 11.3, 11.4
            """
            try:
                # Validate request
                if not request.is_json:
                    return jsonify({
                        'success': False,
                        'error': 'Request must be JSON'
                    }), 400
                
                data = request.get_json()
                command = data.get('command')
                
                if not command:
                    return jsonify({
                        'success': False,
                        'error': 'Missing command field'
                    }), 400
                
                # Check if agent exists
                agent = self.core_server.db_manager.get_agent_by_id(agent_id)
                if not agent:
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} not found'
                    }), 404
                
                if agent['status'] != 'online':
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} is {agent["status"]}'
                    }), 400
                
                # Queue command
                result = self.core_server.broadcast_command(command, [agent_id])
                
                if result.get(agent_id) == 'queued':
                    return jsonify({
                        'success': True,
                        'message': 'Command queued successfully',
                        'agent_id': agent_id
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to queue command'
                    }), 500
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/agents/<agent_id>/history', methods=['GET'])
        @self._require_auth
        def get_history(agent_id: str):
            """
            GET /api/agents/<agent_id>/history - Retrieve command history
            
            Query params: limit (optional, default 100)
            
            Requirements: 11.4, 11.6
            """
            try:
                # Get limit from query params
                limit = request.args.get('limit', default=100, type=int)
                
                # Validate limit
                if limit < 1 or limit > 1000:
                    return jsonify({
                        'success': False,
                        'error': 'Limit must be between 1 and 1000'
                    }), 400
                
                # Check if agent exists
                agent = self.core_server.db_manager.get_agent_by_id(agent_id)
                if not agent:
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} not found'
                    }), 404
                
                # Get history
                history = self.core_server.db_manager.get_agent_history(agent_id, limit)
                
                return jsonify({
                    'success': True,
                    'agent_id': agent_id,
                    'history': history,
                    'count': len(history)
                }), 200
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/agents/<agent_id>/screenshot', methods=['GET'])
        @self._require_auth
        def get_screenshot(agent_id: str):
            """
            GET /api/agents/<agent_id>/screenshot - Capture and return screenshot
            
            Query params: quality (optional, default 85), format (optional, default PNG)
            
            Requirements: 11.5
            """
            try:
                # Get parameters
                quality = request.args.get('quality', default=85, type=int)
                img_format = request.args.get('format', default='PNG', type=str).upper()
                
                # Validate parameters
                if quality < 1 or quality > 100:
                    return jsonify({
                        'success': False,
                        'error': 'Quality must be between 1 and 100'
                    }), 400
                
                if img_format not in ['PNG', 'JPEG', 'BMP']:
                    return jsonify({
                        'success': False,
                        'error': 'Format must be PNG, JPEG, or BMP'
                    }), 400
                
                # Check if agent exists and is online
                agent = self.core_server.db_manager.get_agent_by_id(agent_id)
                if not agent:
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} not found'
                    }), 404
                
                if agent['status'] != 'online':
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} is {agent["status"]}'
                    }), 400
                
                # Queue screenshot command
                screenshot_command = {
                    'plugin': 'screenshot',
                    'action': 'capture',
                    'args': {
                        'quality': quality,
                        'format': img_format
                    }
                }
                
                result = self.core_server.broadcast_command(screenshot_command, [agent_id])
                
                if result.get(agent_id) == 'queued':
                    return jsonify({
                        'success': True,
                        'message': 'Screenshot command queued',
                        'agent_id': agent_id,
                        'note': 'Screenshot will be available in command history'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to queue screenshot command'
                    }), 500
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/agents/broadcast', methods=['POST'])
        @self._require_auth
        def broadcast_command():
            """
            POST /api/agents/broadcast - Send command to multiple agents
            
            Request body: {"command": {...}, "agent_ids": [...]} or {"command": {...}}
            If agent_ids is omitted, broadcasts to all agents
            
            Requirements: 11.7
            """
            try:
                # Validate request
                if not request.is_json:
                    return jsonify({
                        'success': False,
                        'error': 'Request must be JSON'
                    }), 400
                
                data = request.get_json()
                command = data.get('command')
                agent_ids = data.get('agent_ids')  # Optional, None = all agents
                
                if not command:
                    return jsonify({
                        'success': False,
                        'error': 'Missing command field'
                    }), 400
                
                # Validate agent_ids if provided
                if agent_ids is not None:
                    if not isinstance(agent_ids, list):
                        return jsonify({
                            'success': False,
                            'error': 'agent_ids must be a list'
                        }), 400
                    
                    if len(agent_ids) == 0:
                        return jsonify({
                            'success': False,
                            'error': 'agent_ids list cannot be empty'
                        }), 400
                
                # Broadcast command
                results = self.core_server.broadcast_command(command, agent_ids)
                
                # Count successes
                queued_count = sum(1 for status in results.values() if status == 'queued')
                
                return jsonify({
                    'success': True,
                    'message': f'Command broadcast to {queued_count} agents',
                    'results': results,
                    'queued_count': queued_count,
                    'total_count': len(results)
                }), 200
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/agents/<agent_id>/notify', methods=['POST'])
        @self._require_auth
        def send_notification(agent_id: str):
            """
            POST /api/agents/<agent_id>/notify - Send notification to agent
            
            Request body: {
                "message": "text",
                "title": "optional title",
                "duration": 10,
                "icon": "info|warning|error"
            }
            
            Shows popup notification on client screen
            """
            try:
                # Validate request
                if not request.is_json:
                    return jsonify({
                        'success': False,
                        'error': 'Request must be JSON'
                    }), 400
                
                data = request.get_json()
                message = data.get('message')
                title = data.get('title', 'Server Message')
                duration = data.get('duration', 10)
                icon = data.get('icon', 'info')
                
                if not message:
                    return jsonify({
                        'success': False,
                        'error': 'Missing message field'
                    }), 400
                
                # Check if agent exists and is online
                agent = self.core_server.db_manager.get_agent_by_id(agent_id)
                if not agent:
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} not found'
                    }), 404
                
                if agent['status'] != 'online':
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} is {agent["status"]}'
                    }), 400
                
                # Queue notification command
                notification_command = {
                    'plugin': 'notification',
                    'action': 'show',
                    'args': {
                        'message': message,
                        'title': title,
                        'duration': duration,
                        'icon': icon
                    }
                }
                
                result = self.core_server.broadcast_command(notification_command, [agent_id])
                
                if result.get(agent_id) == 'queued':
                    return jsonify({
                        'success': True,
                        'message': 'Notification queued successfully',
                        'agent_id': agent_id,
                        'notification': {
                            'title': title,
                            'message': message,
                            'duration': duration
                        }
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to queue notification'
                    }), 500
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/agents/<agent_id>/uninstall', methods=['POST'])
        @self._require_auth
        def uninstall_agent(agent_id: str):
            """
            POST /api/agents/<agent_id>/uninstall - Uninstall agent with password verification
            
            Request body: {"password": "string"}
            
            Returns:
                200: Command queued successfully
                400: Agent offline or invalid request
                404: Agent not found
                500: Internal error
            
            Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
            """
            try:
                # Validate request is JSON format
                if not request.is_json:
                    return jsonify({
                        'success': False,
                        'error': 'Request must be JSON'
                    }), 400
                
                # Extract password from request body
                data = request.get_json()
                password = data.get('password')
                
                # Validate password field exists
                if password is None:
                    return jsonify({
                        'success': False,
                        'error': 'Missing password field'
                    }), 400
                
                # Query agent from database using agent_id
                agent = self.core_server.db_manager.get_agent_by_id(agent_id)
                
                # Return HTTP 404 if agent not found
                if not agent:
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} not found'
                    }), 404
                
                # Check if agent is a legacy agent (not supported for uninstall)
                if agent_id.startswith("legacy_"):
                    return jsonify({
                        'success': False,
                        'error': 'Uninstall feature is not supported for legacy agents. Please upgrade the agent to use this feature.'
                    }), 400
                
                # Return HTTP 400 if agent status is not "online"
                if agent['status'] != 'online':
                    return jsonify({
                        'success': False,
                        'error': f'Agent {agent_id} is {agent["status"]}, must be online to uninstall'
                    }), 400
                
                # Queue uninstall command to server with password
                uninstall_command = {
                    'plugin': 'uninstall',
                    'action': 'execute',
                    'args': {
                        'password': password
                    }
                }
                
                result = self.core_server.broadcast_command(uninstall_command, [agent_id])
                
                # Return HTTP 200 with success message on successful queuing
                if result.get(agent_id) == 'queued':
                    return jsonify({
                        'success': True,
                        'message': 'Uninstall command queued successfully',
                        'agent_id': agent_id
                    }), 200
                else:
                    # Return HTTP 500 if command queuing fails
                    return jsonify({
                        'success': False,
                        'error': 'Failed to queue uninstall command'
                    }), 500
            
            except Exception as e:
                # Requirement 10.5: Don't expose password in error responses
                error_msg = str(e)
                # Sanitize error message to remove any potential password exposure
                if password and password in error_msg:
                    error_msg = error_msg.replace(password, '[REDACTED]')
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint (no auth required)"""
            return jsonify({
                'success': True,
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            }), 200
    
    def _require_auth(self, f: Callable) -> Callable:
        """
        Authentication decorator for API endpoints
        
        Requires HTTP Basic Authentication with username/password
        
        Requirements: 11.8
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth = request.authorization
            
            if not auth:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            if auth.username != self.web_username or auth.password != self.web_password:
                return jsonify({
                    'success': False,
                    'error': 'Invalid credentials'
                }), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def start(self) -> None:
        """
        Start the REST API server
        
        Runs Flask app in a separate thread
        """
        if self.running:
            print("[WARNING] REST API server is already running")
            return
        
        self.running = True
        
        def run_server():
            print(f"[STARTED] REST API server listening on port {self.port}")
            self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def stop(self) -> None:
        """
        Stop the REST API server
        
        Note: Flask's built-in server doesn't have a clean shutdown method,
        so we rely on daemon thread termination
        """
        if not self.running:
            print("[WARNING] REST API server is not running")
            return
        
        self.running = False
        print("[STOPPED] REST API server has stopped")


if __name__ == "__main__":
    # Example usage
    from remote_system.enhanced_server.enhanced_server import EnhancedServer
    
    # Create enhanced server
    server = EnhancedServer(
        host="0.0.0.0",
        port=9999,
        db_path="./remote_system.db",
        use_tls=True
    )
    
    # Create REST API server
    api_server = RESTAPIServer(
        core_server=server,
        port=8080,
        web_username="admin",
        web_password="admin"
    )
    
    # Start both servers
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    api_server.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Shutting down...")
        server.stop()
        api_server.stop()
