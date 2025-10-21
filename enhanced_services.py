"""
Enhanced services with integrated layers for configuration, authentication, validation, and caching.
This demonstrates how all the separation layers work together in a cohesive architecture.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Import our new layers
from config_manager import get_config, AppConfig
from auth_manager import get_auth_manager, AuthenticationManager
from validation_layer import (
    validate_email, validate_prediction, validate_training_data,
    ValidationResult, create_email_validation_chain
)
from cache_layer import (
    get_default_cache_manager, create_namespace, cached,
    cache_email, get_cached_email, cache_prediction, get_cached_prediction
)

# Import existing modules
import gmail_client
import data_store
import model
import preprocessor
import sorter
from logger import logger


@dataclass
class ServiceResponse:
    """Standardized response from service operations."""
    success: bool
    data: Any = None
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "") -> 'ServiceResponse':
        """Create a successful response."""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(cls, message: str, errors: List[str] = None) -> 'ServiceResponse':
        """Create an error response."""
        return cls(
            success=False, 
            message=message, 
            errors=errors or [message]
        )
    
    def add_validation_result(self, validation: ValidationResult) -> None:
        """Add validation results to the response."""
        if not validation.is_valid:
            self.success = False
            self.errors.extend(validation.errors)
        self.warnings.extend(validation.warnings)


class EnhancedGmailService:
    """Enhanced Gmail service with integrated layers."""
    
    def __init__(self):
        self.config: AppConfig = get_config()
        self.auth_manager: AuthenticationManager = get_auth_manager()
        self.cache = create_namespace("gmail_service")
        self.validation_chain = create_email_validation_chain()
    
    def initialize(self) -> ServiceResponse:
        """Initialize Gmail service with authentication."""
        try:
            # Authenticate with Gmail
            credentials = self.auth_manager.authenticate()
            
            # Validate required scopes
            required_scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.labels'
            ]
            
            if not self.auth_manager.validate_scopes(required_scopes):
                return ServiceResponse.error_response(
                    "Insufficient permissions. Please re-authenticate with required scopes."
                )
            
            # Initialize data store with config
            data_store.init_db(self.config.database.path)
            
            logger.info("Gmail service initialized successfully")
            return ServiceResponse.success_response(
                message="Gmail service initialized and authenticated"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return ServiceResponse.error_response(f"Initialization failed: {str(e)}")
    
    @cached(ttl_seconds=300, key_func=lambda self, label_id=None: f"labels_{label_id or 'all'}")
    def get_labels(self, label_id: Optional[str] = None) -> ServiceResponse:
        """Get Gmail labels with caching."""
        try:
            service = self.auth_manager.get_service('gmail', 'v1')
            
            if label_id:
                # Get specific label
                result = service.users().labels().get(userId='me', id=label_id).execute()
                return ServiceResponse.success_response(
                    data=result,
                    message=f"Retrieved label: {label_id}"
                )
            else:
                # Get all labels
                result = service.users().labels().list(userId='me').execute()
                labels = result.get('labels', [])
                
                # Filter out system labels based on config
                user_labels = [
                    label for label in labels 
                    if label['name'] not in self.config.labels.system_labels
                ]
                
                return ServiceResponse.success_response(
                    data=user_labels,
                    message=f"Retrieved {len(user_labels)} user labels"
                )
                
        except Exception as e:
            logger.error(f"Failed to get labels: {e}")
            return ServiceResponse.error_response(f"Failed to get labels: {str(e)}")
    
    def sync_emails(self, max_results: Optional[int] = None) -> ServiceResponse:
        """Sync emails with validation and caching."""
        try:
            # Use configured sync page size
            page_size = max_results or self.config.gmail.sync_page_size
            
            # Get service
            service = self.auth_manager.get_service('gmail', 'v1')
            
            # Sync emails using existing gmail_client
            emails = gmail_client.get_recent_emails(service, max_results=page_size)
            
            if not emails:
                return ServiceResponse.success_response(
                    data=[],
                    message="No new emails to sync"
                )
            
            # Validate each email
            validated_emails = []
            validation_errors = []
            
            for email_data in emails:
                validation_result = validate_email(email_data)
                
                if validation_result.is_valid:
                    validated_emails.append(email_data)
                    # Cache the email
                    cache_email(email_data['id'], email_data)
                else:
                    validation_errors.extend(validation_result.errors)
                    logger.warning(f"Email {email_data.get('id', 'unknown')} failed validation")
            
            # Store validated emails
            if validated_emails:
                data_store.store_emails(validated_emails)
            
            response = ServiceResponse.success_response(
                data=validated_emails,
                message=f"Synced {len(validated_emails)} emails"
            )
            
            if validation_errors:
                response.warnings.extend([f"Validation issues: {'; '.join(validation_errors)}"])
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to sync emails: {e}")
            return ServiceResponse.error_response(f"Sync failed: {str(e)}")


class EnhancedPredictionService:
    """Enhanced prediction service with validation and caching."""
    
    def __init__(self):
        self.config: AppConfig = get_config()
        self.cache = create_namespace("predictions")
    
    @cached(ttl_seconds=1800, key_func=lambda self, email_id: f"prediction_{email_id}")
    def predict_labels(self, email_id: str) -> ServiceResponse:
        """Predict labels for an email with caching and validation."""
        try:
            # Check cache first (decorator handles this, but we can add custom logic)
            cached_prediction = get_cached_prediction(email_id)
            if cached_prediction:
                # Validate cached prediction
                validation_result = validate_prediction(
                    cached_prediction, 
                    set(self.config.labels.default_target_labels)
                )
                
                if validation_result.is_valid:
                    return ServiceResponse.success_response(
                        data=cached_prediction,
                        message="Retrieved cached prediction"
                    )
                else:
                    # Invalidate bad cache entry
                    self.cache.delete(f"prediction_{email_id}")
            
            # Get email data
            email_data = get_cached_email(email_id)
            if not email_data:
                email_data = data_store.get_email(email_id)
                if not email_data:
                    return ServiceResponse.error_response(f"Email not found: {email_id}")
            
            # Validate email data
            email_validation = validate_email(email_data)
            if not email_validation.is_valid:
                return ServiceResponse.error_response(
                    "Invalid email data",
                    email_validation.errors
                )
            
            # Get prediction using existing model
            predictions = model.predict_single_email(email_data)
            
            if not predictions:
                return ServiceResponse.error_response("No predictions generated")
            
            # Use configured thresholds
            prediction_data = {
                'email_id': email_id,
                'predicted_label': predictions[0]['label'],
                'confidence': predictions[0]['confidence'],
                'alternatives': predictions[1:] if len(predictions) > 1 else [],
                'threshold_spam': self.config.thresholds.spam,
                'threshold_certain': self.config.thresholds.certain,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Validate prediction
            prediction_validation = validate_prediction(
                prediction_data,
                set(self.config.labels.default_target_labels)
            )
            
            response = ServiceResponse.success_response(
                data=prediction_data,
                message=f"Predicted label: {predictions[0]['label']} (confidence: {predictions[0]['confidence']:.3f})"
            )
            
            response.add_validation_result(prediction_validation)
            
            # Cache the prediction
            cache_prediction(email_id, prediction_data)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to predict labels for {email_id}: {e}")
            return ServiceResponse.error_response(f"Prediction failed: {str(e)}")


class EnhancedTrainingService:
    """Enhanced training service with validation."""
    
    def __init__(self):
        self.config: AppConfig = get_config()
        self.cache = create_namespace("training")
    
    def train_model(self, force_retrain: bool = False) -> ServiceResponse:
        """Train the model with validation."""
        try:
            # Get training data
            training_data = data_store.get_training_data()
            
            if not training_data:
                return ServiceResponse.error_response("No training data available")
            
            # Validate training data
            validation_result = validate_training_data(training_data)
            
            if not validation_result.is_valid:
                return ServiceResponse.error_response(
                    "Training data validation failed",
                    validation_result.errors
                )
            
            # Check if we have enough data per label
            min_samples = 5  # Could be configurable
            label_counts = {}
            for sample in training_data:
                for label in sample.get('labels', []):
                    label_counts[label] = label_counts.get(label, 0) + 1
            
            insufficient_labels = [
                label for label, count in label_counts.items() 
                if count < min_samples
            ]
            
            if insufficient_labels:
                return ServiceResponse.error_response(
                    f"Insufficient training data for labels: {insufficient_labels}. Need at least {min_samples} samples per label."
                )
            
            # Train the model using existing trainer
            import trainer
            success = trainer.train_model(
                artifacts_dir=self.config.model.artifacts_dir,
                epochs=self.config.model.epochs,
                batch_size=self.config.model.batch_size
            )
            
            if success:
                # Clear prediction cache since model changed
                self.cache.cache_manager.clear("predictions")
                
                return ServiceResponse.success_response(
                    message=f"Model trained successfully with {len(training_data)} samples across {len(label_counts)} labels"
                )
            else:
                return ServiceResponse.error_response("Model training failed")
            
        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return ServiceResponse.error_response(f"Training failed: {str(e)}")


class EnhancedActionService:
    """Enhanced action service with validation."""
    
    def __init__(self):
        self.config: AppConfig = get_config()
        self.auth_manager: AuthenticationManager = get_auth_manager()
        self.cache = create_namespace("actions")
    
    def apply_label(self, email_id: str, label_name: str) -> ServiceResponse:
        """Apply label to email with validation."""
        try:
            # Validate label name
            from validation_layer import validate_label
            label_validation = validate_label(label_name)
            
            if not label_validation.is_valid:
                return ServiceResponse.error_response(
                    "Invalid label",
                    label_validation.errors
                )
            
            # Get Gmail service
            service = self.auth_manager.get_service('gmail', 'v1')
            
            # Apply label using existing sorter
            success = sorter.apply_label_to_email(service, email_id, label_name)
            
            if success:
                # Invalidate email cache for this email
                cache_key = f"email_{email_id}"
                self.cache.delete(cache_key)
                
                return ServiceResponse.success_response(
                    message=f"Applied label '{label_name}' to email {email_id}"
                )
            else:
                return ServiceResponse.error_response(f"Failed to apply label to email {email_id}")
            
        except Exception as e:
            logger.error(f"Failed to apply label {label_name} to {email_id}: {e}")
            return ServiceResponse.error_response(f"Label application failed: {str(e)}")


class EnhancedEmailSyncService:
    """Enhanced email sync service combining all layers."""
    
    def __init__(self):
        self.config: AppConfig = get_config()
        self.gmail_service = EnhancedGmailService()
        self.prediction_service = EnhancedPredictionService()
        self.cache = create_namespace("sync")
    
    def full_sync_and_predict(self, max_emails: Optional[int] = None) -> ServiceResponse:
        """Perform full sync with predictions."""
        try:
            # Initialize if needed
            init_response = self.gmail_service.initialize()
            if not init_response.success:
                return init_response
            
            # Sync emails
            sync_response = self.gmail_service.sync_emails(max_emails)
            if not sync_response.success:
                return sync_response
            
            emails = sync_response.data
            if not emails:
                return ServiceResponse.success_response(
                    data={'synced': 0, 'predicted': 0},
                    message="No emails to process"
                )
            
            # Generate predictions for synced emails
            predictions = []
            prediction_errors = []
            
            for email_data in emails:
                email_id = email_data['id']
                pred_response = self.prediction_service.predict_labels(email_id)
                
                if pred_response.success:
                    predictions.append(pred_response.data)
                else:
                    prediction_errors.extend(pred_response.errors)
            
            response_data = {
                'synced': len(emails),
                'predicted': len(predictions),
                'predictions': predictions
            }
            
            response = ServiceResponse.success_response(
                data=response_data,
                message=f"Synced {len(emails)} emails and generated {len(predictions)} predictions"
            )
            
            if prediction_errors:
                response.warnings.extend([f"Prediction errors: {'; '.join(prediction_errors)}"])
            
            return response
            
        except Exception as e:
            logger.error(f"Full sync and predict failed: {e}")
            return ServiceResponse.error_response(f"Full sync failed: {str(e)}")


# Global service instances
gmail_service = EnhancedGmailService()
prediction_service = EnhancedPredictionService()
training_service = EnhancedTrainingService()
action_service = EnhancedActionService()
sync_service = EnhancedEmailSyncService()


# Convenience functions for backward compatibility
def initialize_services() -> bool:
    """Initialize all services."""
    try:
        # Load configuration
        from config_manager import load_config
        config = load_config()
        logger.info(f"Loaded configuration for {config.environment.value} environment")
        
        # Initialize Gmail service
        response = gmail_service.initialize()
        return response.success
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False


def get_service_stats() -> Dict[str, Any]:
    """Get statistics from all services."""
    from cache_layer import get_cache_stats
    
    return {
        'cache_stats': get_cache_stats(),
        'authentication': {
            'is_authenticated': gmail_service.auth_manager.is_authenticated(),
            'token_info': gmail_service.auth_manager.get_token_info()
        },
        'configuration': {
            'environment': gmail_service.config.environment.value,
            'database_path': gmail_service.config.database.path,
            'model_dir': gmail_service.config.model.artifacts_dir
        }
    }