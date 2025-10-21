# Gmail ML Client - Architecture Documentation

## Overview
The Gmail ML Client is a production-ready Python application that uses machine learning to automatically classify, sort, and manage Gmail messages. It features a robust neural network classifier with TF-IDF features, comprehensive error handling, and a human-in-the-loop workflow for continuous improvement.

## Architecture Components

### 1. CLI Layer (`cli.py`)
- **Purpose**: Main user interface using Typer framework
- **Enhanced Features**:
  - Improved parameter handling with proper Typer syntax
  - Comprehensive error handling and user feedback
  - Progress bars and rich console output
  - Graceful error exits with proper logging

### 2. Configuration (`cfg.py`)
- **Purpose**: Centralized configuration with validation
- **Enhanced Features**:
  - Runtime configuration validation
  - Threshold and rule validation
  - Conflict detection between user and system labels
  - Clear error messages for invalid configurations

### 3. Gmail API Client (`gmail_client.py`)
- **Purpose**: Secure Gmail API interaction
- **Enhanced Features**:
  - Comprehensive error handling for API failures
  - Detailed logging of all operations
  - Graceful handling of rate limits and network issues
  - Clear error messages for credential problems

### 4. Data Store (`data_store.py`)
- **Purpose**: SQLite database with SQLAlchemy ORM
- **Enhanced Features**:
  - Database transaction safety with rollback on errors
  - Connection pooling and session management
  - Detailed logging of all database operations
  - Graceful handling of database corruption/locks

### 5. Machine Learning Model (`model.py`)
- **Purpose**: Neural text classifier with TF-IDF features
- **Enhanced Features**:
  - Input validation for training data
  - Train/validation splits for better evaluation
  - Early stopping to prevent overfitting
  - Robust handling of edge cases (empty data, single class)
  - Model artifact validation before loading

### 6. Text Preprocessing (`preprocessor.py`)
- **Purpose**: Email content extraction and normalization
- **Features**:
  - Multi-part email handling (HTML + plain text)
  - Subject line extraction
  - URL normalization
  - Character set handling with error tolerance

### 7. Decision Engine (`sorter.py`)
- **Purpose**: Combines ML predictions with rule-based logic
- **Features**:
  - Hybrid rule + model approach
  - Confidence-based decision making
  - Action proposal (trash, route, review)

### 8. Training Module (`trainer.py`)
- **Purpose**: Orchestrates model training from feedback
- **Features**:
  - Fetches labeled data from user reviews
  - Handles training failures gracefully

### 9. Logging System (`logger.py`)
- **Purpose**: Comprehensive logging and debugging
- **Features**:
  - Console and file logging
  - Configurable log levels
  - Structured log format with timestamps
  - Automatic log directory creation

### 10. Setup Script (`setup.py`)
- **Purpose**: Automated setup and configuration guidance
- **Features**:
  - Dependency checking and installation
  - Credential setup guidance
  - Basic functionality testing
  - User-friendly error messages

## Data Flow

```
1. Setup (setup.py)
   ↓
2. Initialize (cli.py init)
   ↓
3. Sync emails (cli.py sync)
   ↓ gmail_client.py → preprocessor.py → data_store.py
4. Review/Label (cli.py review)
   ↓ sorter.py → model.py (predict) → user feedback → data_store.py
5. Train (cli.py train)
   ↓ trainer.py → data_store.py → model.py
6. Apply (cli.py apply)
   ↓ sorter.py → gmail_client.py (modify labels/trash)
```

## Enhanced Features

### Error Handling Strategy
- **Gmail API**: Retry logic, rate limit handling, clear credential error messages
- **Database**: Transaction safety, connection pooling, corruption recovery
- **ML Model**: Input validation, graceful degradation, safe defaults
- **File I/O**: Path validation, permission checking, disk space monitoring

### Logging Strategy
- **Levels**: DEBUG for development, INFO for operations, ERROR for failures
- **Destinations**: Console (user feedback) + file (debugging)
- **Format**: Timestamp, component, level, message
- **Rotation**: Automatic log file management

### Configuration Validation
- **Thresholds**: Must be valid probabilities (0-1)
- **Labels**: No conflicts between user and system labels
- **Rules**: All referenced labels must exist in target labels
- **Paths**: Database and model directories must be writable

### Model Robustness
- **Training**: Minimum data requirements, class balance checking
- **Validation**: Train/test splits, early stopping, performance metrics
- **Prediction**: Input sanitization, graceful fallbacks, confidence scoring
- **Persistence**: Atomic saves, version compatibility checking

## Security Considerations

### Gmail API Access
- OAuth 2.0 flow with minimal required scopes
- Local credential caching with secure file permissions
- Token refresh handling
- No permanent email deletion (trash only)

### Data Privacy
- Local SQLite database (no cloud storage)
- Configurable data retention
- Email content processing in memory only
- No external network calls except Gmail API

### Model Security
- Input sanitization for email content
- No code execution from email content
- Model files stored locally with integrity checking

## Performance Optimization

### Gmail API
- Batch message fetching
- Efficient pagination
- Rate limit compliance
- Minimal API calls

### Database
- Indexed queries for common operations
- Connection pooling
- Batch inserts/updates
- Query optimization

### Machine Learning
- TF-IDF vectorization (efficient for text)
- Neural network size optimized for speed
- Model caching and reuse
- Batch prediction processing

## Deployment Considerations

### Requirements
- Python 3.8+
- Gmail API credentials
- Write access to working directory
- 100MB+ free space for model artifacts

### Installation
1. Run `python setup.py` for guided setup
2. Follow credential setup instructions
3. Install dependencies via pip
4. Initialize with `python cli.py init`

### Monitoring
- Check log files in `logs/` directory
- Monitor disk space for database growth
- Validate model performance over time
- Review API quota usage

## Extension Points

### Custom Rules
- Modify `RULES_INCLUDE`/`RULES_EXCLUDE` in `cfg.py`
- Add new label categories
- Customize threshold values

### Model Enhancement
- Replace TF-IDF with transformer embeddings
- Add additional features (sender, time, attachments)
- Implement ensemble methods

### API Integration
- Add other email providers
- Integrate with calendar/tasks
- Connect to external classification services

### UI Enhancement
- Web interface for review process
- Mobile app integration
- Real-time dashboard

## Troubleshooting

### Common Issues
1. **Credential Errors**: Run setup script, check Google Cloud Console
2. **Database Locks**: Check file permissions, restart application
3. **Model Loading**: Re-train model, check model artifacts
4. **API Limits**: Reduce sync frequency, implement backoff

### Debug Mode
- Set logging level to DEBUG in `logger.py`
- Check detailed logs in `logs/gmail_ml_client.log`
- Use `--dry-run` for testing without changes

This enhanced architecture provides a robust, scalable, and maintainable foundation for intelligent Gmail management with machine learning.