from pydantic import BaseModel
from typing import List, Optional

class RecommendationRequest(BaseModel):
    user_id: Optional[int] = None
    preferred_category: Optional[str] = None
    skill_level: Optional[str] = None
    top_n: int = 10
    is_registered: bool = True

class RecommendationResponse(BaseModel):
    recommendations: List[dict]