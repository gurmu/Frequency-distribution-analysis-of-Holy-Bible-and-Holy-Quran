variable "location" {
  description = "Azure region (Gov). Example: usgovvirginia / usgovarizona / usgoviowa"
  type        = string
  default     = "usgovvirginia"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "rg-itsm-multiagent-dev"
}

variable "environment" {
  description = "Environment tag (dev/uat/prod)"
  type        = string
  default     = "dev"
}

variable "name_prefix" {
  description = "Short prefix used for resource names (letters/numbers only recommended)"
  type        = string
  default     = "itsm"
}

# ACR name must be globally unique and 5-50 lowercase letters/numbers.
variable "acr_name" {
  description = "ACR name (lowercase, 5-50 chars). Example: acritmdev12345"
  type        = string
}

# Container image tags (in ACR)
variable "teams_bot_image" {
  description = "Image name:tag for teams-bot in ACR (repo:tag). Example: teams-bot:1.0.0"
  type        = string
  default     = "teams-bot:latest"
}

variable "ivanti_api_image" {
  description = "Image name:tag for ivanti-api in ACR (repo:tag). Example: ivanti-api:1.0.0"
  type        = string
  default     = "ivanti-api:latest"
}

variable "nice_api_image" {
  description = "Image name:tag for nice-api in ACR (repo:tag). Example: nice-api:1.0.0"
  type        = string
  default     = "nice-api:latest"
}

# External endpoints (your corporate endpoints)
variable "ivanti_external_base_url" {
  description = "Ivanti external base URL (corporate). Example: https://ivanti.company.mil"
  type        = string
  default     = ""
}

variable "nice_external_base_url" {
  description = "NICE external base URL (corporate). Example: https://api-cxone.niceincontact.com"
  type        = string
  default     = ""
}

# Azure AI / Agents (these are created manually in Azure AI Studio, then pasted here)
variable "project_endpoint" {
  description = "Azure AI project endpoint URL"
  type        = string
  default     = ""
}

variable "azure_ai_projects_api_key" {
  description = "Azure AI Projects API Key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "model_deployment_name" {
  description = "Model deployment name (e.g., gpt-4o)"
  type        = string
  default     = "gpt-4o"
}

variable "itsm_knowledge_agent_id" {
  description = "Agent ID for ITSM knowledge agent"
  type        = string
  default     = ""
}

variable "investigation_agent_id" {
  description = "Agent ID for investigation agent"
  type        = string
  default     = ""
}

# Teams bot app credentials (AAD app registration done manually)
variable "microsoft_app_id" {
  description = "Microsoft App (Client) ID for Teams bot"
  type        = string
  default     = ""
}

variable "microsoft_app_password" {
  description = "Microsoft App Password/Secret for Teams bot"
  type        = string
  sensitive   = true
  default     = ""
}

# Sizing (adjust if needed)
variable "teams_cpu" { type = number, default = 1 }
variable "teams_mem" { type = number, default = 2 }

variable "api_cpu"   { type = number, default = 1 }
variable "api_mem"   { type = number, default = 1.5 }

# DNS labels must be unique within the region; we append a random suffix.
variable "dns_label_prefix" {
  description = "DNS label prefix for ACI public FQDNs"
  type        = string
  default     = "itsm"
}