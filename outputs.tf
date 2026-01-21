output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  value     = azurerm_container_registry.acr.admin_username
  sensitive = true
}

output "acr_admin_password" {
  value     = azurerm_container_registry.acr.admin_password
  sensitive = true
}

output "key_vault_name" {
  value = azurerm_key_vault.kv.name
}

output "container_group_fqdn" {
  value = azurerm_container_group.aci.fqdn
}

output "teams_bot_messages_endpoint" {
  value = "http://${azurerm_container_group.aci.fqdn}:3978/api/messages"
}