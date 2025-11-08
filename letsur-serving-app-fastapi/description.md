# 육아크루 콘텐츠 필터링 시스템

- **Purpose:**
  육아크루 커뮤니티 내 게시글, 닉네임 등의 콘텐츠를 분석하여 부적절한 내용을 탐지하는 API입니다.
  안전한 커뮤니티 환경을 조성하기 위해 게시물의 부적절성 점수를 평가하고 필터링 여부를 판단합니다.

- **Request & Response:**
    - **Input:** 사용자가 작성한 게시글 또는 댓글(`text`)을 입력으로 받습니다.
    - **Output:** 부적절성 점수(`score`), 필터링 필요 여부(`filter`), 판단 근거(`rationale`)를 반환합니다.
- **Supported Features:**
    - 게시글, 댓글, 닉네임 등 다양한 콘텐츠의 부적절성 탐지
    - 머신러닝 기반 점수(`score`) 평가를 통한 필터링 여부 판단
    - 필터링된 콘텐츠에 대한 상세한 판단 근거(`rationale`) 제공
    - 비동기 요청 처리(`async`)를 지원하여 빠른 응답 제공
    - 입력 데이터 검증 및 오류 응답(`ValidationError`) 처리 기능 포함

- **Key Components:**
    - **ModelInput:** 분석 대상 텍스트(`text`)를 입력합니다.
    - **ModelOutput:** 부적절성 점수(`score`), 필터링 여부(`filter`), 판단 근거(`rationale`)를 포함한 JSON 객체를 반환합니다.
    - **API Endpoint:** `POST /invocations/async` – 입력된 텍스트를 분석하여 부적절성 여부를 평가합니다.
    - **ValidationError:** 유효하지 않은 요청에 대해 검증 오류 응답을 반환합니다.
