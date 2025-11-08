"""
Rollback Trigger Lambda Function

UI에서 호출하여 GitHub Actions 롤백 워크플로우를 트리거합니다.
사용자가 롤백 버튼을 누르면 이 Lambda가 실행됩니다.
"""

import json
import os
import boto3
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Environment variables
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.environ.get('GITHUB_REPO_OWNER', 'Softbank-mango')
GITHUB_REPO_NAME = os.environ.get('GITHUB_REPO_NAME', 'deplight-infra')
WORKFLOW_FILE = 'rollback.yml'
WORKFLOW_BRANCH = 'roll-back'

# DynamoDB for audit logging
dynamodb = boto3.resource('dynamodb')
audit_table_name = os.environ.get('AUDIT_TABLE_NAME', 'rollback-audit-log')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for triggering rollback workflow

    Event structure (from API Gateway):
    {
        "body": {
            "environment": "dev" | "prod",
            "rollback_type": "terraform" | "ecs-taskdef",
            "image_tag": "abc123d" (optional - uses last successful if not provided),
            "user_id": "user@example.com",
            "reason": "Manual rollback via UI"
        }
    }
    """

    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        # Validate required fields
        environment = body.get('environment')
        rollback_type = body.get('rollback_type', 'terraform')
        user_id = body.get('user_id')
        reason = body.get('reason', 'Manual rollback via UI')

        if not environment:
            return error_response(400, "environment is required")

        if environment not in ['dev', 'prod']:
            return error_response(400, "environment must be 'dev' or 'prod'")

        if not user_id:
            return error_response(400, "user_id is required")

        # Get image tag (use last successful if not provided)
        image_tag = body.get('image_tag')
        if not image_tag:
            image_tag = get_last_successful_image_tag(environment)
            if not image_tag:
                return error_response(404, f"No previous successful deployment found for {environment}")

        # Log audit record
        audit_id = log_rollback_request(
            user_id=user_id,
            environment=environment,
            rollback_type=rollback_type,
            image_tag=image_tag,
            reason=reason
        )

        # Trigger GitHub Actions workflow
        workflow_run_id = trigger_github_workflow(
            environment=environment,
            rollback_type=rollback_type,
            image_tag=image_tag
        )

        # Update audit log with workflow run ID
        update_audit_log(audit_id, workflow_run_id)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'status': 'success',
                'message': 'Rollback initiated',
                'data': {
                    'audit_id': audit_id,
                    'workflow_run_id': workflow_run_id,
                    'environment': environment,
                    'rollback_type': rollback_type,
                    'image_tag': image_tag,
                    'estimated_duration': '3-5 minutes',
                    'monitor_url': f'https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions'
                }
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, f"Internal server error: {str(e)}")


def get_last_successful_image_tag(environment: str) -> Optional[str]:
    """
    Get last successful image tag from GitHub artifacts

    Returns:
        Image tag string or None if not found
    """
    try:
        # Get recent successful workflow runs
        url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/deploy.yml/runs'
        headers = {
            'Authorization': f'Bearer {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {
            'status': 'success',
            'per_page': 5
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        runs = response.json().get('workflow_runs', [])
        if not runs:
            return None

        # Get artifacts from the latest successful run
        latest_run = runs[0]
        artifacts_url = latest_run['artifacts_url']

        artifacts_response = requests.get(artifacts_url, headers=headers)
        artifacts_response.raise_for_status()

        artifacts = artifacts_response.json().get('artifacts', [])

        # Find the deployment state artifact for this environment
        for artifact in artifacts:
            if artifact['name'] == f'last-successful-deployment-{environment}':
                # Download artifact and extract image tag
                download_url = artifact['archive_download_url']
                download_response = requests.get(download_url, headers=headers)

                # Note: In production, you'd need to unzip and read the file
                # For now, we'll use a simpler approach: return the commit SHA from the run
                return latest_run['head_sha'][:7]  # Short SHA as image tag

        return None

    except Exception as e:
        print(f"Error getting last successful image tag: {str(e)}")
        return None


def trigger_github_workflow(
    environment: str,
    rollback_type: str,
    image_tag: str
) -> str:
    """
    Trigger GitHub Actions rollback workflow

    Returns:
        Workflow run ID
    """
    url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches'

    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

    payload = {
        'ref': WORKFLOW_BRANCH,
        'inputs': {
            'environment': environment,
            'rollback_type': rollback_type,
            'image_tag': image_tag,
            'confirm': 'ROLLBACK'  # Auto-confirm for API-triggered rollbacks
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    # GitHub doesn't return the run ID directly, so we need to fetch recent runs
    # and find the one we just created
    import time
    time.sleep(2)  # Wait a bit for the workflow to be created

    runs_url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/runs'
    runs_response = requests.get(runs_url, headers=headers, params={'per_page': 1})
    runs_response.raise_for_status()

    runs = runs_response.json().get('workflow_runs', [])
    if runs:
        return str(runs[0]['id'])

    return 'unknown'


def log_rollback_request(
    user_id: str,
    environment: str,
    rollback_type: str,
    image_tag: str,
    reason: str
) -> str:
    """
    Log rollback request to DynamoDB for audit trail

    Returns:
        Audit ID
    """
    try:
        table = dynamodb.Table(audit_table_name)

        audit_id = f"{environment}-{int(datetime.utcnow().timestamp())}"

        table.put_item(Item={
            'audit_id': audit_id,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'environment': environment,
            'rollback_type': rollback_type,
            'image_tag': image_tag,
            'reason': reason,
            'status': 'initiated',
            'workflow_run_id': None
        })

        return audit_id

    except Exception as e:
        print(f"Error logging audit: {str(e)}")
        # Don't fail the rollback if audit logging fails
        return f"audit-{int(datetime.utcnow().timestamp())}"


def update_audit_log(audit_id: str, workflow_run_id: str) -> None:
    """Update audit log with workflow run ID"""
    try:
        table = dynamodb.Table(audit_table_name)
        table.update_item(
            Key={'audit_id': audit_id},
            UpdateExpression='SET workflow_run_id = :wid, #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':wid': workflow_run_id,
                ':status': 'triggered'
            }
        )
    except Exception as e:
        print(f"Error updating audit log: {str(e)}")


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Return error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'error',
            'message': message
        })
    }
