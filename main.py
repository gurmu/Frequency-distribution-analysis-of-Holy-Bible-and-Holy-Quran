"""
Ivanti Incident Management API
Production service for creating incidents using Ivanti REST API
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum
import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ivanti Incident Management API",
    description="Production API for Ivanti ITSM incident creation with email-based employee lookup",
    version="2.0.0"
)

# ============================
# CONFIGURATION
# ============================

IVANTI_BASE_URL = os.getenv(
    "IVANTI_BASE_URL",
    "https://tss.keypoint.us.com/HEAT/api/odata/businessobject"
)
IVANTI_API_KEY = os.getenv("IVANTI_API_KEY", "")

if not IVANTI_API_KEY:
    logger.warning("⚠️  IVANTI_API_KEY not set - API calls will fail")

HEADERS = {
    "Authorization": f"rest_api_key={IVANTI_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# ============================
# ENUMS
# ============================

class IncidentTypeEnum(str, Enum):
    """Incident type catalog items"""
    fdr_issues = "FDR Issues"
    fws_issues = "FWS Issues"
    laptop_issues = "Laptop Issues"
    outlook_issues = "Outlook Issues"
    pips_issues = "PIPS Issues"
    portal_access_missing = "Portal – Access Missing"
    portal_logon_issue = "Portal – Logon Issue"
    portal_other_issue = "Portal – Other Issue"
    rsa_soft_token_setup = "RSA Soft Token Setup for New Phone"
    windows_11_upgrade = "Windows 11 Upgrade – Question or Issue"
    cisco_vpn_issues = "Cisco VPN Issues"
    account_passwords_not_synced = "Account – Passwords Not Synchronized"
    account_smart_card_blocked = "Account – Smart Card Blocked (PIV / CAC)"


class UrgencyEnum(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class ImpactEnum(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class CategoryEnum(str, Enum):
    zoom = "Zoom"
    windows = "Windows"
    outlook = "Outlook"
    adobe_acrobat = "Adobe Acrobat"


class ServiceEnum(str, Enum):
    software = "Software"
    hardware = "Hardware"
    network = "Network"
    support = "Support"


class SourceEnum(str, Enum):
    chat = "Chat"
    phone = "Phone"
    self_service = "Self Service"
    email = "Email"


# ============================
# REQUEST MODELS
# ============================

class IncidentRequest(BaseModel):
    """Request model for creating an incident"""
    email: EmailStr = Field(..., description="Employee email address")
    incident_type: IncidentTypeEnum = Field(..., description="Type of incident being reported")
    subject: Optional[str] = Field(None, min_length=1, max_length=255, description="Incident subject (auto-generated if not provided)")
    symptom: str = Field(..., min_length=1, description="Detailed symptom description")
    urgency: UrgencyEnum = Field(default=UrgencyEnum.medium, description="Urgency level")
    impact: ImpactEnum = Field(..., description="Business impact level")
    service: ServiceEnum = Field(..., description="Related service")
    category: CategoryEnum = Field(..., description="Issue category")
    source: SourceEnum = Field(default=SourceEnum.chat, description="Incident source (automatically set to Chat)")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "ashenafi.t.gurmu@rdg.peraton.com",
                "incident_type": "Outlook Issues",
                "subject": "Cannot send emails",
                "symptom": "Cannot send emails from Outlook desktop client",
                "urgency": "Medium",
                "impact": "High",
                "service": "Software",
                "category": "Outlook",
                "source": "Chat"
            }
        }


# ============================
# RESPONSE MODELS
# ============================

class EmployeeResponse(BaseModel):
    """Response model for employee lookup"""
    success: bool
    employee_recid: Optional[str] = None
    employee_data: Optional[dict] = None
    message: str


class IncidentResponse(BaseModel):
    """Response model for incident creation"""
    success: bool
    message: str
    incident_data: Optional[dict] = None


# ============================
# HELPER FUNCTIONS
# ============================

def lookup_employee_recid(email: str) -> str:
    """
    Look up employee by email and return RecId
    
    Args:
        email: Employee email address
        
    Returns:
        Employee RecId
        
    Raises:
        HTTPException: If employee not found or API call fails
    """
    logger.info(f"Looking up employee: {email}")
    
    employee_url = f"{IVANTI_BASE_URL}/Employees?$filter=PrimaryEmail eq '{email}'"
    
    try:
        response = requests.get(employee_url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Employee lookup failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to lookup employee: {response.text}"
            )
        
        data = response.json()
        
        # Extract RecId from response
        try:
            employee_recid = data["value"][0]["RecId"]
            logger.info(f"✓ Found employee RecId: {employee_recid}")
            return employee_recid
        except (KeyError, IndexError) as e:
            logger.error(f"Employee not found: {email}")
            raise HTTPException(
                status_code=404,
                detail=f"Employee not found in Ivanti. Please verify email address: {email}"
            )
    
    except requests.RequestException as e:
        logger.error(f"Request error during employee lookup: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )


def create_incident_in_ivanti(profile_recid: str, incident_data: dict) -> dict:
    """
    Create incident in Ivanti using profile RecId
    
    Args:
        profile_recid: Employee RecId
        incident_data: Incident details
        
    Returns:
        Ivanti API response
        
    Raises:
        HTTPException: If incident creation fails
    """
    logger.info(f"Creating incident for RecId: {profile_recid}")
    
    incident_url = f"{IVANTI_BASE_URL}/Incidents"
    
    payload = {
        "ProfileLink_RecID": profile_recid,
        **incident_data
    }
    
    try:
        response = requests.post(
            incident_url,
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        
        if response.status_code not in (200, 201):
            logger.error(f"Incident creation failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create incident: {response.text}"
            )
        
        result = response.json()
        logger.info(f"✓ Incident created successfully")
        return result
    
    except requests.RequestException as e:
        logger.error(f"Request error during incident creation: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )


# ============================
# ROUTES
# ============================

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Ivanti Incident Management API",
        "version": "2.0.0",
        "mode": "Production",
        "ivanti_base_url": IVANTI_BASE_URL,
        "api_key_configured": bool(IVANTI_API_KEY)
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    if not IVANTI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="IVANTI_API_KEY not configured"
        )
    
    return {
        "status": "healthy",
        "ivanti_base_url": IVANTI_BASE_URL,
        "api_key_configured": True
    }


@app.get("/employees", response_model=EmployeeResponse, tags=["Employees"])
async def lookup_employee(email: str):
    """
    Look up employee by email address
    
    Args:
        email: Employee email address (query parameter)
        
    Returns:
        Employee information including RecId
    """
    try:
        employee_recid = lookup_employee_recid(email)
        
        return EmployeeResponse(
            success=True,
            employee_recid=employee_recid,
            message=f"Employee found: {email}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, tags=["Incidents"])
async def create_incident(incident: IncidentRequest):
    """
    Create an incident in Ivanti ITSM
    
    Process:
    1. Look up employee by email to get RecId
    2. Create incident with the employee's RecId
    
    Args:
        incident: Incident details including employee email
        
    Returns:
        Incident creation response from Ivanti
    """
    try:
        # Step 1: Look up employee RecId
        profile_recid = lookup_employee_recid(incident.email)
        
        # Step 2: Generate subject combining user input + incident type
        # Format: "user's subject - Incident Type" (e.g., "my outlook didn't work - Outlook Issues")
        if incident.subject:
            subject = f"{incident.subject} - {incident.incident_type.value}"
        else:
            # If no custom subject, just use incident type
            subject = incident.incident_type.value
        
        # Step 3: Prepare incident data
        incident_data = {
            "Subject": subject,  # Format: "user subject - Incident Type"
            "Symptom": incident.symptom,
            "Urgency": incident.urgency.value,
            "Impact": incident.impact.value,
            "Service": incident.service.value,
            "Category": incident.category.value,
            "Source": incident.source.value  # Chat, Phone, Self Service, etc.
        }
        
        logger.info(f"Incident data: {incident_data}")
        
        # Step 3: Create incident in Ivanti
        result = create_incident_in_ivanti(profile_recid, incident_data)
        
        return IncidentResponse(
            success=True,
            message="Incident created successfully",
            incident_data=result
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ============================
# ERROR HANDLERS
# ============================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "incident_data": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"Internal server error: {str(exc)}",
            "incident_data": None
        }
    )


# ============================
# STARTUP
# ============================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("Starting Ivanti Incident Management API")
    logger.info(f"Base URL: {IVANTI_BASE_URL}")
    logger.info(f"API Key configured: {bool(IVANTI_API_KEY)}")
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
