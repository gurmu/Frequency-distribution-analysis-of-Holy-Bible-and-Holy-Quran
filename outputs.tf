output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  value = azurerm_container_registry.acr.admin_username
}

output "acr_admin_password" {
  value     = azurerm_container_registry.acr.admin_password
  sensitive = true
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.law.name
}

output "app_insights_connection_string" {
  value     = azurerm_application_insights.appi.connection_string
  sensitive = true
}

output "teams_bot_fqdn" {
  value = azurerm_container_group.teams_bot.fqdn
}

output "ivanti_api_fqdn" {
  value = azurerm_container_group.ivanti_api.fqdn
}

output "nice_api_fqdn" {
  value = azurerm_container_group.nice_api.fqdn
}

output "teams_bot_messages_endpoint" {
  value = "http://${azurerm_container_group.teams_bot.fqdn}:3978/api/messages"
}