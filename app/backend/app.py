#!/usr/bin/env python3
"""
Task Management Backend API
A simple Flask application for managing tasks.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
import redis
import requests
from datetime import datetime

app = Flask(__name__)

# Configuration from environment variables (ConfigMap)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
LOGGER_SERVICE_URL = os.getenv('LOGGER_SERVICE_URL', 'http://logger-service:8080')
APP_NAME = os.getenv('APP_NAME', 'task-backend')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(APP_NAME)

# Initialize Redis connection
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


def send_log(log_level, message):
    """Send log to logger service"""
    try:
        requests.post(
            f"{LOGGER_SERVICE_URL}/log",
            json={
                "level": log_level,
                "message": message,
                "service": APP_NAME,
                "timestamp": datetime.utcnow().isoformat()
            },
            timeout=2
        )
    except Exception as e:
        logger.debug(f"Could not send log to logger service: {e}")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "redis": "connected" if redis_client and redis_client.ping() else "disconnected"
    }
    return jsonify(status), 200 if status["redis"] == "connected" else 503


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint"""
    if redis_client and redis_client.ping():
        return jsonify({"status": "ready"}), 200
    return jsonify({"status": "not ready"}), 503


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    try:
        if not redis_client:
            return jsonify({"error": "Database not available"}), 503
        
        task_keys = [k for k in redis_client.keys("task:*") if k != "task:counter"]
        tasks = []
        for key in task_keys:
            task_data = redis_client.get(key)
            if task_data:
                tasks.append(json.loads(task_data))
        
        send_log("INFO", f"Retrieved {len(tasks)} tasks")
        return jsonify({"tasks": tasks}), 200
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        send_log("ERROR", f"Error getting tasks: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        if not redis_client:
            return jsonify({"error": "Database not available"}), 503
        
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({"error": "Title is required"}), 400
        
        task_id = redis_client.incr("task:counter")
        task = {
            "id": task_id,
            "title": data.get("title"),
            "description": data.get("description", ""),
            "completed": False,
            "created_at": datetime.utcnow().isoformat()
        }
        
        redis_client.set(f"task:{task_id}", json.dumps(task))
        send_log("INFO", f"Created task {task_id}: {task['title']}")
        return jsonify(task), 201
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        send_log("ERROR", f"Error creating task: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    try:
        if not redis_client:
            return jsonify({"error": "Database not available"}), 503
        
        task_data = redis_client.get(f"task:{task_id}")
        if not task_data:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify(json.loads(task_data)), 200
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    try:
        if not redis_client:
            return jsonify({"error": "Database not available"}), 503
        
        task_data = redis_client.get(f"task:{task_id}")
        if not task_data:
            return jsonify({"error": "Task not found"}), 404
        
        task = json.loads(task_data)
        data = request.get_json()
        
        if 'title' in data:
            task['title'] = data['title']
        if 'description' in data:
            task['description'] = data['description']
        if 'completed' in data:
            task['completed'] = data['completed']
        
        redis_client.set(f"task:{task_id}", json.dumps(task))
        send_log("INFO", f"Updated task {task_id}")
        return jsonify(task), 200
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        send_log("ERROR", f"Error updating task: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        if not redis_client:
            return jsonify({"error": "Database not available"}), 503
        
        if not redis_client.exists(f"task:{task_id}"):
            return jsonify({"error": "Task not found"}), 404
        
        redis_client.delete(f"task:{task_id}")
        send_log("INFO", f"Deleted task {task_id}")
        return jsonify({"message": "Task deleted"}), 200
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        send_log("ERROR", f"Error deleting task: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
