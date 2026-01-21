variable "environment" {
  type        = string
  description = "Environment label (dev/test/prod)"
  default     = "dev"
}

variable "location" {
  type        = string
  description = "Azure region (for Azure Gov you used USGov Arizona)"
  default     = "usgovarizona"
}

variable "resource_group_name" {
  type        = string
  description = "Optional. If empty, Terraform generates rg name."
  default     = ""
}

variable "acr_name" {
  type        = string
  description = "Optional. Must be globally unique. If empty, Terraform generates."
  default     = ""
}

variable "acr_sku" {
  type        = string
  default     = "Basic"
}

variable "key_vault_name" {
  type        = string
  default     = ""
}

variable "key_vault_public_network_access_enabled" {
  type        = bool
  default     = true
}

variable "key_vault_purge_protection_enabled" {
  type        = bool
  default     = false
}

variable "log_analytics_retention_days" {
  type    = number
  default = 30
}

variable "app_insights_retention_days" {
  type    = number
  default = 30
}

# -------------------------
# Images
# -------------------------
variable "image_tag" {
  type        = string
  description = "Container tag to deploy"
  default     = "latest"
}

variable "teams_bot_image" {
  type        = string
  default     = "teams-bot"
}

variable "ivanti_api_image" {
  type        = string
  default     = "ivanti-api"
}

variable "nice_api_image" {
  type        = string
  default     = "nice-api"
}

# -------------------------
# Sizing
# -------------------------
variable "teams_bot_cpu"    { type = number, default = 1 }
variable "teams_bot_memory" { type = number, default = 2 }

variable "ivanti_api_cpu"    { type = number, default = 1 }
variable "ivanti_api_memory" { type = number, default = 1.5 }

variable "nice_api_cpu"    { type = number, default = 1 }
variable "nice_api_memory" { type = number, default = 1.5 }

# -------------------------
# AI + Bot runtime configuration (secure)
# -------------------------
variable "project_endpoint" {
  type        = string
  description = "Azure AI Foundry Project Endpoint URL"
  sensitive   = true
}

variable "azure_ai_projects_api_key" {
  type        = string
  description = "Azure AI Foundry API Key"
  sensitive   = true
}

variable "model_deployment_name" {
  type        = string
  description = "Model deployment name (e.g., gpt-4o)"
  default     = "gpt-4o"
}

variable "itsm_knowledge_agent_id" {
  type        = string
  sensitive   = true
}

variable "investigation_agent_id" {
  type        = string
  sensitive   = true
}

variable "microsoft_app_id" {
  type      = string
  sensitive = true
}

variable "microsoft_app_password" {
  type      = string
  sensitive = true
}

# -------------------------
# Tags
# -------------------------
variable "tags" {
  type = map(string)
  default = {
    app = "itsm-multiagent"
  }
}