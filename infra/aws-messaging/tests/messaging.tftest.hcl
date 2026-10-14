mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }
}

variables {
  aws_region  = "us-west-2"
  aws_profile = "temperature-iot-demo"
}

run "fanout_is_raw_and_named" {
  command = plan

  assert {
    condition     = aws_sns_topic.readings.name == "temperature-readings"
    error_message = "topic name drifted from temperature-readings"
  }

  assert {
    condition     = aws_sqs_queue.home["home-a"].name == "temperature-home-a"
    error_message = "home-a queue name drifted"
  }

  assert {
    condition     = aws_sqs_queue.home["home-b"].name == "temperature-home-b"
    error_message = "home-b queue name drifted"
  }

  assert {
    condition     = aws_sqs_queue.dlq["home-a"].name == "temperature-home-a-dlq"
    error_message = "home-a dead-letter queue name drifted"
  }

  assert {
    condition     = aws_sqs_queue.dlq["home-b"].name == "temperature-home-b-dlq"
    error_message = "home-b dead-letter queue name drifted"
  }

  assert {
    condition     = aws_sns_topic_subscription.home["home-a"].raw_message_delivery == true
    error_message = "home-a subscription must use raw message delivery"
  }

  assert {
    condition     = aws_sns_topic_subscription.home["home-b"].raw_message_delivery == true
    error_message = "home-b subscription must use raw message delivery"
  }

  assert {
    condition     = aws_sns_topic_subscription.home["home-a"].protocol == "sqs"
    error_message = "home-a subscription protocol must be sqs"
  }

  assert {
    condition     = aws_sns_topic_subscription.home["home-b"].protocol == "sqs"
    error_message = "home-b subscription protocol must be sqs"
  }
}
