"""
Memory Manager Module
====================

This module handles conversation memory and session management
for the Web Page Intelligence application.

Author: AI Assistant
Date: 2025
"""

import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from config.settings import AppConfig
from utils.helpers import safe_json_dump, safe_json_load, ensure_directory_exists

logger = logging.getLogger(__name__)

@dataclass
class SessionInfo:
    """Session information data class"""
    session_id: str
    name: str
    created_at: str
    last_activity: str
    message_count: int
    urls_processed: int
    questions_extracted: int
    metadata: Dict[str, Any] = None

class MemoryManager:
    """Manages conversation memory and sessions"""
    
    def __init__(self):
        """Initialize the memory manager"""
        self.config = AppConfig()
        self.sessions_file = os.path.join(self.config.SESSION_DATA_DIR, "sessions.json")
        self.conversations_dir = os.path.join(self.config.SESSION_DATA_DIR, "conversations")
        
        # Ensure directories exist
        ensure_directory_exists(self.config.SESSION_DATA_DIR)
        ensure_directory_exists(self.conversations_dir)
        
        # Load existing sessions
        self.sessions = self._load_sessions()
    
    def _load_sessions(self) -> Dict[str, SessionInfo]:
        """Load sessions from file"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                
                sessions = {}
                for session_id, data in sessions_data.items():
                    sessions[session_id] = SessionInfo(**data)
                
                logger.info(f"Loaded {len(sessions)} sessions from storage")
                return sessions
            else:
                return {}
        
        except Exception as e:
            logger.error(f"Error loading sessions: {str(e)}")
            return {}
    
    def _save_sessions(self) -> bool:
        """Save sessions to file"""
        try:
            sessions_data = {}
            for session_id, session_info in self.sessions.items():
                sessions_data[session_id] = asdict(session_info)
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving sessions: {str(e)}")
            return False
    
    def create_new_session(self, name: str = None) -> str:
        """Create a new session"""
        try:
            session_id = str(uuid.uuid4())[:8]  # Short UUID for readability
            current_time = datetime.now().isoformat()
            
            if not name:
                name = f"Session {len(self.sessions) + 1}"
            
            session_info = SessionInfo(
                session_id=session_id,
                name=name,
                created_at=current_time,
                last_activity=current_time,
                message_count=0,
                urls_processed=0,
                questions_extracted=0,
                metadata={}
            )
            
            self.sessions[session_id] = session_info
            self._save_sessions()
            
            logger.info(f"Created new session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating new session: {str(e)}")
            return str(uuid.uuid4())[:8]  # Return a basic ID as fallback
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        return self.sessions.get(session_id)
    
    def update_session_activity(self, session_id: str, 
                              message_count: int = None,
                              urls_processed: int = None,
                              questions_extracted: int = None) -> bool:
        """Update session activity"""
        try:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.last_activity = datetime.now().isoformat()
                
                if message_count is not None:
                    session.message_count = message_count
                if urls_processed is not None:
                    session.urls_processed = urls_processed
                if questions_extracted is not None:
                    session.questions_extracted = questions_extracted
                
                self._save_sessions()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
            return False
    
    def save_conversation(self, session_id: str, 
                         conversation_history: List[Dict[str, Any]]) -> bool:
        """Save conversation history for a session"""
        try:
            # Limit conversation history size
            limited_history = conversation_history[-self.config.MAX_CHAT_HISTORY:]
            
            conversation_file = os.path.join(self.conversations_dir, f"{session_id}.json")
            
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_id": session_id,
                    "last_updated": datetime.now().isoformat(),
                    "conversation": limited_history
                }, f, indent=2, ensure_ascii=False, default=str)
            
            # Update session info
            self.update_session_activity(session_id, message_count=len(limited_history))
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation for session {session_id}: {str(e)}")
            return False
    
    def load_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Load conversation history for a session"""
        try:
            conversation_file = os.path.join(self.conversations_dir, f"{session_id}.json")
            
            if os.path.exists(conversation_file):
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return data.get("conversation", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading conversation for session {session_id}: {str(e)}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its conversation history"""
        try:
            # Remove from sessions dict
            if session_id in self.sessions:
                del self.sessions[session_id]
                self._save_sessions()
            
            # Delete conversation file
            conversation_file = os.path.join(self.conversations_dir, f"{session_id}.json")
            if os.path.exists(conversation_file):
                os.remove(conversation_file)
            
            logger.info(f"Deleted session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    def get_all_sessions(self) -> List[SessionInfo]:
        """Get all sessions sorted by last activity"""
        sessions_list = list(self.sessions.values())
        sessions_list.sort(key=lambda x: x.last_activity, reverse=True)
        return sessions_list
    
    def cleanup_old_sessions(self, days_old: int = None) -> int:
        """Clean up old sessions"""
        if days_old is None:
            days_old = self.config.SESSION_TIMEOUT_HOURS / 24
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            sessions_to_delete = []
            
            for session_id, session_info in self.sessions.items():
                try:
                    last_activity = datetime.fromisoformat(session_info.last_activity)
                    if last_activity < cutoff_date:
                        sessions_to_delete.append(session_id)
                except ValueError:
                    # If we can't parse the date, consider it old
                    sessions_to_delete.append(session_id)
            
            # Delete old sessions
            deleted_count = 0
            for session_id in sessions_to_delete:
                if self.delete_session(session_id):
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old sessions")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {str(e)}")
            return 0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory and session statistics"""
        try:
            total_sessions = len(self.sessions)
            total_conversations = 0
            total_messages = 0
            
            for session_info in self.sessions.values():
                total_messages += session_info.message_count
            
            # Count conversation files
            if os.path.exists(self.conversations_dir):
                conversation_files = [f for f in os.listdir(self.conversations_dir) 
                                    if f.endswith('.json')]
                total_conversations = len(conversation_files)
            
            return {
                "total_sessions": total_sessions,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
                "storage_directory": self.config.SESSION_DATA_DIR,
                "sessions_file_exists": os.path.exists(self.sessions_file)
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {str(e)}")
            return {"error": str(e)}
    
    def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export complete session data"""
        try:
            session_info = self.get_session_info(session_id)
            if not session_info:
                return None
            
            conversation_history = self.load_conversation(session_id)
            
            return {
                "session_info": asdict(session_info),
                "conversation_history": conversation_history,
                "export_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting session data: {str(e)}")
            return None
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search through conversations for specific content"""
        results = []
        
        try:
            query_lower = query.lower()
            
            for session_id in self.sessions.keys():
                conversation = self.load_conversation(session_id)
                session_info = self.get_session_info(session_id)
                
                for message in conversation:
                    content = message.get("content", "").lower()
                    
                    if query_lower in content:
                        results.append({
                            "session_id": session_id,
                            "session_name": session_info.name if session_info else "Unknown",
                            "message": message,
                            "timestamp": message.get("timestamp", ""),
                            "match_preview": self._create_match_preview(message.get("content", ""), query)
                        })
                
                if len(results) >= limit:
                    break
            
            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching conversations: {str(e)}")
            return []
    
    def _create_match_preview(self, text: str, query: str, context_length: int = 100) -> str:
        """Create a preview of text around the matched query"""
        if not text or not query:
            return ""
        
        try:
            query_lower = query.lower()
            text_lower = text.lower()
            
            match_index = text_lower.find(query_lower)
            if match_index == -1:
                return text[:context_length] + "..." if len(text) > context_length else text
            
            start = max(0, match_index - context_length // 2)
            end = min(len(text), match_index + len(query) + context_length // 2)
            
            preview = text[start:end]
            
            if start > 0:
                preview = "..." + preview
            if end < len(text):
                preview = preview + "..."
            
            return preview
            
        except Exception:
            return text[:context_length] + "..." if len(text) > context_length else text