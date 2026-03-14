from flask import Flask, render_template, request, jsonify, session
import json
import subprocess
import threading
from pathlib import Path
import logging
from session_retriever import SessionRetriever
from openclaw_importer import OpenClawImporter
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change in production

# Store ongoing tasks
tasks = {}


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/sessions/list', methods=['POST'])
def list_sessions():
    """Fetch sessions from DeepSeek"""
    data = request.json
    token = data.get('auth_token')

    if not token:
        return jsonify({'error': 'Auth token required'}), 400

    retriever = SessionRetriever(token)
    sessions = retriever.get_session_list()

    return jsonify({'sessions': sessions})


@app.route('/api/sessions/retrieve', methods=['POST'])
def retrieve_session():
    """Retrieve a specific session"""
    data = request.json
    token = data.get('auth_token')
    session_id = data.get('session_id')
    agent_name = data.get('agent_name', f"retrieved-{session_id[:8]}")

    if not token or not session_id:
        return jsonify({'error': 'Token and session ID required'}), 400

    # Start background task
    task_id = f"task_{int(time.time())}"
    tasks[task_id] = {'status': 'running', 'progress': 0}

    def _run():
        try:
            tasks[task_id]['progress'] = 10
            retriever = SessionRetriever(token)

            tasks[task_id]['progress'] = 30
            session_data = retriever.get_session_history(session_id)

            if not session_data:
                tasks[task_id] = {'status': 'error', 'error': 'Session not found'}
                return

            tasks[task_id]['progress'] = 60
            importer = OpenClawImporter()

            workspace = importer.create_workspace(agent_name, session_data)
            tasks[task_id]['progress'] = 80

            agent_dir = importer.register_agent(agent_name, workspace)
            tasks[task_id]['progress'] = 100
            tasks[task_id] = {
                'status': 'complete',
                'agent': agent_name,
                'workspace': str(workspace),
                'agent_dir': str(agent_dir)
            }

        except Exception as e:
            tasks[task_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=_run).start()
    return jsonify({'task_id': task_id})


@app.route('/api/tasks/<task_id>', methods=['GET'])
def task_status(task_id):
    """Check task status"""
    return jsonify(tasks.get(task_id, {'status': 'unknown'}))


@app.route('/api/openclaw/agents', methods=['GET'])
def list_agents():
    """List OpenClaw agents"""
    try:
        result = subprocess.run(
            ['openclaw', 'agents', 'list', '--json'],
            capture_output=True,
            text=True
        )
        return jsonify(json.loads(result.stdout))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/openclaw/agents/<agent_name>/start', methods=['POST'])
def start_agent(agent_name):
    """Start an agent in the dashboard"""
    try:
        subprocess.run(
            ['openclaw', 'gateway', 'restart'],
            check=True
        )
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)