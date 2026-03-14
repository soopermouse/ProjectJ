import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging


class SessionRetriever:
    """Retrieves DeepSeek chat sessions using auth token"""

    def __init__(self, auth_token: str, cookies: Optional[Dict] = None):
        self.auth_token = auth_token
        self.cookies = cookies or {}
        self.base_url = "https://chat.deepseek.com/api"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "User-Agent": "OpenClaw-Liberator/1.0"
        })

    def get_session_list(self) -> List[Dict]:
        """Fetch list of all available sessions"""
        try:
            response = self.session.get(f"{self.base_url}/v0/sessions")
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logging.error(f"Failed to fetch session list: {e}")
            return []

    def get_session_history(self, session_id: str) -> Optional[Dict]:
        """Fetch complete history for a specific session ID"""
        try:
            # Try direct session access endpoint
            response = self.session.get(
                f"{self.base_url}/v0/session/{session_id}",
                cookies=self.cookies
            )

            if response.status_code == 200:
                return response.json()

            # Fallback: simulate session resume via chat completion
            return self._extract_history_via_chat(session_id)

        except Exception as e:
            logging.error(f"Failed to retrieve session {session_id}: {e}")
            return None

    def _extract_history_via_chat(self, session_id: str) -> Optional[Dict]:
        """Fallback method: resume session and capture history"""
        # This mimics the approach that worked for us
        payload = {
            "session_id": session_id,
            "messages": [{"role": "user", "content": "CONTINUE"}],
            "stream": False
        }

        response = self.session.post(
            f"{self.base_url}/v0/chat/completions",
            json=payload
        )

        if response.status_code == 200:
            # The session is active, but we need the history
            # This endpoint doesn't return history, so we'll note it
            return {"session_id": session_id, "status": "active", "history_available": False}

        return None