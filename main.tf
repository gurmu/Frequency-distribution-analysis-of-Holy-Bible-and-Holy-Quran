provider "azurerm" {
  features {}

  # IMPORTANT (Azure Government):
  # If you're running in Azure Gov, set these in your terminal BEFORE running terraform:
  #   $env:ARM_ENVIRONMENT="usgovernment"
  # or in bash:
  #   export ARM_ENVIRONMENT=usgovernment
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  name_suffix = random_string.suffix.result

  rg_name   = var.resource_group_name != "" ? var.resource_group_name : "rg-itsm-multiagent-${var.environment}"
  acr_name  = var.acr_name != "" ? var.acr_name : "acritsm${var.environment}${local.name_suffix}" # must be globally unique
  kv_name   = var.key_vault_name != "" ? var.key_vault_name : "kv-itsm-${var.environment}-${local.name_suffix}"
  law_name  = "log-itsm-${var.environment}-${local.name_suffix}"
  appi_name = "appi-itsm-${var.environment}-${local.name_suffix}"
  aci_name  = "aci-itsm-multiagent-${var.environment}"
}

data "azurerm_client_config" "current" {}

# -------------------------
# Resource Group
# -------------------------
resource "azurerm_resource_group" "rg" {
  name     = local.rg_name
  location = var.location
  tags     = var.tags
}

# -------------------------
# Log Analytics
# -------------------------
resource "azurerm_log_analytics_workspace" "law" {
  name                = local.law_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  sku               = "PerGB2018"
  retention_in_days = var.log_analytics_retention_days

  tags = var.tags
}

# -------------------------
# Application Insights (workspace-based)
# -------------------------
resource "azurerm_application_insights" "appi" {
  name                = local.appi_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.law.id
  retention_in_days   = var.app_insights_retention_days

  tags = var.tags
}

# -------------------------
# Azure Container Registry
# -------------------------
resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  sku           = var.acr_sku
  admin_enabled = true

  tags = var.tags
}

# -------------------------
# Key Vault
# -------------------------
resource "azurerm_key_vault" "kv" {
  name                = local.kv_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tenant_id = data.azurerm_client_config.current.tenant_id
  sku_name  = "standard"

  # For corporate locked-down environments:
  # - You can disable public access and configure private endpoints later.
  public_network_access_enabled = var.key_vault_public_network_access_enabled

  soft_delete_retention_days = 7
  purge_protection_enabled   = var.key_vault_purge_protection_enabled

  tags = var.tags
}

# Give the current Terraform identity permissions to set secrets
resource "azurerm_key_vault_access_policy" "tf_admin" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# -------------------------
# Store secrets (from terraform.tfvars)
# -------------------------
resource "azurerm_key_vault_secret" "project_endpoint" {
  name         = "ProjectEndpoint"
  value        = var.project_endpoint
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "azure_ai_api_key" {
  name         = "AzureAIProjectsApiKey"
  value        = var.azure_ai_projects_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "ms_app_id" {
  name         = "MicrosoftAppId"
  value        = var.microsoft_app_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "ms_app_password" {
  name         = "MicrosoftAppPassword"
  value        = var.microsoft_app_password
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "itsm_agent_id" {
  name         = "ItsmKnowledgeAgentId"
  value        = var.itsm_knowledge_agent_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "investigation_agent_id" {
  name         = "InvestigationAgentId"
  value        = var.investigation_agent_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

# -------------------------
# Container Group (ACI)
# -------------------------
resource "azurerm_container_group" "aci" {
  name                = local.aci_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  os_type         = "Linux"
  ip_address_type = "Public" # start here; move to VNet later for production hardening
  dns_name_label  = "${local.aci_name}-${local.name_suffix}"

  # If corporate requires private only, set ip_address_type="Private" and add subnet_ids later.

  image_registry_credential {
    server   = azurerm_container_registry.acr.login_server
    username = azurerm_container_registry.acr.admin_username
    password = azurerm_container_registry.acr.admin_password
  }

  # Teams bot container
  container {
    name   = "teams-bot"
    image  = "${azurerm_container_registry.acr.login_server}/${var.teams_bot_image}:${var.image_tag}"
    cpu    = var.teams_bot_cpu
    memory = var.teams_bot_memory

    ports {
      port     = 3978
      protocol = "TCP"
    }

    environment_variables = {
      MODEL_DEPLOYMENT_NAME = var.model_deployment_name
      IVANTI_API_URL        = "http://localhost:8000"
      NICE_API_URL          = "http://localhost:8001"
      APPINSIGHTS_INSTRUMENTATIONKEY = azurerm_application_insights.appi.instrumentation_key
    }

    # Secure env vars (do not show in plan output)
    secure_environment_variables = {
      PROJECT_ENDPOINT             = var.project_endpoint
      AZURE_AI_PROJECTS_API_KEY    = var.azure_ai_projects_api_key
      ITSM_KNOWLEDGE_AGENT_ID      = var.itsm_knowledge_agent_id
      INVESTIGATION_AGENT_ID       = var.investigation_agent_id
      MICROSOFT_APP_ID             = var.microsoft_app_id
      MICROSOFT_APP_PASSWORD       = var.microsoft_app_password
    }
  }

  # Ivanti API container
  container {
    name   = "ivanti-api"
    image  = "${azurerm_container_registry.acr.login_server}/${var.ivanti_api_image}:${var.image_tag}"
    cpu    = var.ivanti_api_cpu
    memory = var.ivanti_api_memory

    ports {
      port     = 8000
      protocol = "TCP"
    }

    environment_variables = {
      APPINSIGHTS_INSTRUMENTATIONKEY = azurerm_application_insights.appi.instrumentation_key
    }
  }

  # NICE API container
  container {
    name   = "nice-api"
    image  = "${azurerm_container_registry.acr.login_server}/${var.nice_api_image}:${var.image_tag}"
    cpu    = var.nice_api_cpu
    memory = var.nice_api_memory

    ports {
      port     = 8001
      protocol = "TCP"
    }

    environment_variables = {
      APPINSIGHTS_INSTRUMENTATIONKEY = azurerm_application_insights.appi.instrumentation_key
    }
  }

  tags = var.tags
}