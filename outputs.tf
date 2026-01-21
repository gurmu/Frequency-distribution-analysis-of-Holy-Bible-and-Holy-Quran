output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "location" {
  value = azurerm_resource_group.rg.location
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}

output "app_insights_name" {
  value = azurerm_application_insights.appi.name
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.law.name
}

output "kb_storage_account_name" {
  value = azurerm_storage_account.kb.name
}

output "kb_container_name" {
  value = azurerm_storage_container.kb.name
}

output "aci_name" {
  value = azurerm_container_group.itsm.name
}

output "aci_fqdn" {
  value = try(azurerm_container_group.itsm.fqdn, "")
}

output "teams_bot_messaging_endpoint" {
  value = var.expose_public_fqdn ? "http://${azurerm_container_group.itsm.fqdn}:3978/api/messages" : ""
}