variable "aws_region" {
  description = "AWS region for the messaging resources."
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "Named AWS CLI profile. Access keys stay in the local AWS CLI configuration."
  type        = string
  default     = "temperature-iot-demo"
}

variable "topic_name" {
  description = "SNS topic that receives one temperature event and fans it out."
  type        = string
  default     = "temperature-readings"
}

variable "max_receive_count" {
  description = "Receives before SQS moves a message to that queue's dead-letter queue."
  type        = number
  default     = 5
}

variable "queues" {
  description = "Home queues and the dead-letter queue for each home."
  type = map(object({
    queue_name = string
    dlq_name   = string
  }))
  default = {
    home-a = {
      queue_name = "temperature-home-a"
      dlq_name   = "temperature-home-a-dlq"
    }
    home-b = {
      queue_name = "temperature-home-b"
      dlq_name   = "temperature-home-b-dlq"
    }
  }
}
