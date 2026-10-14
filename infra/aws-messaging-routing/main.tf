data "aws_caller_identity" "current" {}

locals {
  tags = {
    Project   = "temperature-iot"
    Component = "messaging-routing"
  }
}

module "topic" {
  source = "../../../../../10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sns"

  name = var.topic_name
  tags = local.tags
}

module "dlq" {
  source   = "../../../../../10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sqs"
  for_each = var.homes

  name = each.value.dlq_name
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns = [
      "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${each.value.queue_name}",
    ]
  })
  tags = local.tags
}

module "queue" {
  source   = "../../../../../10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sqs"
  for_each = var.homes

  name = each.value.queue_name
  redrive_policy = jsonencode({
    deadLetterTargetArn = module.dlq[each.key].queue_arn
    maxReceiveCount     = var.max_receive_count
  })
  tags = local.tags
}

module "binding" {
  source   = "../../../../../10_Infrastructure/01_Terraform/terraform-modules/modules/aws/messaging/sns-sqs-binding"
  for_each = var.homes

  topic_arn            = module.topic.topic_arn
  queue_arn            = module.queue[each.key].queue_arn
  queue_url            = module.queue[each.key].queue_url
  raw_message_delivery = true
  filter_policy_scope  = "MessageBody"
  filter_policy        = jsonencode({ house_id = [each.key] })
}
