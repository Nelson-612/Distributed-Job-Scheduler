from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class JobRequest(BaseModel):
    name:            str
    handler:         str
    payload:         dict         = {}
    schedule:        Optional[str] = None
    priority:        int          = 5
    max_retries:     int          = 3
    timeout_seconds: int          = 300

class JobResponse(BaseModel):
    job_id:      str
    name:        str
    status:      str
    priority:    int
    schedule:    Optional[str]
    retry_count: int
    result:      Optional[Any]
    created_at:  Optional[datetime]

    model_config = {"from_attributes": True}