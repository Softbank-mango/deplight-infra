# Rollback Trigger Lambda

UI에서 배포 롤백을 트리거하기 위한 Lambda 함수입니다.

## 🎯 기능

사용자가 UI에서 롤백 버튼을 클릭하면:
1. 이 Lambda 함수가 호출됨
2. GitHub Actions 롤백 워크플로우를 트리거
3. DynamoDB에 감사 로그 기록
4. 롤백 진행 상황 추적 가능

## 🚀 빠른 시작

### 1. 배포 패키지 생성

```bash
cd lambda/rollback-trigger

# 의존성 설치
pip install -r requirements.txt -t .

# ZIP 파일 생성
zip -r rollback-trigger.zip lambda_function.py requests/ boto3/ urllib3/ certifi/ charset_normalizer/ idna/
```

### 2. Lambda 함수 생성 (AWS CLI)

```bash
# Lambda 함수 생성
aws lambda create-function \
  --function-name rollback-trigger \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://rollback-trigger.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{GITHUB_TOKEN=ghp_xxx,GITHUB_REPO_OWNER=Softbank-mango,GITHUB_REPO_NAME=deplight-infra,AUDIT_TABLE_NAME=rollback-audit-log}"
```

### 3. Terraform으로 배포 (권장)

```bash
# terraform-example.tf 참고
terraform init
terraform plan -var="github_token=ghp_xxx"
terraform apply -var="github_token=ghp_xxx"
```

배포 후 출력:
```
Outputs:

api_endpoint = "https://abc123.execute-api.ap-northeast-2.amazonaws.com/prod/rollback"
lambda_function_name = "rollback-trigger"
dynamodb_table_name = "rollback-audit-log"
```

## 🔐 필요한 권한

### GitHub Personal Access Token

다음 권한이 있는 GitHub PAT 필요:
- `repo` (전체 저장소 접근)
- `workflow` (GitHub Actions 워크플로우 트리거)

생성 방법:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. 권한 선택: `repo`, `workflow`
4. 생성 후 토큰 복사

### IAM 역할

Lambda 함수 실행 역할에 필요한 권한:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/rollback-audit-log"
    }
  ]
}
```

## 📡 API 사용법

### Request

```http
POST /rollback
Content-Type: application/json

{
  "environment": "prod",
  "rollback_type": "terraform",
  "user_id": "user@example.com",
  "reason": "Manual rollback via UI",
  "image_tag": "abc123d"  // Optional - 생략 시 마지막 성공 버전 사용
}
```

### Response (Success)

```json
{
  "status": "success",
  "message": "Rollback initiated",
  "data": {
    "audit_id": "prod-1699459200",
    "workflow_run_id": "6789012345",
    "environment": "prod",
    "rollback_type": "terraform",
    "image_tag": "abc123d",
    "estimated_duration": "3-5 minutes",
    "monitor_url": "https://github.com/Softbank-mango/deplight-infra/actions"
  }
}
```

### Response (Error)

```json
{
  "status": "error",
  "message": "environment is required"
}
```

## 🧪 테스트

### 로컬 테스트

```python
# test.py
import json
from lambda_function import lambda_handler

# Test event
event = {
    'body': json.dumps({
        'environment': 'dev',
        'rollback_type': 'terraform',
        'user_id': 'test@example.com',
        'reason': 'Test rollback'
    })
}

# Invoke handler
result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
```

실행:
```bash
python test.py
```

### API Gateway 테스트

```bash
curl -X POST https://your-api-gateway-url.amazonaws.com/prod/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "environment": "dev",
    "rollback_type": "terraform",
    "user_id": "test@example.com",
    "reason": "Test via curl"
  }'
```

## 📊 모니터링

### CloudWatch Logs

```bash
# 실시간 로그 확인
aws logs tail /aws/lambda/rollback-trigger --follow

# 최근 에러 검색
aws logs filter-log-events \
  --log-group-name /aws/lambda/rollback-trigger \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### DynamoDB 감사 로그

```bash
# 최근 롤백 기록 조회
aws dynamodb scan \
  --table-name rollback-audit-log \
  --limit 10 \
  --query 'Items[*].[audit_id.S, timestamp.S, user_id.S, environment.S, status.S]' \
  --output table

# 특정 환경의 롤백 기록
aws dynamodb query \
  --table-name rollback-audit-log \
  --index-name environment-timestamp-index \
  --key-condition-expression "environment = :env" \
  --expression-attribute-values '{":env":{"S":"prod"}}' \
  --scan-index-forward false \
  --limit 10
```

### CloudWatch Metrics

Lambda 메트릭 확인:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=rollback-trigger \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

## 🔧 환경 변수

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `GITHUB_TOKEN` | ✅ | - | GitHub Personal Access Token |
| `GITHUB_REPO_OWNER` | ❌ | `Softbank-mango` | GitHub 조직/사용자명 |
| `GITHUB_REPO_NAME` | ❌ | `deplight-infra` | 저장소 이름 |
| `AUDIT_TABLE_NAME` | ❌ | `rollback-audit-log` | DynamoDB 테이블 이름 |

## 💰 비용

### 예상 비용 (월 100회 롤백 기준)

| 서비스 | 사용량 | 단가 | 월 비용 |
|--------|--------|------|---------|
| Lambda | 100 invocations × 1초 | $0.0000002/request | < $0.01 |
| API Gateway | 100 requests | $1.00/M requests | < $0.01 |
| DynamoDB | 100 writes | $1.25/M writes | < $0.01 |
| CloudWatch Logs | ~10 MB | $0.50/GB | < $0.01 |

**총 예상 비용: < $0.05/월**

## 🔒 보안 고려사항

### 1. 인증 추가 (권장)

```python
# Lambda Authorizer 사용 또는
# Cognito User Pool 사용 또는
# API Key 사용

def verify_auth(event):
    auth_header = event.get('headers', {}).get('Authorization', '')
    # JWT 검증 로직
    return is_valid
```

### 2. Rate Limiting

API Gateway에서 설정:
```hcl
resource "aws_apigatewayv2_stage" "prod" {
  # ...

  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
  }
}
```

### 3. IP 화이트리스트 (선택)

```python
ALLOWED_IPS = ['1.2.3.4', '5.6.7.8']

def lambda_handler(event, context):
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp')
    if source_ip not in ALLOWED_IPS:
        return error_response(403, "Access denied")
```

## 🐛 트러블슈팅

### 문제: "GitHub token is invalid"

**해결**:
1. GitHub PAT이 만료되지 않았는지 확인
2. `workflow` 권한이 있는지 확인
3. Lambda 환경 변수에 올바르게 설정되었는지 확인

### 문제: "DynamoDB table not found"

**해결**:
1. DynamoDB 테이블이 생성되었는지 확인
2. Lambda 함수의 IAM 역할에 DynamoDB 권한이 있는지 확인
3. 환경 변수 `AUDIT_TABLE_NAME`이 올바른지 확인

### 문제: "Workflow dispatch failed"

**해결**:
1. 저장소 이름과 오너가 올바른지 확인
2. `rollback.yml` 워크플로우 파일이 `roll-back` 브랜치에 있는지 확인
3. GitHub Actions 로그 확인

## 📚 관련 문서

- [UI 컴포넌트 가이드](../../apps/ui-samples/README.md)
- [롤백 운영 가이드](../../ops/runbooks/ROLLBACK.md)
- [자동 롤백 워크플로우](../../.github/workflows/auto-rollback.yml)

## 🤝 기여

개선 사항이나 버그 리포트는 이슈로 등록해주세요!
