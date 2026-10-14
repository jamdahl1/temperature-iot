variable "aws_region" {
  description = "AWS region for the routing resources."
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "Named AWS CLI profile. Access keys stay in the local AWS CLI configuration."
  type        = string
  default     = "temperature-iot-terraform"
}

variable "topic_name" {
  description = "SNS topic for home-filtered temperature events."
  type        = string
  default     = "temperature-readings-routing"
}

variable "max_receive_count" {
  description = "Receives before SQS moves a message to that home's dead-letter queue."
  type        = number
  default     = 5
}

variable "homes" {
  description = "Home id to queue names. The map key is the house_id SNS filter value."
  type = map(object({
    queue_name = string
    dlq_name   = string
  }))
  default = {
    home-a = {
      queue_name = "temperature-routing-home-a"
      dlq_name   = "temperature-routing-home-a-dlq"
    }
    home-b = {
      queue_name = "temperature-routing-home-b"
      dlq_name   = "temperature-routing-home-b-dlq"
    }
  }
}
