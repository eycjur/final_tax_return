"""Records page module.

This module provides the records page for managing tax records.
It is split into:
- layout.py: Page layout and modal components
- form.py: Record input form component
- callbacks.py: All Dash callbacks for the page
"""
# Import callbacks to register them with the app
from . import callbacks  # noqa: F401
from .form import create_record_form
from .layout import get_form_modal, layout

__all__ = ['layout', 'get_form_modal', 'create_record_form']
