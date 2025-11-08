# Observability Suite Module Design (T-09)

## Objective
Create a Terraform module (`infrastructure/modules/observability-suite`) that provisions the baseline observability assets required for the ECS service delivered in this project. The module must be opinionated enough to cover:

- A CloudWatch dashboard focused on the primary ECS service (CPU, memory, task count, ALB target response, CodeDeploy status widgets as data becomes available).
- Metric alarms to guardrail the ECS task/service health (CPU/Mem, 5XX/latency via ALB), with outputs wired so downstream tasks (T-11 smoke tests/notifications) can link or subscribe.
- CloudWatch Logs retention controls for key log groups (ECS, application, CodeDeploy) so retention changes are centralized.
- An optional X-Ray sampling rule to keep trace volume predictable while still enabling distributed tracing visibility.

## Module Layout
```
infrastructure/modules/observability-suite/
  main.tf          # resources (dashboard, alarms, log retention, X-Ray)
  variables.tf     # interface definition
  outputs.tf       # dashboard/alarm identifiers for consumers
  templates/
    ecs_dashboard.json.tpl   # dashboard body rendered via templatefile()
```

The module intentionally keeps Terraform logic lightweight by delegating the CloudWatch dashboard body to a JSON template. Future widgets (CodeDeploy, Lambda analyzer, etc.) can be appended inside `templates/ecs_dashboard.json.tpl` without touching the module contract.

## Inputs
| Variable | Type | Purpose |
| --- | --- | --- |
| `environment` | `string` | Included in resource names/labels (e.g., `staging`). |
| `service_name` | `string` | ECS service identifier used in metric dimensions. |
| `cluster_name` | `string` | ECS cluster dimension for dashboards/alarms. |
| `alb_target_group_arn_suffix` | `string` | ALB target group suffix for latency/5XX metrics (optional). |
| `log_group_names` | `list(string)` | CloudWatch log groups that need uniform retention. |
| `log_retention_in_days` | `number` | Retention period applied to each log group (default 30). |
| `xray_sampling_enabled` | `bool` | Toggles creation of `aws_xray_sampling_rule`. |
| `xray_fixed_rate` | `number` | Sampling rate (0–1) used when rule is enabled (default 0.1). |
| `alarm_topic_arn` | `string` | SNS topic ARN to wire alarm actions (optional; alarms will exist without actions if unset). |
| `cpu_high_threshold` | `number` | % CPU utilization that should trigger an alarm (default 80). |
| `memory_high_threshold` | `number` | % memory utilization threshold (default 80). |
| `alb_5xx_threshold` | `number` | Count of 5XX errors over evaluation period that should raise an alarm (default 5). |
| `alb_latency_threshold_ms` | `number` | P99 latency threshold for the ALB target group (default 1500). |
| `tags` | `map(string)` | Standard tags applied to resources. |

Inputs are scoped so the initial T-09 delivery can focus on ECS; additional services (e.g., Lambda analyzer metrics) can be incorporated later by extending the template and adding optional inputs.

## Outputs
| Output | Description |
| --- | --- |
| `dashboard_name` | CloudWatch dashboard name (also serves as ARN suffix). |
| `dashboard_body` | Rendered JSON for traceability/debugging. |
| `alarm_arns` | Map of named alarms (`cpu_high`, `memory_high`, `alb_5xx`, `alb_latency`). |
| `xray_sampling_rule_arn` | ARN of the sampling rule when enabled, `null` otherwise. |

Downstream workflows can reference `alarm_arns` to post links in Slack (T-11) or attach SNS subscriptions elsewhere.

## Usage Pattern
Environment stacks (e.g., `infrastructure/environments/dev/main.tf`) will instantiate the module after ECS/ALB resources exist. Only include log group names that are not already managed elsewhere (the ECS module currently creates `/ecs/<service>` and sets retention itself):

```hcl
module "observability" {
  source = "../../modules/observability-suite"

  environment                = var.environment
  service_name               = module.ecs.service_name
  cluster_name               = module.ecs.cluster_name
  alb_target_group_arn_suffix = module.alb.target_group_arn_suffix

  log_group_names        = [module.ecs.log_group_name]
  log_retention_in_days  = 30
  xray_sampling_enabled  = true
  xray_fixed_rate        = 0.1
  alarm_topic_arn        = aws_sns_topic.deploy_notifications.arn

  tags = local.common_tags
}
```

This placement satisfies the dependency on T-03 (module scaffolding) while leaving room to wire CodeDeploy/ECR metrics later. The module will not apply destructive changes outside observability resources, so it is safe to iterate as future tasks add widgets/alarms.

## Open Questions / Next Steps
1. Confirm the canonical list of log groups to manage (ECS service log group is known; CodeDeploy/Lambda analyzer groups need names once created).  
2. Decide whether alarms should create SNS topics internally when `alarm_topic_arn` is empty or leave actions unset (current plan: unset).  
3. Validate X-Ray enablement strategy for ECS tasks (requires task definition instrumentation; module only manages sampling rule).

Answering these ahead of implementation will keep Terraform plans clean and avoid rework during T-11 when notifications hook into alarm ARNs.
