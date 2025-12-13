"""
/api/feedback endpoint: Collect user feedback on AI responses.
Used for thumbs up/down on answers to improve the system over time.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])
limiter = Limiter(key_func=get_remote_address)


class FeedbackRequest(BaseModel):
    message_id: str
    session_id: Optional[str] = None
    score: int  # 1 for thumbs up, -1 for thumbs down
    comment: Optional[str] = None
    reason_code: Optional[str] = None  # 'hallucination', 'missing_info', 'style', 'helpful', etc.
    question: Optional[str] = None  # Store original question for context
    answer: Optional[str] = None  # Store the answer that was rated


@router.post("/feedback")
@limiter.limit("20/minute")
async def submit_feedback(request: Request, feedback: FeedbackRequest):
    """
    Submit user feedback on an AI response.
    
    For now, we'll just log it. Later, we can persist to PostgreSQL.
    """
    try:
        # Log feedback for now (later: save to database)
        logger.info(
            f"Feedback received - Message: {feedback.message_id}, "
            f"Score: {feedback.score}, Reason: {feedback.reason_code}, "
            f"Comment: {feedback.comment[:50] if feedback.comment else 'None'}"
        )
        
        # TODO: Persist to PostgreSQL feedback table
        # Example schema:
        # CREATE TABLE feedback (
        #     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        #     message_id TEXT NOT NULL,
        #     session_id TEXT,
        #     score INT NOT NULL,
        #     comment TEXT,
        #     reason_code TEXT,
        #     question TEXT,
        #     answer TEXT,
        #     created_at TIMESTAMP DEFAULT NOW()
        # );
        
        return {
            "status": "success",
            "message": "Feedback received",
            "feedback_id": feedback.message_id  # In production, return actual DB ID
        }
        
    except Exception as e:
        logger.error(f"Error saving feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save feedback")
