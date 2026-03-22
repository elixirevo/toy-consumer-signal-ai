# Vercel Deployment

이 레포는 `frontend`와 `backend`를 각각 별도의 Vercel 프로젝트로 배포하는 구조로 정리되어 있습니다.

## 권장 배포 구조

### 1. Frontend 프로젝트

- Vercel Project Root Directory: `frontend`
- 정적 파일 배포
- `frontend/api/[...path].mjs` same-origin 프록시 포함
- 설정 파일: `frontend/vercel.json`

프론트 환경변수:

- `BACKEND_API_BASE_URL`

배포 후 확인:

- 프론트 앱이 열리는지 확인
- `백엔드 API Base URL` 기본값이 `/api`인지 확인
- 한 번 입력하면 브라우저에 저장됨

### 2. Backend 프로젝트

- Vercel Project Root Directory: `backend`
- FastAPI 배포
- 엔트리포인트: `backend/app.py`
- 설정 파일: `backend/vercel.json`

백엔드 배포 전 환경변수:

- `OPENAI_API_KEY`

## Vercel에서 프로젝트 생성 방법

### Frontend

1. Vercel에서 `New Project`
2. 이 GitHub 레포 선택
3. Root Directory를 `frontend`로 설정
4. Deploy

### Backend

1. Vercel에서 `New Project`
2. 같은 GitHub 레포 선택
3. Root Directory를 `backend`로 설정
4. Environment Variables에 `OPENAI_API_KEY` 추가
5. Deploy

## CLI 배포

### 1. Vercel CLI 설치

```bash
npm i -g vercel
```

### 2. 프로젝트 링크

interactive로 링크할 수도 있고, 환경변수로 프로젝트명을 넘길 수도 있습니다.

```bash
./scripts/vercel_link.sh
```

또는:

```bash
FRONTEND_VERCEL_PROJECT=my-frontend \
BACKEND_VERCEL_PROJECT=my-backend \
VERCEL_SCOPE=my-team \
VERCEL_TOKEN=xxxx \
./scripts/vercel_link.sh
```

### 3. 배포

Preview 배포:

```bash
./scripts/vercel_deploy.sh
```

Production 배포:

```bash
./scripts/vercel_deploy.sh --prod
```

백엔드 환경변수를 CLI에서 같이 넘기고 싶으면:

```bash
OPENAI_API_KEY=sk-... ./scripts/vercel_deploy.sh --prod
```

프론트는 배포 스크립트가 backend 배포 URL을 읽어서 `BACKEND_API_BASE_URL`로 자동 주입합니다.
직접 지정하고 싶으면:

```bash
BACKEND_API_BASE_URL=https://your-backend.vercel.app ./scripts/vercel_deploy.sh --prod
```

### 스크립트 파일

- `scripts/vercel_link.sh`
- `scripts/vercel_deploy.sh`

## 참고 사항

- FastAPI는 Vercel 공식 문서 기준으로 `app.py`, `index.py`, `server.py`, `src/index.py` 등의 엔트리포인트에서 `app = FastAPI()`를 인식합니다. 이 레포는 `backend/app.py`에서 `main.app`을 export 하는 방식으로 맞췄습니다.
- `functions` 설정은 Vercel에서 보통 `api/**` 패턴에 적용되므로, 현재 backend는 FastAPI zero-config 배포 방식을 사용합니다.
- 배포된 frontend는 browser에서 backend 도메인을 직접 호출하지 않고, same-origin `/api/*` 경로로 요청합니다. 이 요청은 `frontend/api/[...path].mjs`가 `BACKEND_API_BASE_URL`로 프록시하므로 브라우저 CORS를 피할 수 있습니다.
- Vercel Python Runtime은 `pyproject.toml`과 `.python-version`을 프로젝트 루트 기준으로 읽습니다. backend 프로젝트는 Root Directory를 `backend`로 설정해야 현재 설정이 그대로 적용됩니다.
- Vercel 공식 문서에 따르면 FastAPI 앱은 단일 Vercel Function으로 배포되고 Fluid compute를 사용합니다.
- Python 함수 번들 크기 제한이 있으므로 `backend/.vercelignore`에서 `.venv`, `__pycache__`, `.env` 등을 제외하도록 설정했습니다.

## 공식 문서

- FastAPI on Vercel: <https://vercel.com/docs/frameworks/backend/fastapi>
- Python Runtime: <https://vercel.com/docs/functions/runtimes/python>
- Project Configuration: <https://vercel.com/docs/project-configuration/vercel-json>
