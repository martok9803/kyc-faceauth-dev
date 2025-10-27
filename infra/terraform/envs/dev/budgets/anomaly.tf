#############################################
# Anomaly Monitor (CUSTOM, tag-scoped to dev)
#############################################

resource "aws_ce_anomaly_monitor" "dev_tag_monitor" {
  name         = "dev-tag-monitor"
  monitor_type = "CUSTOM"

  monitor_specification = jsonencode({
    Tags = {
      Key    = "Environment"
      Values = ["dev"]
    }
  })
}

#############################################
# Subscription (daily email + absolute impact)
#############################################

resource "aws_ce_anomaly_subscription" "daily_email" {
  name             = "dev-anomaly-subscription"
  frequency        = "DAILY"
  monitor_arn_list = [aws_ce_anomaly_monitor.dev_tag_monitor.arn]

  # Alert when the absolute anomaly impact >= X (USD)
  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = [tostring(var.anomaly_threshold_absolute)]
    }
  }

  subscriber {
    type    = "EMAIL"
    address = var.alert_emails[0]
  }

  dynamic "subscriber" {
    for_each = length(var.alert_emails) > 1 ? slice(var.alert_emails, 1, length(var.alert_emails)) : []
    content {
      type    = "EMAIL"
      address = subscriber.value
    }
  }
}
