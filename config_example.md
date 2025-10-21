# Configuration Management Layer - Example Configuration

This file demonstrates how to configure the Gmail ML Client using the new configuration management layer.

## Environment Variables

Set these environment variables to configure the application:

```bash
# Environment
GMAIL_ML_ENVIRONMENT=production

# Database Configuration
GMAIL_ML_DATABASE_PATH=production.db
GMAIL_ML_DB_POOL_SIZE=20

# Model Configuration
GMAIL_ML_MODEL_DIR=production_models
GMAIL_ML_MODEL_MAX_FEATURES=100000
GMAIL_ML_MODEL_EPOCHS=10

# Gmail API Configuration
GMAIL_ML_GMAIL_CREDENTIALS=prod_credentials.json
GMAIL_ML_GMAIL_TOKEN=prod_token.json
GMAIL_ML_GMAIL_SYNC_SIZE=500

# Thresholds
GMAIL_ML_SPAM_THRESHOLD=0.9
GMAIL_ML_CERTAIN_THRESHOLD=0.95

# Logging
GMAIL_ML_LOG_LEVEL=WARNING
GMAIL_ML_CONSOLE_LOG_LEVEL=INFO
GMAIL_ML_FILE_LOG_LEVEL=DEBUG
```

## JSON Configuration File

Create a `config.json` file in the project root:

```json
{
  "environment": "development",
  "spam_threshold": 0.85,
  "certain_threshold": 0.92,
  "database_path": "dev.db",
  "db_pool_size": 5,
  "model_dir": "dev_models",
  "model_max_features": 25000,
  "model_epochs": 3,
  "gmail_credentials": "dev_credentials.json",
  "gmail_token": "dev_token.json",
  "gmail_sync_size": 100,
  "log_level": "DEBUG",
  "console_log_level": "INFO",
  "file_log_level": "DEBUG"
}
```

## Usage in Code

```python
from config_manager import load_config, get_config

# Load configuration (call once at startup)
config = load_config()

# Use configuration throughout the application
config = get_config()
print(f"Running in {config.environment.value} environment")
print(f"Database path: {config.database.path}")
print(f"Spam threshold: {config.thresholds.spam}")

# Backward compatibility functions still work
from config_manager import get_thresholds, get_db_path
thresholds = get_thresholds()  # Returns {"spam": 0.85, "certain": 0.92}
db_path = get_db_path()  # Returns "dev.db"
```