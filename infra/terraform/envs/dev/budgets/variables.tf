variable "aws_region" {
  description = "AWS region for API calls (Budgets is global but needs a region)."
  type        = string
  default     = "eu-central-1"
}

variable "budget_limit_amount_eur" {
  description = "Monthly budget cap in EUR for dev."
  type        = number
  default     = 5
}

variable "alert_emails" {
  description = "Email recipients for budget and anomaly alerts."
  type        = list(string)
  default     = ["martinkirov9803@gmail.com"]
}

variable "anomaly_threshold_absolute" {
  description = "Absolute anomaly threshold in your billing currency. If an anomaly exceeds this amount/day, alert."
  type        = number
  default     = 1
}

variable "budget_name" {
  description = "Name of the monthly dev budget."
  type        = string
  default     = "dev-monthly-budget"
}
