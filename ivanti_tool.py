"""
Ivanti Function Tool
Wraps the Ivanti FastAPI service as an Azure AI Agent function tool
"""

import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def create_ivanti_tool_definition() -> Dict[str, Any]:
    """
    Create the function tool definition for Ivanti incident creation
    This is what the agent sees as an available tool
    """
    return {
        "type": "function",
        "function": {
            "name": "create_ivanti_incident",
            "description": """Creates an incident ticket in the Ivanti ITSM system.
            
            Use this tool to create a formal incident record after analyzing the ticket with knowledge bases.
            
            Required fields:
            - email: Employee email address (used to lookup employee in Ivanti)
            - incident_type: Select from predefined incident types (FDR, FWS, Laptop, Outlook, PIPS, Portal, etc.)
            - symptom: Detailed description of the issue
            - urgency: Urgency level (Low/Medium/High)
            - impact: Business impact level (Low/Medium/High/Critical)
            - category: Issue category (Zoom/Windows/Outlook/Adobe Acrobat)
            - service: Related service (Software/Hardware/Network/Support)
            
            Optional fields:
            - subject: Custom subject line (auto-generated from incident_type if not provided)
            
            Returns incident details from Ivanti.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Employee email address (required for employee lookup)"
                    },
                    "incident_type": {
                        "type": "string",
                        "enum": [
                            "FDR Issues",
                            "FWS Issues",
                            "Laptop Issues",
                            "Outlook Issues",
                            "PIPS Issues",
                            "Portal – Access Missing",
                            "Portal – Logon Issue",
                            "Portal – Other Issue",
                            "RSA Soft Token Setup for New Phone",
                            "Windows 11 Upgrade – Question or Issue",
                            "Cisco VPN Issues",
                            "Account – Passwords Not Synchronized",
                            "Account – Smart Card Blocked (PIV / CAC)"
                        ],
                        "description": "Type of incident (subject auto-generated from this)"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Brief problem description (combined with incident_type in final subject)"
                    },
                    "symptom": {
                        "type": "string",
                        "description": "Detailed symptom description"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High"],
                        "description": "Urgency level",
                        "default": "Medium"
                    },
                    "impact": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High", "Critical"],
                        "description": "Business impact level"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["Zoom", "Windows", "Outlook", "Adobe Acrobat"],
                        "description": "Issue category"
                    },
                    "service": {
                        "type": "string",
                        "enum": ["Software", "Hardware", "Network", "Support"],
                        "description": "Related service"
                    }
                },
                "required": ["email", "incident_type", "symptom", "impact", "category", "service"]
            }
        }
    }


class IvantiTool:
    """
    Function tool implementation for Ivanti API
    Handles actual HTTP calls to the FastAPI service
    """
    
    def __init__(self, api_url: str, timeout: int = 30):
        """
        Initialize Ivanti tool
        
        Args:
            api_url: Base URL of Ivanti API (e.g., http://localhost:8000)
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        
        logger.info(f"Ivanti tool initialized: {self.api_url}")
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Ivanti incident creation
        
        Args:
            arguments: Function arguments from the agent
            
        Returns:
            Response from Ivanti API
        """
        logger.info(f"Creating Ivanti incident: {arguments.get('subject')}")
        
        try:
            # Prepare request payload matching FastAPI schema
            payload = {
                "email": arguments["email"],
                "incident_type": arguments["incident_type"],
                "symptom": arguments["symptom"],
                "urgency": arguments.get("urgency", "Medium"),
                "impact": arguments["impact"],
                "category": arguments["category"],
                "service": arguments["service"]
            }
            
            # Add subject if provided (otherwise API will auto-generate)
            if "subject" in arguments and arguments["subject"]:
                payload["subject"] = arguments["subject"]
            
            # Call Ivanti API
            url = f"{self.api_url}/incidents"
            logger.debug(f"POST {url}")
            logger.debug(f"Payload: {payload}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"✓ Incident created successfully")
            
            # Extract incident details from response
            incident_data = result.get("incident_data", {})
            
            return {
                "success": True,
                "message": result.get("message"),
                "incident_data": incident_data,
                "full_response": result
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(f"✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status_code": e.response.status_code
            }
            
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            import asyncio
            asyncio.run(self.close())
        except:
            pass


# Standalone test function
async def test_ivanti_tool():
    """Test the Ivanti tool directly"""
    tool = IvantiTool("http://localhost:8000")
    
    test_args = {
        "email": "ashenafi.t.gurmu@rdg.peraton.com",
        "incident_type": "Outlook Issues",
        "symptom": "Cannot send emails from Outlook client",
        "urgency": "Medium",
        "impact": "Medium",
        "category": "Outlook",
        "service": "Software"
    }
    
    result = await tool.execute(test_args)
    print("Result:", result)
    
    await tool.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ivanti_tool())