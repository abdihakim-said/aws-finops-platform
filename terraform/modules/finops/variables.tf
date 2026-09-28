variable "name" {
  description = "Prefix for every resource this module creates."
  type        = string
  default     = "finops"
}

variable "regions" {
  description = "Regions to scan. Defaults to the provider's region."
  type        = list(string)
  default     = []
}

variable "schedule" {
  description = "EventBridge schedule for the read-only scan."
  type        = string
  default     = "cron(0 6 ? * MON *)" # Mondays 06:00 UTC
}

variable "notification_email" {
  description = "Email address that receives each plan. Leave null to skip the subscription."
  type        = string
  default     = null
}

variable "enable_apply" {
  description = "Allow the apply function to act on approved plans. Off by default: the tool only reports."
  type        = bool
  default     = false
}

variable "snapshot_min_age_days" {
  description = "Snapshots younger than this are never proposed for deletion."
  type        = number
  default     = 30
}

variable "idle_window_days" {
  description = "Look-back window for idle load balancers and databases."
  type        = number
  default     = 14
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
