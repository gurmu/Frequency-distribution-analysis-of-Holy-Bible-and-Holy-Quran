from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import requests
import json
from enum import Enum

# Configuration
BASE_URL = "https://tss.keypoint.us.com"
API_KEY = "8D24C2DC57F64064986130CAFAC73D2E"
PROFILE_REC_ID = "52ECCFD50F8B41F5B0535D0F98B0729D"  # Static internal ITSM person ID

app = FastAPI(
    title="Ivanti Incident Management API",
    description="FastAPI service for creating Ivanti incidents",
    version="1.0.0"
)

# Enums for validation
class StatusEnum(str, Enum):
    logged = "Logged"
    active = "Active"
    waiting = "Waiting"
    resolved = "Resolved"
    closed = "Closed"

class ImpactEnum(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"

class CategoryEnum(str, Enum):
    hardware = "Hardware"
    software = "Software"
    network = "Network"
    other = "Other"

class ServiceEnum(str, Enum):
    software = "Software"
    hardware = "Hardware"
    network = "Network"
    support = "Support"

# Request Model
class IncidentRequest(BaseModel):
    subject: str = Field(..., description="Brief subject of the incident", min_length=1, max_length=255)
    symptom: str = Field(..., description="Detailed description of the incident", min_length=1)
    status: StatusEnum = Field(default=StatusEnum.logged, description="Incident status")
    impact: ImpactEnum = Field(..., description="Impact level of the incident")
    category: CategoryEnum = Field(..., description="Incident category")
    service: ServiceEnum = Field(..., description="Service type")
    owner_team: str = Field(..., description="Team responsible for handling the incident", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject": "Application Login Issue",
                "symptom": "Users unable to login to the portal since 9 AM",
                "status": "Logged",
                "impact": "High",
                "category": "Software",
                "service": "Software",
                "owner_team": "IT Support"
            }
        }

# Response Model
class IncidentResponse(BaseModel):
    success: bool
    message: str
    incident_id: Optional[str] = None
    data: Optional[dict] = None

# Ivanti Client
class IvantiClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        
        self.headers = {
            "Authorization": f"rest_api_key={self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                data=json.dumps(data) if data else None,
                timeout=self.timeout
            )
            
            if 200 <= response.status_code < 300:
                try:
                    return {"success": True, "data": response.json(), "status_code": response.status_code}
                except json.JSONDecodeError:
                    return {"success": True, "message": "Success but no JSON returned", "raw": response.text}
            
            return {
                "success": False,
                "status_code": response.status_code,
                "details": response.text
            }
        except Exception as e:
            return {"success": False, "exception": str(e)}
    
    def create_incident(self, incident_data: dict):
        return self._request("POST", "HEAT/api/odata/businessobject/incidents", incident_data)

# Initialize client
ivanti_client = IvantiClient(base_url=BASE_URL, api_key=API_KEY)

# API Endpoints
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Ivanti Incident Management API",
        "version": "1.0.0"
    }

@app.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, tags=["Incidents"])
async def create_incident(incident: IncidentRequest):
    """
    Create a new incident in Ivanti ITSM
    
    - **subject**: Brief subject line for the incident
    - **symptom**: Detailed description of the issue
    - **status**: Current status (default: Logged)
    - **impact**: Impact level (Low, Medium, High, Critical)
    - **category**: Incident category
    - **service**: Service type
    - **owner_team**: Team that will handle the incident
    """
    
    # Build payload with static ProfileLink_RecID
    incident_payload = {
        "ProfileLink_RecID": PROFILE_REC_ID,  # Static internal ITSM person ID
        "Subject": incident.subject,
        "Symptom": incident.symptom,
        "Status": incident.status.value,
        "Impact": incident.impact.value,
        "Category": incident.category.value,
        "Service": incident.service.value,
        "OwnerTeam": incident.owner_team
    }
    
    # Call Ivanti API
    result = ivanti_client.create_incident(incident_payload)
    
    # Handle response
    if result.get("success"):
        incident_id = None
        if result.get("data") and isinstance(result["data"], dict):
            # Try to extract incident ID from response
            incident_id = result["data"].get("RecId") or result["data"].get("IncidentNumber")
        
        return IncidentResponse(
            success=True,
            message="Incident created successfully",
            incident_id=incident_id,
            data=result.get("data")
        )
    else:
        # Error handling
        error_detail = result.get("details", result.get("exception", "Unknown error"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create incident: {error_detail}"
        )

@app.get("/incidents/schema", tags=["Incidents"])
async def get_incident_schema():
    """Get the schema for creating incidents with all valid enum values"""
    return {
        "required_fields": ["subject", "symptom", "impact", "category", "service", "owner_team"],
        "optional_fields": ["status"],
        "valid_values": {
            "status": [s.value for s in StatusEnum],
            "impact": [i.value for i in ImpactEnum],
            "category": [c.value for c in CategoryEnum],
            "service": [s.value for s in ServiceEnum]
        },
        "static_fields": {
            "ProfileLink_RecID": "Set internally - ITSM person accepting the ticket"
        }
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "incident_id": None,
            "data": None
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)