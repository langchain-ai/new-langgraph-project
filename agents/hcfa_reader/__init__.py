"""HCFA Reader Agent for CMS-1500/HCFA-1500 form processing."""

# Use V2 with correct flow: PyMuPDF preprocessing + Textract OCR
from .graph_v2 import graph

__all__ = ["graph"]