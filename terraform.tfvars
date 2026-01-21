location            = "usgovvirginia"
resource_group_name = "rg-itsm-multiagent-dev"
environment         = "dev"
name_prefix         = "itsm"

# IMPORTANT: must be globally unique + lowercase
acr_name = "acritsmdev12345"

# Your ACR repo:tag (must exist after you push images)
teams_bot_image  = "teams-bot:latest"
ivanti_api_image = "ivanti-api:latest"
nice_api_image   = "nice-api:latest"

# External systems (corporate endpoints)
ivanti_external_base_url = "https://<your-ivanti-host>"
nice_external_base_url   = "https://<your-nice-host>"

# Azure AI (from Azure AI Studio)
project_endpoint         = "https://<your-project>.cognitiveservices.azure.com/"
azure_ai_projects_api_key = "<paste_api_key>"
model_deployment_name    = "gpt-4o"
itsm_knowledge_agent_id  = "asst_..."
investigation_agent_id   = "asst_..."

# Bot app registration (manual)
microsoft_app_id       = "<client-id-guid>"
microsoft_app_password = "<client-secret>"