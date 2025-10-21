# Gmail ML Client - REST API Documentation

## Overview
The Gmail ML Client provides a REST API for programmatic access to email management and machine learning functionality. This API allows integration with other applications and services.

## API Server Setup

### Starting the API Server
```bash
# Start the FastAPI server
python api.py

# Server will start on http://localhost:8000
# API documentation available at http://localhost:8000/docs
```

### Configuration
Edit `api.py` to configure server settings:
```python
# Server configuration
HOST = "localhost"
PORT = 8000
DEBUG = True
```

## Authentication

### API Key Authentication
The API uses simple API key authentication for security:

```bash
# Include API key in headers
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/emails
```

### Setting API Key
Configure your API key in environment variables:
```bash
export GMAIL_ML_API_KEY="your-secure-api-key"
```

## Base URL
```
http://localhost:8000/api
```

## Endpoints Reference

### Health Check

#### `GET /health`
Check API server health and status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-10-21T12:00:00Z",
    "version": "1.0.0",
    "database": "connected",
    "gmail_auth": "valid"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### Email Management

#### `GET /api/emails`
Retrieve emails from the local database.

**Query Parameters:**
- `limit` (int): Maximum number of emails to return (default: 50, max: 1000)
- `offset` (int): Number of emails to skip (default: 0)
- `reviewed` (bool): Filter by review status
- `label` (string): Filter by predicted or assigned label

**Response:**
```json
{
    "emails": [
        {
            "id": "msg_12345",
            "snippet": "Meeting reminder for tomorrow at 2pm",
            "text": "team meeting tomorrow 2pm conference room",
            "label_guess": "Work",
            "spam_score": 0.15,
            "target_label": "Work",
            "reviewed": true,
            "gold_label": "Work",
            "created_at": "2025-10-21T10:30:00Z",
            "updated_at": "2025-10-21T10:35:00Z"
        }
    ],
    "total": 145,
    "limit": 50,
    "offset": 0
}
```
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                         ┌───────▼───────┐
                         │  FastAPI      │
                         │  REST API     │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │   Service     │
                         │   Layer       │
                         └───────┬───────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
    ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
    │  Gmail    │     │ Database  │     │   ML      │
    │   API     │     │ (SQLite)  │     │  Model    │
    └───────────┘     └───────────┘     └───────────┘
```

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
# Run the API server
python api.py

# Or with custom settings
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health & Status

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-21T10:30:00",
  "version": "1.0.0"
}
```

#### `GET /api/status`
Detailed application status including training data statistics.

**Response:**
```json
{
  "status": "running",
  "timestamp": "2024-10-21T10:30:00",
  "training_data": {
    "total_samples": 150,
    "label_counts": {
      "SPAM": 45,
      "Work": 30,
      "Personal": 25,
      "Receipts": 20,
      "Finance": 15,
      "Newsletters": 15
    },
    "unique_labels": 6
  },
  "version": "1.0.0"
}
```

### Initialization

#### `POST /api/init`
Initialize the Gmail ML Client (database and Gmail authentication).

**Response:**
```json
{
  "success": true,
  "message": "Gmail ML Client initialized successfully"
}
```

### Labels

#### `GET /api/labels`
Get all Gmail labels.

**Response:**
```json
[
  {
    "id": "Label_1",
    "name": "Work",
    "type": "user"
  },
  {
    "id": "INBOX",
    "name": "INBOX",
    "type": "system"
  }
]
```

#### `POST /api/labels/ensure`
Create default target labels if missing.

**Response:**
```json
{
  "Work": "Label_1",
  "Personal": "Label_2",
  "Receipts": "Label_3",
  "Finance": "Label_4",
  "Newsletters": "Label_5",
  "Social": "Label_6",
  "Updates": "Label_7"
}
```

### Email Synchronization

#### `POST /api/sync`
Sync emails from Gmail to local database.

**Request Body:**
```json
{
  "query": "is:unread",
  "limit": 100
}
```

**Response:**
```json
{
  "total_messages": 100,
  "processed_messages": 98,
  "failed_messages": 2,
  "errors": [
    "Failed to process message msg_123: Network error"
  ],
  "sync_time": "2024-10-21T10:30:00"
}
```

### Predictions

#### `GET /api/predictions?limit=50`
Get predictions for unreviewed messages.

**Parameters:**
- `limit` (query): Maximum predictions to return (1-200)

**Response:**
```json
{
  "actions": [
    {
      "id": "msg_123",
      "snippet": "Your order has been shipped...",
      "spam_score": 0.15,
      "confidence": 0.94,
      "predicted_label": "Receipts",
      "target_label": "Receipts",
      "action": "route"
    },
    {
      "id": "msg_456",
      "snippet": "Get rich quick scheme...",
      "spam_score": 0.89,
      "confidence": 0.96,
      "predicted_label": "SPAM",
      "target_label": null,
      "action": "trash"
    }
  ],
  "total_count": 25,
  "prediction_time": "2024-10-21T10:30:00"
}
```

### Review

#### `POST /api/review`
Mark a message as reviewed with the correct label.

**Request Body:**
```json
{
  "message_id": "msg_123",
  "label": "Work"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message msg_123 reviewed with label Work"
}
```

### Training

#### `GET /api/training/stats`
Get statistics about available training data.

**Response:**
```json
{
  "total_samples": 150,
  "label_counts": {
    "SPAM": 45,
    "Work": 30,
    "Personal": 25,
    "Receipts": 20,
    "Finance": 15,
    "Newsletters": 15
  },
  "unique_labels": 6
}
```

#### `POST /api/train`
Train the neural classifier from reviewed feedback.

**Request Body:**
```json
{
  "epochs": 6
}
```

**Response:**
```json
{
  "success": true,
  "report": "              precision    recall  f1-score   support\n\n        SPAM       0.95      0.93      0.94        15\n        Work       0.88      0.91      0.89        11\n    Personal       0.92      0.86      0.89         7\n     Finance       0.85      0.83      0.84         6\n\n    accuracy                           0.90        39\n   macro avg       0.90      0.88      0.89        39\nweighted avg       0.90      0.90      0.90        39",
  "classes": ["SPAM", "Work", "Personal", "Finance"],
  "error": null
}
```

### Actions

#### `POST /api/apply`
Apply predicted actions to Gmail.

**Request Body:**
```json
{
  "dry_run": true,
  "limit": 100
}
```

**Response:**
```json
{
  "total_actions": 50,
  "applied_actions": 0,
  "dry_run": true,
  "errors": [],
  "apply_time": "2024-10-21T10:30:00"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200**: Success
- **400**: Bad Request (validation errors)
- **500**: Internal Server Error

Error responses follow this format:
```json
{
  "detail": "Detailed error message"
}
```

## CORS Configuration

The API is configured to allow CORS requests from:
- `http://localhost:3000` (React development server)
- `http://localhost:3001` (Alternative React port)

## Rate Limiting

The API inherits Gmail API rate limits:
- **250 quota units per user per second**
- **1 billion quota units per day**

Each API call consumes different amounts based on Gmail operations performed.

## Security Considerations

1. **OAuth2 Authentication**: Gmail access uses OAuth2 with local token storage
2. **Local Processing**: All email content stays on your machine
3. **No External APIs**: Only connects to Gmail API
4. **Minimal Scopes**: Only requests necessary Gmail permissions

## Performance Guidelines

### Typical Response Times
- **Health/Status**: < 10ms
- **Labels**: < 100ms
- **Predictions**: 100-500ms (depends on model size)
- **Sync**: 1-5 seconds per 100 emails
- **Training**: 30-60 seconds for 1000 samples

### Recommended Usage
- **Sync**: Run periodically (every 15-30 minutes)
- **Predictions**: On-demand or after sync
- **Training**: After accumulating 50+ reviews
- **Apply**: Use dry-run first, then apply in batches

## Development Tips

### Local Testing
```bash
# Start the API server
python api.py

# Test with curl
curl http://localhost:8000/health

# Check interactive docs
open http://localhost:8000/docs
```

### React Integration
See the React example in `react-example/` directory for complete integration examples.

### CLI Migration
The original CLI still works and now uses the same service layer:
```bash
# CLI commands work as before
python cli_fixed.py init
python cli_fixed.py sync
python cli_fixed.py predict
```

## Next Steps

1. **Install new dependencies**: `pip install -r requirements.txt`
2. **Start the API server**: `python api.py`
3. **Test with interactive docs**: Visit http://localhost:8000/docs
4. **Integrate with React**: Use the provided examples
5. **Monitor logs**: Check `logs/gmail_ml_client.log` for detailed operation logs