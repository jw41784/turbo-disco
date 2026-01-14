# Marketing automation module
# Repurposes newsletter content into social media posts

from .linkedin import LinkedInGenerator
from .repurpose import ContentRepurposer

__all__ = [
    "LinkedInGenerator",
    "ContentRepurposer",
]
