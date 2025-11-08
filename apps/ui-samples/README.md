# UI Rollback Button - 사용 가이드

GitHub Actions 롤백 워크플로우를 직접 호출하는 UI 컴포넌트입니다. 배포 대시보드나 운영 포털에 손쉽게 붙여서 운영자가 버튼 한 번으로 롤백을 요청할 수 있습니다.

## 🆕 변경 사항 요약 (한국어)

- 이제 UI가 AWS Lambda를 거치지 않고 **GitHub Actions `workflow_dispatch` API를 직접 호출**합니다.
- Vue 기반 샘플 컴포넌트와 Lambda 예제 코드는 정리되었고, React 버전만 유지됩니다.
- GitHub 토큰 주입과 보안 모범 사례, 모니터링 링크 등은 README에 정리되어 있으니 UI 통합 시 참고하세요.

## 🎯 기능

- ✅ 원클릭 롤백 (버튼 클릭 → 확인 다이얼로그 → GitHub Actions API 호출)
- ✅ 환경별 구분 (Dev/Prod)
- ✅ Production 안전 장치 (빨간색 경고, 명확한 확인 메시지)
- ✅ 실시간 진행 상황 페이지 바로가기 (워크플로우 모니터링 URL)
- ✅ 감사 로그 연동용 콜백 제공 (`onSuccess`, `onError`)

---

## 📦 포함된 컴포넌트

### **React + Material-UI** (`RollbackButton.tsx`)

**의존성:**
```bash
npm install @mui/material @mui/icons-material @emotion/react @emotion/styled
```

**필수 props:**
- `environment`: `dev` 또는 `prod`
- `userId`: 롤백을 요청한 사용자를 나타내는 식별자
- `githubToken`: GitHub Actions API를 호출할 수 있는 [Fine-grained Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) (workflow 권한 필요)
- `repoOwner` / `repoName`: 롤백 워크플로우가 존재하는 저장소 정보
- `workflowFileName`: 워크플로우 파일 이름 (예: `rollback.yml`)

**선택 props:**
- `workflowRef`: 워크플로우가 위치한 브랜치 또는 태그 (기본값: `roll-back`)

**사용법:**
```tsx
import { RollbackButton } from './RollbackButton';

function DeploymentDashboard() {
  return (
    <RollbackButton
      environment="prod"
      currentImageTag="abc123d"
      userId="user@example.com"
      githubToken={process.env.REACT_APP_GITHUB_TOKEN!}
      repoOwner="Softbank-mango"
      repoName="deplight-infra"
      workflowFileName="rollback.yml"
      // workflowRef prop을 생략하면 기본값으로 roll-back 브랜치를 사용합니다.
      onSuccess={(result) => {
        console.log('Rollback dispatched:', result);
      }}
      onError={(error) => {
        console.error('Rollback failed:', error);
      }}
    />
  );
}
```

> ⚠️ **보안 주의:** 프런트엔드 번들에 GitHub 토큰을 직접 포함하면 안 됩니다. [BFF(Backend-for-Frontend)](https://microservices.io/patterns/apigateway.html)나 사내 API를 두어 토큰을 안전하게 주입하세요.

---

## 🔗 GitHub Actions API 호출 흐름

`RollbackButton` 컴포넌트는 아래와 같은 흐름으로 GitHub Actions `workflow_dispatch` 이벤트를 호출합니다.

```tsx
const handleRollback = async () => {
  const endpoint = `https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowFileName}/dispatches`;

  const inputs: Record<string, string> = {
    environment,
    reason: `Manual rollback via UI by ${userId}`,
    triggered_by: userId,
  };

  if (currentImageTag) {
    inputs.image_tag = currentImageTag;
  }

  const dispatchRef = workflowRef ?? 'roll-back';

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${githubToken}`,
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({
      ref: dispatchRef,
      inputs,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
};
```

- 호출이 성공하면 HTTP 204를 반환하며, GitHub Actions 워크플로우가 큐에 등록됩니다.
- 컴포넌트는 성공 시 자동으로 워크플로우 모니터링 페이지 (`https://github.com/<owner>/<repo>/actions/workflows/<file>`)를 새 탭으로 엽니다.

---

## 🧪 테스트

1. **Mock 토큰/엔드포인트로 개발 환경 테스트**
   - [Mock Service Worker](https://mswjs.io/) 또는 간단한 프록시 서버를 사용해 GitHub API 호출을 가로채고 응답을 시뮬레이션합니다.
2. **GitHub Actions 샌드박스 저장소 테스트**
   - 별도의 테스트 저장소와 PAT를 준비하여 실제 `workflow_dispatch` 동작을 검증합니다.

---

## 🚀 roll-back 브랜치에 변경사항 반영하기

UI 변경 사항을 실제 롤백 워크플로우에서 활용하려면 GitHub의 `roll-back` 브랜치에 커밋을 올려야 합니다. 기본적으로 `RollbackButton`은 `roll-back` 브랜치를 타깃으로 `workflow_dispatch` 이벤트를 호출합니다.

```bash
git checkout roll-back
# 필요한 수정 적용
git add apps/ui-samples/RollbackButton.tsx apps/ui-samples/README.md
git commit -m "chore: sync rollback ui"
git push origin roll-back
```

> ℹ️ 다른 브랜치나 태그로 워크플로우를 실행하고 싶다면 `workflowRef` prop으로 명시하면 됩니다. 미지정 시 기본값인 `roll-back`이 사용됩니다.

---

## 🎨 커스터마이징

### 버튼 스타일 변경
```tsx
<RollbackButton
  sx={{
    backgroundColor: 'custom.main',
    '&:hover': {
      backgroundColor: 'custom.dark',
    },
  }}
  {...props}
/>
```

### 다이얼로그 메시지 변경
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

## 📚 추가 자료

- [GitHub Actions workflow_dispatch 문서](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch)
- [롤백 워크플로우 가이드](../../ops/runbooks/ROLLBACK.md)
- [자동 롤백 시스템](../../.github/workflows/auto-rollback.yml)

---

## 🤝 기여

개선 사항이나 버그가 있다면 이슈를 생성하거나 PR을 보내주세요!

## 📝 라이선스

MIT License
