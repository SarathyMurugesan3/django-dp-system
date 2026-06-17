"""
Audit Log Writer
Handles writing system events, privacy budget changes, and Guardian AI triggers
"""
import os
import json
import logging
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class AuditLogWriter:
    @staticmethod
    def log_event(event_type: str, details: dict, user_id: str = "system") -> bool:
        """
        Write a structured audit log for compliance (GDPR/DPDP)
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "details": details
            }
            
            logger.info(json.dumps(log_entry))
            
            # Log to file
            try:
                log_dir = os.path.join(settings.BASE_DIR, 'logs')
            except Exception:
                log_dir = 'logs'
                
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"audit_log_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                
            return True
        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")
            return False
