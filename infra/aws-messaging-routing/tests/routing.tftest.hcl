mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_resource "aws_sns_topic" {
    defaults = {
      arn  = "arn:aws:sns:us-east-2:123456789012:temperature-readings-routing"
      name = "temperature-readings-routing"
    }
  }

  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-2:123456789012:mock-queue"
      url = "https://sqs.us-east-2.amazonaws.com/123456789012/mock-queue"
    }
  }
}

variables {
  aws_region  = "us-east-2"
  aws_profile = "temperature-iot-terraform"
}

run "routes_each_home_by_message_body" {
  command = plan

  assert {
    condition     = module.topic.topic_name == "temperature-readings-routing"
    error_message = "routing topic name drifted"
  }

  assert {
    condition     = module.topic.topic_name != "temperature-readings"
    error_message = "routing topic reuses the broadcast topic name"
  }

  assert {
    condition     = module.queue["home-a"].queue_name == "temperature-routing-home-a"
    error_message = "home-a routing queue name drifted"
  }

  assert {
    condition     = module.queue["home-b"].queue_name == "temperature-routing-home-b"
    error_message = "home-b routing queue name drifted"
  }

  assert {
    condition     = module.dlq["home-a"].queue_name == "temperature-routing-home-a-dlq"
    error_message = "home-a routing DLQ name drifted"
  }

  assert {
    condition     = module.dlq["home-b"].queue_name == "temperature-routing-home-b-dlq"
    error_message = "home-b routing DLQ name drifted"
  }

  assert {
    condition     = module.queue["home-a"].queue_name != "temperature-home-a"
    error_message = "home-a routing queue reuses the broadcast queue name"
  }

  assert {
    condition     = module.binding["home-a"].raw_message_delivery == true
    error_message = "home-a subscription must use raw message delivery"
  }

  assert {
    condition     = module.binding["home-b"].raw_message_delivery == true
    error_message = "home-b subscription must use raw message delivery"
  }

  assert {
    condition     = module.binding["home-a"].filter_policy_scope == "MessageBody"
    error_message = "home-a filter must read the message body"
  }

  assert {
    condition     = module.binding["home-b"].filter_policy_scope == "MessageBody"
    error_message = "home-b filter must read the message body"
  }

  assert {
    condition     = jsondecode(module.binding["home-a"].filter_policy).house_id == ["home-a"]
    error_message = "home-a filter does not match house_id home-a"
  }

  assert {
    condition     = jsondecode(module.binding["home-b"].filter_policy).house_id == ["home-b"]
    error_message = "home-b filter does not match house_id home-b"
  }
}
