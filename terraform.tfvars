environment         = "dev"
location            = "usgovarizona"
resource_group_name = "rg-itsm-multiagent-dev"

# Azure AI (from your AI Project)
project_endpoint          = "https://<your-project-endpoint>/"
azure_ai_projects_api_key = "<your-ai-projects-api-key>"
model_deployment_name     = "gpt-4o"
itsm_knowledge_agent_id   = "asst_xxxxxxxxxxxxxxxxxxxxx"

# Teams bot app registration
microsoft_app_id       = "<app-id-guid>"
microsoft_app_password = "<client-secret>"

# Images
teams_bot_image_name   = "teams-bot"
ivanti_api_image_name  = "ivanti-api"
nice_api_image_name    = "nice-api"
image_tag              = "latest"

# Exposure
expose_public_fqdn = true

tags = {
  project = "itsm-multiagent"
  owner   = "ashenafi"
}