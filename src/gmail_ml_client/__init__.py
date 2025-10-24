"""
Gmail ML Client - Intelligent Email Management

A production-ready Python application that connects to Gmail and uses machine learning
to automatically classify, sort, and manage emails with intelligent spam filtering
and content-based organization.
"""

__version__ = "1.0.0"
__author__ = "Gmail ML Client Team"
__description__ = "Intelligent Email Management with Machine Learning"

# Core modules - import these directly for convenience
from . import cfg, logger


# Lazy imports for modules that might have initialization dependencies
def __getattr__(name):
    """Lazy import for modules that may have initialization dependencies."""
    lazy_imports = {
        "api": ".api",
        "cli_fixed": ".cli_fixed",
        "gmail_client": ".gmail_client",
        "model": ".model",
        "data_store": ".data_store",
        "preprocessor": ".preprocessor",
        "sorter": ".sorter",
        "trainer": ".trainer",
        "auth_manager": ".auth_manager",
        "interfaces": ".interfaces",
        "services": ".services",
        "enhanced_services": ".enhanced_services",
        "testable_services": ".testable_services",
        "validation_layer": ".validation_layer",
        "cache_layer": ".cache_layer",
        "config_manager": ".config_manager",
        "adapters": ".adapters",
    }

    if name in lazy_imports:
        from importlib import import_module

        module = import_module(lazy_imports[name], __name__)
        globals()[name] = module
        return module

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
