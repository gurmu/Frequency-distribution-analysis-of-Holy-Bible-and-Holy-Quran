"""
NICE inContact Callback Queue API
Production FastAPI service for NICE inContact integration
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Literal
import requests
import os
from dotenv import load_dotenv
from authentication import get_access_token, invalidate_token

load_dotenv()

app = FastAPI(
    title="NICE inContact Callback Queue API",
    description="API for managing callback queues in NICE inContact",
    version="1.0.0"
)

API_URL = os.getenv("BASE_URL", "https://api-na2.niceincontact.com")


# ===== REQUEST MODELS =====
class CallbackQueueRequest(BaseModel):
    """Model for creating callback queue"""
    skillId: str = Field(..., description="Skill ID for routing")
    mediaType: Literal["chat", "voice", "email", "workitem"] = Field(
        default="chat",
        description="Type of media channel"
    )
    workItemQueueType: Optional[str] = Field(
        None,
        description="Work item queue type (if mediaType is workitem)"
    )
    isActive: bool = Field(default=True, description="Whether queue is active")
    phoneNumber: str = Field(..., description="Customer phone number")
    emailFromEditable: bool = Field(
        default=True,
        description="Whether email from address is editable"
    )
    emailFrom: EmailStr = Field(
        ...,
        description="Email address for callback",
        example="ashenafi.t.gurmu@rdg.peraton.com"
    )
    emailBccAddress: EmailStr = Field(
        ...,
        description="BCC email address",
        example="ashenafi.t.gurmu@rdg.peraton.com"
    )
    
    # Optional fields
    firstName: Optional[str] = Field(None, description="Customer first name")
    lastName: Optional[str] = Field(None, description="Customer last name")
    priority: Optional[int] = Field(1, ge=1, le=10, description="Priority level (1-10)")
    targetAgentId: Optional[str] = Field(None, description="Specific agent ID to route to")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator('phoneNumber')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Remove non-numeric characters
        cleaned = ''.join(filter(str.isdigit, str(v)))
        if len(cleaned) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned

    class Config:
        json_schema_extra = {
            "example": {
                "skillId": "4354630",
                "mediaType": "chat",
                "workItemQueueType": None,
                "isActive": True,
                "phoneNumber": "2407559064",
                "emailFromEditable": True,
                "emailFrom": "ashenafi.t.gurmu@rdg.peraton.com",
                "emailBccAddress": "ashenafi.t.gurmu@rdg.peraton.com",
                "firstName": "John",
                "lastName": "Doe",
                "priority": 5,
                "notes": "Customer requesting callback"
            }
        }


class CallbackQueueResponse(BaseModel):
    """Response model"""
    success: bool
    message: str
    contactId: Optional[str] = None
    data: Optional[dict] = None


# ===== HELPER FUNCTIONS =====
def make_api_request(endpoint: str, method: str = "POST", payload: dict = None):
    """
    Make authenticated request to NICE inContact API
    Automatically handles token refresh on 401
    """
    token = get_access_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to obtain access token"
        )

    url = f"{API_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "identity"
    }

    # Make initial request
    if method.upper() == "POST":
        response = requests.post(url, json=payload, headers=headers, verify=False)
    elif method.upper() == "GET":
        response = requests.get(url, headers=headers, verify=False)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    # Handle 401 - token expired
    if response.status_code == 401:
        print("⚠️ Token expired, refreshing...")
        invalidate_token()
        token = get_access_token(force_refresh=True)
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh access token"
            )
        
        headers["Authorization"] = f"Bearer {token}"
        
        # Retry request
        if method.upper() == "POST":
            response = requests.post(url, json=payload, headers=headers, verify=False)
        else:
            response = requests.get(url, headers=headers, verify=False)

    return response


# ===== API ENDPOINTS =====
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "NICE inContact Callback Queue API",
        "version": "1.0.0",
        "api_url": API_URL
    }


@app.post(
    "/callback-queue",
    response_model=CallbackQueueResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Callback Queue"]
)
async def create_callback_queue(request: CallbackQueueRequest):
    """
    Create a new callback queue entry in NICE inContact
    
    - **skillId**: Required skill ID for routing
    - **mediaType**: Channel type (chat, voice, email, workitem)
    - **phoneNumber**: Customer phone number
    - **emailFrom**: Customer email address
    - **emailBccAddress**: BCC email for notifications
    """
    
    # Build payload for NICE inContact API
    payload = {
        "skillId": request.skillId,
        "mediaType": request.mediaType,
        "isActive": request.isActive,
        "pointOfContact": {
            "phoneNumber": request.phoneNumber,
            "email": request.emailFrom
        },
        "emailFromEditable": request.emailFromEditable,
        "emailBccAddress": request.emailBccAddress
    }
    
    # Add optional fields
    if request.workItemQueueType:
        payload["workItemQueueType"] = request.workItemQueueType
    
    if request.firstName or request.lastName:
        payload["customer"] = {}
        if request.firstName:
            payload["customer"]["firstName"] = request.firstName
        if request.lastName:
            payload["customer"]["lastName"] = request.lastName
    
    if request.priority:
        payload["priority"] = request.priority
    
    if request.targetAgentId:
        payload["targetAgentId"] = request.targetAgentId
    
    if request.notes:
        payload["notes"] = request.notes

    try:
        # Call NICE inContact API - queuecallback endpoint
        endpoint = "incontactAPI/services/v33.0/queuecallback"
        
        response = make_api_request(endpoint, method="POST", payload=payload)
        
        if response.status_code in [200, 201, 202]:
            response_data = response.json()
            return CallbackQueueResponse(
                success=True,
                message="Callback queue created successfully",
                contactId=response_data.get("contactId"),
                data=response_data
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "message": "Failed to create callback queue",
                    "error": response.text,
                    "status_code": response.status_code
                }
            )
    
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API request failed: {str(e)}"
        )


@app.get("/skills", tags=["Skills"])
async def get_skills():
    """Get all available skills from NICE inContact"""
    try:
        endpoint = "incontactAPI/services/v33.0/skills"
        response = make_api_request(endpoint, method="GET")
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch skills: {response.text}"
            )
    
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API request failed: {str(e)}"
        )


@app.get("/callback-queue/{contact_id}", tags=["Callback Queue"])
async def get_callback_status(contact_id: str):
    """
    Get status of a specific callback queue entry
    
    - **contact_id**: The contact ID returned when callback was created
    """
    try:
        endpoint = f"incontactAPI/services/v33.0/contacts/{contact_id}"
        response = make_api_request(endpoint, method="GET")
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch callback status: {response.text}"
            )
    
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API request failed: {str(e)}"
        )


# ===== RUN THE APP =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
