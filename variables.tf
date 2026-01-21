variable "subscription_id" {
  description = "Azure Subscription ID (optional; used only for outputs / clarity)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name. Example: dev, test, prod"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region. For your case: usgovarizona"
  type        = string
  default     = "usgovarizona"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "rg-itsm-multiagent-dev"
}

# ----------------------------
# Azure AI (already created in portal)
# ----------------------------
variable "project_endpoint" {
  description = "Azure AI Project endpoint URL (from AI Foundry / Project)."
  type        = string
  sensitive   = true
}

variable "azure_ai_projects_api_key" {
  description = "Azure AI Projects API Key"
  type        = string
  sensitive   = true
}

variable "model_deployment_name" {
  description = "Model deployment name in Azure AI (e.g., gpt-4o)"
  type        = string
  default     = "gpt-4o"
}

variable "itsm_knowledge_agent_id" {
  description = "ITSM Knowledge Agent ID (asst_...)"
  type        = string
  sensitive   = true
}

# ----------------------------
# Teams bot app registration (Azure AD)
# ----------------------------
variable "microsoft_app_id" {
  description = "Microsoft App (client) ID for the Teams bot"
  type        = string
  sensitive   = true
}

variable "microsoft_app_password" {
  description = "Client secret for the Teams bot app registration"
  type        = string
  sensitive   = true
}

# ----------------------------
# Container images (ACR)
# You can keep :latest for dev, pin tags for prod.
# ----------------------------
variable "teams_bot_image_name" {
  description = "Repository name for Teams bot image in ACR"
  type        = string
  default     = "teams-bot"
}

variable "ivanti_api_image_name" {
  description = "Repository name for Ivanti API image in ACR"
  type        = string
  default     = "ivanti-api"
}

variable "nice_api_image_name" {
  description = "Repository name for NICE API image in ACR"
  type        = string
  default     = "nice-api"
}

variable "image_tag" {
  description = "Image tag for all services"
  type        = string
  default     = "latest"
}

# ----------------------------
# ACI sizing
# ----------------------------
variable "teams_bot_cpu" {
  type    = number
  default = 1
}

variable "teams_bot_memory" {
  type    = number
  default = 2
}

variable "api_cpu" {
  type    = number
  default = 1
}

variable "api_memory" {
  type    = number
  default = 1.5
}

# ----------------------------
# Networking exposure
# ----------------------------
variable "expose_public_fqdn" {
  description = "If true, ACI gets a public FQDN and public ports are exposed."
  type        = bool
  default     = true
}

# ----------------------------
# Tags
# ----------------------------
variable "tags" {
  type        = map(string)
  default     = { "project" = "itsm-multiagent" }
}