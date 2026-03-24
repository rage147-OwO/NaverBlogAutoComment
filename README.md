# Naver Blog Auto Comment Service

네이버 블로그의 일기 포스트를 자동으로 읽고, Claude AI로 깊이 있는 위로 댓글을 생성해 달아주는 자동화 서비스입니다.

## 특징

- **자동화된 댓글 생성**: Claude Haiku를 활용한 저비용 AI 댓글 생성
- **철학적 깊이**: 단순한 위로가 아닌 심리학·철학적 관점의 통찰력 있는 댓글
- **GitHub Actions 배포**: 서버 없이 완전 자동화된 일일 실행
- **중복 방지**: 이미 댓글을 단 포스트는 자동으로 스킵
- **우아한 실패 처리**: API 크레딧 부족 시 고품질 목(mock) 댓글로 자동 대체

## 요구사항

- GitHub 계정
- Anthropic API 키 (https://console.anthropic.com)
- 네이버 블로그 계정

## 배포 가이드

### 1단계: GitHub 저장소 생성

1. GitHub에 로그인하고 새 저장소 생성:
   - 저장소명: `NaverBlogAutoComment` (또는 원하는 이름)
   - Public 또는 Private (선택사항)

2. 로컬 저장소를 GitHub에 push:
   ```bash
   git remote add origin https://github.com/{YOUR_USERNAME}/{YOUR_REPO_NAME}.git
   git branch -M main
   git push -u origin main
   ```

### 2단계: GitHub Secrets 설정

GitHub 저장소 페이지에서:

1. **Settings** → **Secrets and variables** → **Actions** 클릭
2. **New repository secret** 버튼으로 아래 3개 시크릿 추가:

| 시크릿 이름 | 값 | 설명 |
|-----------|-----|------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | [Anthropic Console](https://console.anthropic.com)에서 발급 |
| `NAVER_ID` | 네이버 로그인 아이디 | 예: `bbbaa1004` |
| `NAVER_PASSWORD` | 네이버 로그인 비밀번호 | 예: `password123!` |

> **보안 주의**: 이 정보는 GitHub Secrets에만 저장되며, 워크플로우 로그에는 절대 노출되지 않습니다.

### 3단계: GitHub Actions 활성화

1. 저장소의 **Actions** 탭 클릭
2. "I understand my workflows, go ahead and enable them" 클릭
3. 자동으로 활성화됨

### 4단계: 첫 실행 테스트

#### 자동 실행
- **일정**: 매일 오전 8시 (KST, UTC 23:00)
- 자동으로 최근 3개 포스트에 댓글 달음

#### 수동 실행
1. **Actions** 탭 → **네이버 블로그 자동 댓글** 워크플로우 선택
2. **Run workflow** → **Run workflow** 클릭
3. 실행 진행 상황을 실시간으로 확인

### 5단계: 실행 결과 확인

1. **Actions** 탭에서 최신 워크플로우 실행 선택
2. 각 단계의 로그 확인:
   - `네이버 블로그 자동 댓글 실행` 섹션에서 댓글 생성 내용 확인
   - 포스트 수, 새 댓글 수, 건너뜀 수 확인

## 로컬 테스트 (선택사항)

로컬에서 먼저 테스트하고 싶다면:

### 1. 환경 설정

```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium
```

### 2. .env 파일 생성

```bash
cp .env.example .env
```

`.env` 파일 수정:
```
ANTHROPIC_API_KEY=sk-ant-...
NAVER_ID=your_naver_id
NAVER_PASSWORD=your_password
```

### 3. 테스트 실행

```bash
# 테스트 모드: 댓글을 달지 않고 내용만 확인
uv run python main.py --dry-run --count 1

# 실제 댓글 달기 (최근 3개 포스트)
uv run python main.py --count 3

# 기록 초기화 후 재처리
uv run python main.py --reset --count 5
```

## CLI 옵션

```bash
uv run python main.py [OPTIONS]

옵션:
  --dry-run        테스트 모드: 댓글을 달지 않음
  --count N        처리할 포스트 수 (기본값: 5)
  --headless       브라우저 창 없이 실행
  --reset          기록 초기화 후 전체 재처리
```

## 댓글 예시

시스템은 포스트의 감정을 분석하고 깊이 있는 댓글을 생성합니다:

| 감정 | 댓글 예시 |
|------|---------|
| 힘들 | "당신의 글에서 느껴지는 것은 단순한 어려움이 아니라, 그 과정 속에서 자기 성찰을 멈추지 않는 성숙함입니다. 심리학에서 말하는 '포스트트라우마틱 그로스(역경을 통한 성장)'의 초기 단계를 보는 것 같습니다." |
| 외로 | "고독함이 때로는 가장 정직한 감정이라는 점을 당신의 글에서 느꼈습니다. 그것을 마주하고 표현하는 용기 자체가 이미 연결의 첫걸음이 되어 있습니다." |
| 희망 | "절망 속에서도 희망을 찾으려는 시도는, 단순한 긍정이 아니라 인간의 회복탄력성을 증명하는 것입니다. 당신의 성장 궤적이 의미 있습니다." |

## 비용

- **Claude Haiku**: 입력 $1/백만 토큰, 출력 $5/백만 토큰
- **예상 월 비용**: 약 $1-5 (일일 3개 포스트 기준)

## 문제 해결

### 1. "자동 댓글이 달리지 않음"
- **Actions** 탭에서 워크플로우 실행 로그 확인
- Secrets가 올바르게 설정되었는지 확인
- `.env.example`에 필요한 환경변수 목록 있음

### 2. "API 크레딧 부족"
- 시스템이 자동으로 고품질 목 댓글로 전환됨
- 댓글이 계속 달리며, 나중에 API 크레딧 복구 후 정상 작동

### 3. "네이버 로그인 실패"
- 비밀번호에 특수문자 포함 시 이스케이프 필요
- 2단계 인증 활성화되어 있으면 먼저 비활성화

### 4. "GitHub Actions에서 오류"
- 각 단계별 로그 상세 확인
- 로그에 재현 가능한 정보 캡처 후 issue 생성

## 구조

```
NaverBlogAutoComment/
├── .github/
│   └── workflows/
│       └── auto-comment.yml      # GitHub Actions 워크플로우
├── main.py                        # 메인 진입점
├── comment_generator.py          # Claude API 통합
├── naver_blog.py                 # Playwright 브라우저 자동화
├── pyproject.toml                # 프로젝트 설정 (UV)
└── README.md                      # 이 파일
```

## 기술 스택

- **Python 3.11**: 비동기 프로그래밍
- **Playwright**: 브라우저 자동화
- **Anthropic Claude API**: AI 댓글 생성
- **GitHub Actions**: 서버리스 자동화
- **UV**: 현대적인 Python 패키지 관리

## 라이선스

MIT

## 문의

문제가 발생하면 이 저장소에 Issue를 생성하세요.
