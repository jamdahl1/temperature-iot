output "aws_region" {
  description = "Region where the messaging resources were created."
  value       = var.aws_region
}

output "topic_name" {
  description = "SNS topic name."
  value       = aws_sns_topic.readings.name
}

output "topic_arn" {
  description = "SNS topic ARN."
  value       = aws_sns_topic.readings.arn
}

output "home_a_queue_url" {
  description = "Home A queue URL for SQS_QUEUE_URL."
  value       = aws_sqs_queue.home["home-a"].url
}

output "home_a_queue_arn" {
  description = "Home A queue ARN."
  value       = aws_sqs_queue.home["home-a"].arn
}

output "home_b_queue_url" {
  description = "Home B queue URL for SQS_QUEUE_URL."
  value       = aws_sqs_queue.home["home-b"].url
}

output "home_b_queue_arn" {
  description = "Home B queue ARN."
  value       = aws_sqs_queue.home["home-b"].arn
}

output "home_a_dlq_url" {
  description = "Home A dead-letter queue URL."
  value       = aws_sqs_queue.dlq["home-a"].url
}

output "home_a_dlq_arn" {
  description = "Home A dead-letter queue ARN."
  value       = aws_sqs_queue.dlq["home-a"].arn
}

output "home_b_dlq_url" {
  description = "Home B dead-letter queue URL."
  value       = aws_sqs_queue.dlq["home-b"].url
}

output "home_b_dlq_arn" {
  description = "Home B dead-letter queue ARN."
  value       = aws_sqs_queue.dlq["home-b"].arn
}

output "consumer_a_environment" {
  description = "Future Home A consumer configuration. No credentials."
  value = {
    HOME_ID       = "home-a"
    SQS_QUEUE_URL = aws_sqs_queue.home["home-a"].url
    AWS_REGION    = var.aws_region
  }
}

output "consumer_b_environment" {
  description = "Future Home B consumer configuration. No credentials."
  value = {
    HOME_ID       = "home-b"
    SQS_QUEUE_URL = aws_sqs_queue.home["home-b"].url
    AWS_REGION    = var.aws_region
  }
}
