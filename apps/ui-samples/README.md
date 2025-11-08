# UI Rollback Button - 사용 가이드

UI에서 배포 롤백을 트리거할 수 있는 컴포넌트입니다.

## 🎯 기능

- ✅ 원클릭 롤백 (버튼 클릭 → 확인 다이얼로그 → 롤백 실행)
- ✅ 환경별 구분 (Dev/Prod)
- ✅ Production 안전 장치 (빨간색 경고, 명확한 확인 메시지)
- ✅ 실시간 진행 상황 표시
- ✅ GitHub Actions 모니터링 페이지 자동 오픈
- ✅ 감사 로그 (누가, 언제, 어떤 환경을 롤백했는지)

---

## 📦 포함된 컴포넌트

### 1. **React + Material-UI** (`RollbackButton.tsx`)

**의존성:**
```bash
npm install @mui/material @mui/icons-material @emotion/react @emotion/styled
```

**사용법:**
```tsx
import { RollbackButton } from './RollbackButton';

function DeploymentDashboard() {
  return (
    <RollbackButton
      environment="prod"
      currentImageTag="abc123d"
      userId="user@example.com"
      apiEndpoint="https://your-api-id.execute-api.ap-northeast-2.amazonaws.com/prod/rollback"
      onSuccess={(data) => {
        console.log('Rollback initiated:', data);
      }}
      onError={(error) => {
        console.error('Rollback failed:', error);
      }}
    />
  );
}
```

### 2. **Vue 3 + Vuetify** (`RollbackButton.vue`)

**의존성:**
```bash
npm install vuetify @mdi/font
```

**사용법:**
```vue
<template>
  <RollbackButton
    environment="prod"
    current-image-tag="abc123d"
    user-id="user@example.com"
    api-endpoint="https://your-api-id.execute-api.ap-northeast-2.amazonaws.com/prod/rollback"
    @success="handleSuccess"
    @error="handleError"
  />
</template>

<script setup>
import RollbackButton from './RollbackButton.vue';

const handleSuccess = (data) => {
  console.log('Rollback initiated:', data);
};

const handleError = (error) => {
  console.error('Rollback failed:', error);
};
</script>
```

---

## 🔧 백엔드 설정

### Lambda 함수 배포

#### 1. **Lambda 함수 생성**

```bash
cd lambda/rollback-trigger

# 의존성 설치
pip install -r requirements.txt -t .

# ZIP 패키지 생성
zip -r rollback-trigger.zip lambda_function.py requests/ boto3/
```

#### 2. **Lambda 환경 변수 설정**

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `GITHUB_TOKEN` | `ghp_xxxx...` | GitHub Personal Access Token (workflow 권한 필요) |
| `GITHUB_REPO_OWNER` | `Softbank-mango` | GitHub 조직/사용자명 |
| `GITHUB_REPO_NAME` | `deplight-infra` | 저장소 이름 |
| `AUDIT_TABLE_NAME` | `rollback-audit-log` | DynamoDB 테이블 이름 (선택사항) |

#### 3. **IAM 역할 권한**

Lambda 함수에 필요한 권한:
- DynamoDB: `PutItem`, `UpdateItem` (감사 로그용)
- 기본 Lambda 실행 권한

#### 4. **API Gateway 생성**

```bash
# REST API 생성
aws apigateway create-rest-api --name rollback-api

# POST /rollback 엔드포인트 생성
# Lambda 함수와 연결
# CORS 활성화
```

**또는 Terraform으로:**

```hcl
# 예시 (infrastructure/modules/rollback-api/main.tf)
resource "aws_lambda_function" "rollback_trigger" {
  filename      = "rollback-trigger.zip"
  function_name = "rollback-trigger"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"

  environment {
    variables = {
      GITHUB_TOKEN      = var.github_token
      GITHUB_REPO_OWNER = "Softbank-mango"
      GITHUB_REPO_NAME  = "deplight-infra"
      AUDIT_TABLE_NAME  = aws_dynamodb_table.audit_log.name
    }
  }
}

resource "aws_apigatewayv2_api" "rollback_api" {
  name          = "rollback-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://your-ui-domain.com"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.rollback_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.rollback_trigger.invoke_arn
}

resource "aws_dynamodb_table" "audit_log" {
  name         = "rollback-audit-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audit_id"

  attribute {
    name = "audit_id"
    type = "S"
  }
}
```

---

## 🔐 보안 고려사항

### 1. **인증 (Authentication)**

현재 구현은 기본적인 예시입니다. Production 환경에서는 다음을 추가하세요:

```typescript
// JWT 토큰 인증 예시
const response = await fetch(apiEndpoint, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`, // 추가
  },
  body: JSON.stringify({...})
});
```

Lambda에서:
```python
# API Gateway Authorizer 사용 또는
# Lambda 내부에서 토큰 검증
def lambda_handler(event, context):
    # Verify JWT token
    token = event['headers'].get('Authorization', '').replace('Bearer ', '')
    user_info = verify_jwt_token(token)

    if not user_info:
        return error_response(401, "Unauthorized")

    # ... rest of the code
```

### 2. **권한 제어 (Authorization)**

```python
# RBAC 예시
ALLOWED_ROLES = {
    'dev': ['developer', 'admin'],
    'prod': ['admin', 'ops-lead']  # Production은 더 제한적
}

def check_permission(user_role, environment):
    return user_role in ALLOWED_ROLES.get(environment, [])
```

### 3. **Rate Limiting**

```typescript
// 클라이언트 측
let lastRollbackTime = 0;
const COOLDOWN_MS = 60000; // 1분

const handleRollback = async () => {
  const now = Date.now();
  if (now - lastRollbackTime < COOLDOWN_MS) {
    alert('롤백은 1분에 한 번만 실행할 수 있습니다.');
    return;
  }
  lastRollbackTime = now;

  // ... rollback logic
};
```

API Gateway에서 Rate Limiting 설정

---

## 📊 모니터링

### 감사 로그 확인

```bash
# DynamoDB에서 최근 롤백 기록 조회
aws dynamodb scan \
  --table-name rollback-audit-log \
  --limit 10 \
  --query 'Items[*].[audit_id.S, timestamp.S, user_id.S, environment.S, status.S]' \
  --output table
```

### CloudWatch Logs

Lambda 로그 확인:
```bash
aws logs tail /aws/lambda/rollback-trigger --follow
```

---

## 🧪 테스트

### 로컬 테스트 (Lambda)

```python
# test_lambda.py
from lambda_function import lambda_handler

event = {
    'body': json.dumps({
        'environment': 'dev',
        'rollback_type': 'terraform',
        'user_id': 'test@example.com',
        'reason': 'Test rollback'
    })
}

result = lambda_handler(event, None)
print(result)
```

### UI 컴포넌트 테스트

```typescript
// Mock API for testing
const mockApiEndpoint = '/api/mock-rollback';

// Mock server (development)
app.post('/api/mock-rollback', (req, res) => {
  console.log('Mock rollback request:', req.body);

  setTimeout(() => {
    res.json({
      status: 'success',
      message: 'Mock rollback initiated',
      data: {
        audit_id: 'mock-123',
        workflow_run_id: '456789',
        environment: req.body.environment,
        rollback_type: req.body.rollback_type,
        image_tag: 'abc123d',
        estimated_duration: '3-5 minutes',
        monitor_url: 'https://github.com/...'
      }
    });
  }, 1000);
});
```

---

## 🎨 커스터마이징

### 스타일 변경 (React)

```tsx
<RollbackButton
  sx={{
    backgroundColor: 'custom.main',
    '&:hover': {
      backgroundColor: 'custom.dark',
    },
  }}
  // ... other props
/>
```

### 다이얼로그 메시지 변경

컴포넌트 소스에서 메시지 수정:
```typescript
const dialogMessages = {
  prod: {
    title: '🔴 Production 배포 롤백',
    warning: '⚠️ 이 작업은 실제 서비스에 영향을 줍니다.',
  },
  dev: {
    title: '🟡 Dev 배포 롤백',
    warning: '개발 환경을 롤백합니다.',
  },
};
```

---

## 💰 비용

### Lambda
- 요청당: $0.0000002 (100만 요청당 $0.20)
- 실행 시간: 약 1초 (메모리 128MB 기준)
- 월 예상 비용 (100회 롤백): **< $0.01**

### API Gateway
- HTTP API: 100만 요청당 $1.00
- 월 예상 비용 (100회 롤백): **< $0.01**

### DynamoDB
- On-demand: 쓰기 100만당 $1.25
- 월 예상 비용 (100회 롤백): **< $0.01**

**총 예상 비용: < $0.05/월**

---

## 📚 추가 자료

- [GitHub Actions workflow_dispatch 문서](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- [롤백 워크플로우 가이드](../../ops/runbooks/ROLLBACK.md)
- [자동 롤백 시스템](../../.github/workflows/auto-rollback.yml)

---

## 🤝 기여

개선 사항이나 버그가 있다면 이슈를 생성하거나 PR을 보내주세요!

## 📝 라이선스

MIT License
