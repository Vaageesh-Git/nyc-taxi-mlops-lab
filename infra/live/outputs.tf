# S0: expose the outputs listed in contracts/runtime.yaml under terraform_outputs.
# scripts/register-runner.sh, scripts/catch-up.sh and the grader read them by those names.

output "app_public_ip" {
  description = "Public IP of the app host"
  value       = module.app_host.public_ip
}

output "app_instance_id" {
  description = "Instance ID of the app host"
  value       = module.app_host.instance_id
}

output "platform_instance_id" {
  description = "Instance ID of the platform host"
  value       = module.platform_host.instance_id
}

output "platform_private_ip" {
  description = "Private IP of the platform host"
  value       = module.platform_host.private_ip
}

output "llm_instance_id" {
  description = "Instance ID of the LLM host"
  value       = module.llm_host.instance_id
}

output "llm_private_ip" {
  description = "Private IP of the LLM host"
  value       = module.llm_host.private_ip
}

output "rds_endpoint" {
  description = "Postgres endpoint for Dagster and MLflow"
  value       = module.rds.endpoint
}

output "artifact_bucket" {
  description = "Artifact bucket for MLflow and pipelines"
  value       = module.artifact_bucket.name
}
