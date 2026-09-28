terraform {
  required_version = ">= 1.5"
}

provider "aws" {
  region = "eu-west-2"
}

module "finops" {
  source = "../../modules/finops"

  regions            = ["eu-west-2", "us-east-1"]
  notification_email = "platform-team@example.com"
  enable_apply       = false # report-only until the team trusts the plans

  tags = {
    owner = "platform"
  }
}

output "apply_command" {
  value = module.finops.apply_command
}
