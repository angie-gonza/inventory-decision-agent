"""UI view modules for Streamlit interface."""

from .view_eoq import render_eoq_view
from .view_discount import render_quantity_discount_view
from .view_safety_stock import render_safety_stock_view
from .view_periodic import render_periodic_review_view
from .view_newsvendor import render_newsvendor_view
from .view_batch_upload import render_batch_upload_view

__all__ = [
    "render_eoq_view",
    "render_quantity_discount_view",
    "render_safety_stock_view",
    "render_periodic_review_view",
    "render_newsvendor_view",
    "render_batch_upload_view",
]
