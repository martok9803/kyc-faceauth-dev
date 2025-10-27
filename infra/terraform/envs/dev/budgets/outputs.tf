output "budget_name" {
  value = aws_budgets_budget.monthly_cost_cap.name
}

output "anomaly_monitor_arn" {
  value = aws_ce_anomaly_monitor.dev_tag_monitor.arn
}
