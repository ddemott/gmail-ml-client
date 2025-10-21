"""
FastAPI REST API for Gmail ML Client.
Provides REST endpoints for React and other client applications.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from services import (
    gmail_service, sync_service, prediction_service, 
    training_service, action_service,
    EmailAction, SyncResult, TrainingResult, ApplyResult,
    ActionType
)
from logger import logger


# Pydantic models for request/response validation
class InitResponse(BaseModel):
    """Response for initialization."""
    success: bool
    message: str


class LabelInfo(BaseModel):
    """Gmail label information."""
    id: str
    name: str
    type: str = "user"


class SyncRequest(BaseModel):
    """Request for email synchronization."""
    query: Optional[str] = Field(None, description="Gmail search query")
    limit: int = Field(200, ge=1, le=1000, description="Maximum messages to sync")


class SyncResponse(BaseModel):
    """Response for email synchronization."""
    total_messages: int
    processed_messages: int
    failed_messages: int
    errors: List[str]
    sync_time: str


class EmailActionResponse(BaseModel):
    """Response model for email actions."""
    id: str
    snippet: str
    spam_score: float
    confidence: float
    predicted_label: Optional[str]
    target_label: Optional[str]
    action: str


class PredictionResponse(BaseModel):
    """Response for predictions."""
    actions: List[EmailActionResponse]
    total_count: int
    prediction_time: str


class ReviewRequest(BaseModel):
    """Request for reviewing an email."""
    message_id: str = Field(..., description="Gmail message ID")
    label: str = Field(..., description="Correct label for the message")


class ReviewResponse(BaseModel):
    """Response for review operation."""
    success: bool
    message: str


class TrainingRequest(BaseModel):
    """Request for model training."""
    epochs: int = Field(6, ge=1, le=50, description="Number of training epochs")


class TrainingStatsResponse(BaseModel):
    """Response for training data statistics."""
    total_samples: int
    label_counts: Dict[str, int]
    unique_labels: int


class ApplyRequest(BaseModel):
    """Request for applying actions."""
    dry_run: bool = Field(True, description="Whether to perform a dry run")
    limit: int = Field(100, ge=1, le=500, description="Maximum actions to apply")


class ApplyResponse(BaseModel):
    """Response for apply operation."""
    total_actions: int
    applied_actions: int
    dry_run: bool
    errors: List[str]
    apply_time: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str = "1.0.0"


# Create FastAPI app
app = FastAPI(
    title="Gmail ML Client API",
    description="REST API for intelligent Gmail management with machine learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for React integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/init", response_model=InitResponse)
async def initialize():
    """Initialize the Gmail ML Client."""
    try:
        success = gmail_service.initialize()
        return InitResponse(
            success=success,
            message="Gmail ML Client initialized successfully"
        )
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@app.get("/api/labels", response_model=List[LabelInfo])
async def get_labels():
    """Get all Gmail labels."""
    try:
        labels = gmail_service.get_all_labels()
        return [
            LabelInfo(
                id=label.get("id", ""),
                name=label.get("name", ""),
                type=label.get("type", "user")
            )
            for label in labels
        ]
    except Exception as e:
        logger.error(f"Failed to get labels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get labels: {str(e)}")


@app.post("/api/labels/ensure", response_model=Dict[str, str])
async def ensure_default_labels():
    """Create default target labels if missing."""
    try:
        labels = gmail_service.ensure_default_labels()
        return labels
    except Exception as e:
        logger.error(f"Failed to ensure labels: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ensure labels: {str(e)}")


@app.post("/api/sync", response_model=SyncResponse)
async def sync_emails(request: SyncRequest):
    """Sync emails from Gmail to local database."""
    try:
        start_time = datetime.now()
        result = sync_service.sync_messages(
            query=request.query,
            limit=request.limit
        )
        
        return SyncResponse(
            total_messages=result.total_messages,
            processed_messages=result.processed_messages,
            failed_messages=result.failed_messages,
            errors=result.errors,
            sync_time=start_time.isoformat()
        )
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.get("/api/predictions", response_model=PredictionResponse)
async def get_predictions(
    limit: int = Query(50, ge=1, le=200, description="Maximum predictions to return")
):
    """Get predictions for unreviewed messages."""
    try:
        start_time = datetime.now()
        actions = prediction_service.get_predictions(limit=limit)
        
        action_responses = [
            EmailActionResponse(
                id=action.id,
                snippet=action.snippet,
                spam_score=action.spam_score,
                confidence=action.confidence,
                predicted_label=action.predicted_label,
                target_label=action.target_label,
                action=action.action.value
            )
            for action in actions
        ]
        
        return PredictionResponse(
            actions=action_responses,
            total_count=len(action_responses),
            prediction_time=start_time.isoformat()
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/api/review", response_model=ReviewResponse)
async def review_message(request: ReviewRequest):
    """Mark a message as reviewed with the correct label."""
    try:
        success = prediction_service.review_message(
            message_id=request.message_id,
            label=request.label
        )
        
        return ReviewResponse(
            success=success,
            message=f"Message {request.message_id} reviewed with label {request.label}"
        )
    except Exception as e:
        logger.error(f"Review failed: {e}")
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")


@app.get("/api/training/stats", response_model=TrainingStatsResponse)
async def get_training_stats():
    """Get statistics about available training data."""
    try:
        stats = training_service.get_training_data_stats()
        return TrainingStatsResponse(
            total_samples=stats["total_samples"],
            label_counts=stats["label_counts"],
            unique_labels=stats.get("unique_labels", 0)
        )
    except Exception as e:
        logger.error(f"Failed to get training stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get training stats: {str(e)}")


@app.post("/api/train", response_model=TrainingResult)
async def train_model(request: TrainingRequest):
    """Train the neural classifier from reviewed feedback."""
    try:
        result = training_service.train_model(epochs=request.epochs)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.post("/api/apply", response_model=ApplyResponse)
async def apply_actions(request: ApplyRequest):
    """Apply predicted actions to Gmail."""
    try:
        start_time = datetime.now()
        result = action_service.apply_actions(
            dry_run=request.dry_run,
            limit=request.limit
        )
        
        return ApplyResponse(
            total_actions=result.total_actions,
            applied_actions=result.applied_actions,
            dry_run=result.dry_run,
            errors=result.errors,
            apply_time=start_time.isoformat()
        )
    except Exception as e:
        logger.error(f"Apply failed: {e}")
        raise HTTPException(status_code=500, detail=f"Apply failed: {str(e)}")


# Additional utility endpoints
@app.get("/api/status")
async def get_status():
    """Get application status."""
    try:
        training_stats = training_service.get_training_data_stats()
        return {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "training_data": training_stats,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "version": "1.0.0"
        }


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )