#!/usr/bin/env python3
"""
Centralized Logging Service
Receives logs from other services and stores/displays them.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from collections import deque

app = Flask(__name__)

# Configuration
LOG_STORAGE_SIZE = int(os.getenv('LOG_STORAGE_SIZE', '1000'))
APP_NAME = os.getenv('APP_NAME', 'logger-service')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(APP_NAME)

# In-memory log storage (limited size)
log_storage = deque(maxlen=LOG_STORAGE_SIZE)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint"""
    return jsonify({"status": "ready"}), 200


@app.route('/log', methods=['POST'])
def receive_log():
    """Receive log from other services"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        log_entry = {
            "level": data.get("level", "INFO"),
            "message": data.get("message", ""),
            "service": data.get("service", "unknown"),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat())
        }
        
        log_storage.append(log_entry)
        
        # Also log locally
        log_level = getattr(logging, log_entry["level"].upper(), logging.INFO)
        logger.log(log_level, f"[{log_entry['service']}] {log_entry['message']}")
        
        return jsonify({"status": "logged"}), 200
    except Exception as e:
        logger.error(f"Error receiving log: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/logs', methods=['GET'])
def get_logs():
    """Get recent logs"""
    try:
        limit = int(request.args.get('limit', 100))
        service = request.args.get('service')
        level = request.args.get('level')
        
        logs = list(log_storage)
        
        # Filter by service if provided
        if service:
            logs = [log for log in logs if log.get('service') == service]
        
        # Filter by level if provided
        if level:
            logs = [log for log in logs if log.get('level') == level.upper()]
        
        # Limit results
        logs = logs[-limit:]
        
        return jsonify({"logs": logs, "count": len(logs)}), 200
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
