data "aws_caller_identity" "current" {}

locals {
  tags = {
    Project   = "temperature-iot"
    Component = "messaging"
  }
}

resource "aws_sns_topic" "readings" {
  name = var.topic_name
  tags = local.tags
}

resource "aws_sqs_queue" "dlq" {
  for_each = var.queues

  name = each.value.dlq_name
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns = [
      "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${each.value.queue_name}",
    ]
  })
  tags = local.tags
}

resource "aws_sqs_queue" "home" {
  for_each = var.queues

  name = each.value.queue_name
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = var.max_receive_count
  })
  tags = local.tags
}

data "aws_iam_policy_document" "home" {
  for_each = var.queues

  statement {
    sid       = "AllowTemperatureReadingsTopic"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.home[each.key].arn]

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_sns_topic.readings.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "home" {
  for_each = var.queues

  queue_url = aws_sqs_queue.home[each.key].url
  policy    = data.aws_iam_policy_document.home[each.key].json
}

resource "aws_sns_topic_subscription" "home" {
  for_each = var.queues

  topic_arn            = aws_sns_topic.readings.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.home[each.key].arn
  raw_message_delivery = true

  depends_on = [aws_sqs_queue_policy.home]
}
