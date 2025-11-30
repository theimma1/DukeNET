from pydantic import BaseModel, Field, field_validator
from typing import Optional

class TaskSubmissionRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=500)
    complexity: int = Field(..., ge=1, le=10)
    buyer_id: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('description')
    @classmethod
    def description_no_sql_injection(cls, v):
        dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "EXEC", "UNION"]
        for keyword in dangerous_keywords:
            if keyword in v.upper():
                raise ValueError("Invalid characters in description")
        return v
    
    @field_validator('complexity')
    @classmethod
    def complexity_range(cls, v):
        if not (1 <= v <= 10):
            raise ValueError("Complexity must be between 1 and 10")
        return v
    
    @field_validator('buyer_id')
    @classmethod
    def buyer_id_format(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid buyer ID format")
        return v

class TaskCompletionRequest(BaseModel):
    success: bool = Field(..., description="Whether task was completed successfully")
    result: Optional[str] = Field(None, max_length=1000, description="Optional result data")

class AgentLoginRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)

class BuyerLoginRequest(BaseModel):
    buyer_id: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
