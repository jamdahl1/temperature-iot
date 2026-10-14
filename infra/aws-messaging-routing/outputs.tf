output "aws_region" {
  description = "Region where the routing resources were created."
  value       = var.aws_region
}

output "topic_name" {
  description = "SNS topic name."
  value       = module.topic.topic_name
}

output "topic_arn" {
  description = "SNS topic ARN."
  value       = module.topic.topic_arn
}

output "home_a_queue_url" {
  description = "Home A routing queue URL."
  value       = module.queue["home-a"].queue_url
}

output "home_a_queue_arn" {
  description = "Home A routing queue ARN."
  value       = module.queue["home-a"].queue_arn
}

output "home_b_queue_url" {
  description = "Home B routing queue URL."
  value       = module.queue["home-b"].queue_url
}

output "home_b_queue_arn" {
  description = "Home B routing queue ARN."
  value       = module.queue["home-b"].queue_arn
}

output "home_a_dlq_url" {
  description = "Home A routing dead-letter queue URL."
  value       = module.dlq["home-a"].queue_url
}

output "home_a_dlq_arn" {
  description = "Home A routing dead-letter queue ARN."
  value       = module.dlq["home-a"].queue_arn
}

output "home_b_dlq_url" {
  description = "Home B routing dead-letter queue URL."
  value       = module.dlq["home-b"].queue_url
}

output "home_b_dlq_arn" {
  description = "Home B routing dead-letter queue ARN."
  value       = module.dlq["home-b"].queue_arn
}

output "home_a_subscription_arn" {
  description = "Home A subscription ARN."
  value       = module.binding["home-a"].subscription_arn
}

output "home_b_subscription_arn" {
  description = "Home B subscription ARN."
  value       = module.binding["home-b"].subscription_arn
}

output "consumer_a_environment" {
  description = "Home A adapter configuration. No credentials."
  value = {
    HOME_ID       = "home-a"
    SQS_QUEUE_URL = module.queue["home-a"].queue_url
    AWS_REGION    = var.aws_region
  }
}

output "consumer_b_environment" {
  description = "Home B adapter configuration. No credentials."
  value = {
    HOME_ID       = "home-b"
    SQS_QUEUE_URL = module.queue["home-b"].queue_url
    AWS_REGION    = var.aws_region
  }
}
