locals {
  # Unique suffix for global-name resources (ACR, Storage, KV)
  # random_string below ensures uniqueness.
  name_prefix = "itsm${var.environment}"
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  numeric = true
  special = false
}

# ----------------------------
# Resource Group
# ----------------------------
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ----------------------------
# Log Analytics
# ----------------------------
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-${local.name_prefix}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# ----------------------------
# Application Insights
# (Workspace-based)
# ----------------------------
resource "azurerm_application_insights" "appi" {
  name                = "appi-${local.name_prefix}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.law.id
  tags                = var.tags
}

# ----------------------------
# Key Vault (for storing secrets centrally)
# NOTE: Access policy is included for the signed-in user via data.azurerm_client_config.
# ----------------------------
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                = "kv-${local.name_prefix}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled = false
  soft_delete_retention_days = 7

  tags = var.tags
}

resource "azurerm_key_vault_access_policy" "tf_admin" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# Store solution secrets in KV (optional but recommended)
resource "azurerm_key_vault_secret" "project_endpoint" {
  name         = "AzureAIProjectEndpoint"
  value        = var.project_endpoint
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "azure_ai_key" {
  name         = "AzureAIProjectsApiKey"
  value        = var.azure_ai_projects_api_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "itsm_agent_id" {
  name         = "ITSMKnowledgeAgentId"
  value        = var.itsm_knowledge_agent_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "bot_app_id" {
  name         = "MicrosoftAppId"
  value        = var.microsoft_app_id
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

resource "azurerm_key_vault_secret" "bot_app_password" {
  name         = "MicrosoftAppPassword"
  value        = var.microsoft_app_password
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_key_vault_access_policy.tf_admin]
}

# ----------------------------
# Storage Account + KB container (for ITSM knowledge docs you will azcopy)
# ----------------------------
resource "azurerm_storage_account" "kb" {
  name                     = lower(replace("st${local.name_prefix}${random_string.suffix.result}", "-", ""))
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  tags = var.tags
}

resource "azurerm_storage_container" "kb" {
  name                  = "itsm-kb"
  storage_account_name  = azurerm_storage_account.kb.name
  container_access_type = "private"
}

# ----------------------------
# ACR (images for ACI)
# ----------------------------
resource "azurerm_container_registry" "acr" {
  name                = "acr${local.name_prefix}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.tags
}

# ----------------------------
# User-assigned Managed Identity for ACI (recommended)
# ----------------------------
resource "azurerm_user_assigned_identity" "aci" {
  name                = "id-aci-${local.name_prefix}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

# (Optional for later) allow ACI identity to read Key Vault secrets
resource "azurerm_key_vault_access_policy" "aci_kv_reader" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.aci.principal_id

  secret_permissions = ["Get", "List"]
}

# ----------------------------
# ACI Container Group
# - Teams bot: port 3978
# - Ivanti API: port 8000
# - NICE API: port 8001
#
# NOTE: This assumes your images exist in ACR with tags.
#       If images do not exist yet, ACI will fail to pull.
#       Build/push first, or re-apply after pushing.
# ----------------------------
resource "azurerm_container_group" "itsm" {
  name                = "aci-itsm-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  tags                = var.tags

  # public / private
  ip_address_type = var.expose_public_fqdn ? "Public" : "Private"
  dns_name_label  = var.expose_public_fqdn ? "itsm-${var.environment}-${random_string.suffix.result}" : null

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aci.id]
  }

  image_registry_credential {
    server   = azurerm_container_registry.acr.login_server
    username = azurerm_container_registry.acr.admin_username
    password = azurerm_container_registry.acr.admin_password
  }

  # Expose ports at the container group level (public)
  dynamic "exposed_port" {
    for_each = var.expose_public_fqdn ? [3978, 8000, 8001] : []
    content {
      port     = exposed_port.value
      protocol = "TCP"
    }
  }

  # ----------------------------
  # Teams Bot container
  # ----------------------------
  container {
    name   = "teams-bot"
    image  = "${azurerm_container_registry.acr.login_server}/${var.teams_bot_image_name}:${var.image_tag}"
    cpu    = var.teams_bot_cpu
    memory = var.teams_bot_memory

    ports {
      port     = 3978
      protocol = "TCP"
    }

    environment_variables = {
      # Azure AI
      PROJECT_ENDPOINT          = var.project_endpoint
      AZURE_AI_PROJECTS_API_KEY = var.azure_ai_projects_api_key
      MODEL_DEPLOYMENT_NAME     = var.model_deployment_name
      ITSM_KNOWLEDGE_AGENT_ID   = var.itsm_knowledge_agent_id

      # Bot app
      MICROSOFT_APP_ID       = var.microsoft_app_id
      MICROSOFT_APP_PASSWORD = var.microsoft_app_password

      # Local service URLs inside container group
      IVANTI_API_URL = "http://localhost:8000"
      NICE_API_URL   = "http://localhost:8001"

      # Monitoring
      APPINSIGHTS_CONNECTION_STRING = azurerm_application_insights.appi.connection_string
      LOG_LEVEL                     = "INFO"

      # KB storage references (you may use in code later)
      KB_STORAGE_ACCOUNT = azurerm_storage_account.kb.name
      KB_CONTAINER_NAME  = azurerm_storage_container.kb.name
    }
  }

  # ----------------------------
  # Ivanti API container
  # ----------------------------
  container {
    name   = "ivanti-api"
    image  = "${azurerm_container_registry.acr.login_server}/${var.ivanti_api_image_name}:${var.image_tag}"
    cpu    = var.api_cpu
    memory = var.api_memory

    ports {
      port     = 8000
      protocol = "TCP"
    }

    environment_variables = {
      LOG_LEVEL = "INFO"
    }
  }

  # ----------------------------
  # NICE API container
  # ----------------------------
  container {
    name   = "nice-api"
    image  = "${azurerm_container_registry.acr.login_server}/${var.nice_api_image_name}:${var.image_tag}"
    cpu    = var.api_cpu
    memory = var.api_memory

    ports {
      port     = 8001
      protocol = "TCP"
    }

    environment_variables = {
      LOG_LEVEL = "INFO"
    }
  }

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.law.workspace_id
      workspace_key = azurerm_log_analytics_workspace.law.primary_shared_key
    }
  }

  depends_on = [
    azurerm_key_vault_access_policy.aci_kv_reader
  ]
}