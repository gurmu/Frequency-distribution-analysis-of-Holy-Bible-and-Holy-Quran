locals {
  tags = {
    application = "itsm-multiagent"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# Log Analytics for container logs
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.name_prefix}-law-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

# Application Insights (workspace-based)
resource "azurerm_application_insights" "appi" {
  name                = "${var.name_prefix}-appi-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.law.id
  tags                = local.tags
}

# ACR (admin enabled so ACI can pull without extra RBAC/role assignments)
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = local.tags
}

# Common ACR creds block for ACI pulls
locals {
  acr_server   = azurerm_container_registry.acr.login_server
  acr_username = azurerm_container_registry.acr.admin_username
  acr_password = azurerm_container_registry.acr.admin_password
}

#
# ACI: Teams Bot
#
resource "azurerm_container_group" "teams_bot" {
  name                = "${var.name_prefix}-teams-bot-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  os_type         = "Linux"
  ip_address_type = "Public"
  dns_name_label  = "${var.dns_label_prefix}-teams-${var.environment}-${random_string.suffix.result}"

  # Log Analytics integration
  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.law.workspace_id
      workspace_key = azurerm_log_analytics_workspace.law.primary_shared_key
    }
  }

  image_registry_credential {
    server   = local.acr_server
    username = local.acr_username
    password = local.acr_password
  }

  container {
    name   = "teams-bot"
    image  = "${local.acr_server}/${var.teams_bot_image}"
    cpu    = var.teams_cpu
    memory = var.teams_mem

    ports {
      port     = 3978
      protocol = "TCP"
    }

    environment_variables = {
      # External service endpoints (call your own APIs via public FQDNs unless you later move to VNet)
      IVANTI_API_URL = "http://${azurerm_container_group.ivanti_api.fqdn}:8000"
      NICE_API_URL   = "http://${azurerm_container_group.nice_api.fqdn}:8001"

      # Azure AI settings
      PROJECT_ENDPOINT       = var.project_endpoint
      MODEL_DEPLOYMENT_NAME  = var.model_deployment_name
      ITSM_KNOWLEDGE_AGENT_ID = var.itsm_knowledge_agent_id
      INVESTIGATION_AGENT_ID  = var.investigation_agent_id

      # App Insights (optional instrumentation if your app uses it)
      APPINSIGHTS_CONNECTION_STRING = azurerm_application_insights.appi.connection_string
    }

    secure_environment_variables = {
      AZURE_AI_PROJECTS_API_KEY = var.azure_ai_projects_api_key
      MICROSOFT_APP_ID          = var.microsoft_app_id
      MICROSOFT_APP_PASSWORD    = var.microsoft_app_password
    }
  }

  tags = local.tags

  depends_on = [
    azurerm_container_registry.acr,
    azurerm_log_analytics_workspace.law,
    azurerm_container_group.ivanti_api,
    azurerm_container_group.nice_api
  ]
}

#
# ACI: Ivanti API
#
resource "azurerm_container_group" "ivanti_api" {
  name                = "${var.name_prefix}-ivanti-api-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  os_type         = "Linux"
  ip_address_type = "Public"
  dns_name_label  = "${var.dns_label_prefix}-ivanti-${var.environment}-${random_string.suffix.result}"

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.law.workspace_id
      workspace_key = azurerm_log_analytics_workspace.law.primary_shared_key
    }
  }

  image_registry_credential {
    server   = local.acr_server
    username = local.acr_username
    password = local.acr_password
  }

  container {
    name   = "ivanti-api"
    image  = "${local.acr_server}/${var.ivanti_api_image}"
    cpu    = var.api_cpu
    memory = var.api_mem

    ports {
      port     = 8000
      protocol = "TCP"
    }

    environment_variables = {
      IVANTI_BASE_URL                 = var.ivanti_external_base_url
      APPINSIGHTS_CONNECTION_STRING   = azurerm_application_insights.appi.connection_string
    }
  }

  tags = local.tags

  depends_on = [
    azurerm_container_registry.acr,
    azurerm_log_analytics_workspace.law
  ]
}

#
# ACI: NICE API
#
resource "azurerm_container_group" "nice_api" {
  name                = "${var.name_prefix}-nice-api-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  os_type         = "Linux"
  ip_address_type = "Public"
  dns_name_label  = "${var.dns_label_prefix}-nice-${var.environment}-${random_string.suffix.result}"

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.law.workspace_id
      workspace_key = azurerm_log_analytics_workspace.law.primary_shared_key
    }
  }

  image_registry_credential {
    server   = local.acr_server
    username = local.acr_username
    password = local.acr_password
  }

  container {
    name   = "nice-api"
    image  = "${local.acr_server}/${var.nice_api_image}"
    cpu    = var.api_cpu
    memory = var.api_mem

    ports {
      port     = 8001
      protocol = "TCP"
    }

    environment_variables = {
      NICE_BASE_URL                  = var.nice_external_base_url
      APPINSIGHTS_CONNECTION_STRING  = azurerm_application_insights.appi.connection_string
    }
  }

  tags = local.tags

  depends_on = [
    azurerm_container_registry.acr,
    azurerm_log_analytics_workspace.law
  ]
}