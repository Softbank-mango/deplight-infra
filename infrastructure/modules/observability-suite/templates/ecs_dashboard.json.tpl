{
  "start": "-PT6H",
  "periodOverride": "inherit",
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "${dashboard_title} CPU %",
        "region": "${region}",
        "liveData": true,
        "legend": {
          "position": "bottom"
        },
        "metrics": [
          [
            "AWS/ECS",
            "CPUUtilization",
            "ClusterName",
            "${cluster_name}",
            "ServiceName",
            "${service_name}"
          ]
        ],
        "stat": "Average",
        "period": 60,
        "view": "timeSeries",
        "stacked": false
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "${dashboard_title} Memory %",
        "region": "${region}",
        "metrics": [
          [
            "AWS/ECS",
            "MemoryUtilization",
            "ClusterName",
            "${cluster_name}",
            "ServiceName",
            "${service_name}"
          ]
        ],
        "stat": "Average",
        "period": 60,
        "view": "timeSeries",
        "stacked": false
      }
    },
    {
      "type": "metric",
      "x": 0,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "${dashboard_title} Running Tasks",
        "region": "${region}",
        "metrics": [
          [
            "AWS/ECS",
            "ServiceRunningTasksCount",
            "ClusterName",
            "${cluster_name}",
            "ServiceName",
            "${service_name}"
          ]
        ],
        "stat": "Average",
        "period": 60,
        "view": "timeSeries",
        "stacked": false
      }
    }%{ if include_alb },
    {
      "type": "metric",
      "x": 12,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "ALB Target 5XX Count",
        "region": "${region}",
        "metrics": [
          [
            "AWS/ApplicationELB",
            "HTTPCode_Target_5XX_Count",
            "TargetGroup",
            "${target_group_dim}"
          ]
        ],
        "stat": "Sum",
        "period": 60,
        "view": "timeSeries",
        "stacked": false
      }
    },
    {
      "type": "metric",
      "x": 0,
      "y": 12,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "ALB Target Response Time (p99)",
        "region": "${region}",
        "metrics": [
          [
            "AWS/ApplicationELB",
            "TargetResponseTime",
            "TargetGroup",
            "${target_group_dim}"
          ]
        ],
        "stat": "p99",
        "period": 60,
        "view": "timeSeries",
        "stacked": false
      }
    }%{ endif }
  ]
}
