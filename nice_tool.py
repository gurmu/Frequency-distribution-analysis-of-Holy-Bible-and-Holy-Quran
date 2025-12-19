"""
NICE inContact Function Tool
Wraps the NICE inContact Production API as an Azure AI Agent function tool
"""

import httpx
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Import authentication module
try:
    from api.nice_incontact.auth import get_access_token, invalidate_token
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logging.warning("Authentication module not available - NICE API calls will fail")

load_dotenv()
logger = logging.getLogger(__name__)


def create_nice_tool_definition() -> Dict[str, Any]:
    """
    Create the function tool definition for NICE callback queue
    This is what the agent sees as an available tool
    """
    return {
        "type": "function",
        "function": {
            "name": "create_nice_callback",
            "description": """Creates a callback queue entry in NICE inContact for customer follow-up.
            
            Use this tool to schedule a callback when:
            - Incident priority is High or Critical
            - Customer requires immediate attention
            - Issue needs human follow-up
            
            The callback will be routed to the appropriate skill queue based on the incident type.
            
            Required fields:
            - phoneNumber: Customer phone number
            - skill: Skill ID for routing (default: 4354630)
            
            Returns contact ID for tracking the callback.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "phoneNumber": {
                        "type": "string",
                        "description": "Customer phone number (10+ digits)"
                    },
                    "skill": {
                        "type": "integer",
                        "description": "Skill ID for routing (default: 4354630)",
                        "default": 4354630
                    }
                },
                "required": ["phoneNumber"]
            }
        }
    }


class NICETool:
    """
    Function tool implementation for NICE inContact Production API
    """
    
    def __init__(self, api_url: str, timeout: int = 30):
        """
        Initialize NICE tool
        
        Args:
            api_url: Base URL of NICE API service (e.g., http://nice-api:8001)
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        
        # Initialize HTTP client with default headers
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers=default_headers
        )
        
        logger.info(f"NICE tool initialized: {self.api_url}")
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and validate phone number"""
        cleaned = ''.join(filter(str.isdigit, str(phone)))
        if len(cleaned) < 10:
            logger.warning(f"Invalid phone number: {phone}, using default")
            return "9999999999"
        return cleaned
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the NICE callback creation
        
        Args:
            arguments: Function arguments from the agent
                - phoneNumber: Customer phone number (required)
                - skill: Skill ID (default: 4354630)
            
        Returns:
            Response from NICE API
        """
        logger.info(f"Creating NICE callback - Phone: {arguments.get('phoneNumber')}")
        
        try:
            # Clean phone number
            phone = self._clean_phone_number(arguments.get("phoneNumber", ""))
            skill = arguments.get("skill", 4354630)
            
            # Prepare simple payload for NICE API
            payload = {
                "phoneNumber": phone,
                "skill": skill
            }
            
            # Call NICE API service
            url = f"{self.api_url}/callback-queue"
            logger.debug(f"POST {url}")
            logger.debug(f"Payload: {payload}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"✓ Callback created successfully")
            logger.info(f"  Contact ID: {result.get('contactId')}")
            
            return {
                "success": True,
                "contactId": result.get("contactId"),
                "message": result.get("message"),
                "data": result.get("data")
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
async def test_nice_tool():
    """Test the NICE tool directly"""
    tool = NICETool("http://localhost:8001")
    
    test_args = {
        "phoneNumber": "240-755-9064",
        "skill": 4354630
    }
    
    result = await tool.execute(test_args)
    print("Result:", result)
    
    await tool.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_nice_tool())