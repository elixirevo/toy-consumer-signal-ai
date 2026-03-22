# Vercel Deployment

이 레포는 `frontend`와 `backend`를 각각 별도의 Vercel 프로젝트로 배포하는 구조로 정리되어 있습니다.

## 권장 배포 구조

### 1. Frontend 프로젝트

- Vercel Project Root Directory: `frontend`
- 정적 파일 배포
- 설정 파일: `frontend/vercel.json`

배포 후 확인:

- 프론트 앱이 열리는지 확인
- `백엔드 API Base URL` 입력란에 backend 배포 URL 입력
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

## 참고 사항

- FastAPI는 Vercel 공식 문서 기준으로 `app.py`, `index.py`, `server.py`, `src/index.py` 등의 엔트리포인트에서 `app = FastAPI()`를 인식합니다. 이 레포는 `backend/app.py`에서 `main.app`을 export 하는 방식으로 맞췄습니다.
- Vercel Python Runtime은 `pyproject.toml`과 `.python-version`을 프로젝트 루트 기준으로 읽습니다. backend 프로젝트는 Root Directory를 `backend`로 설정해야 현재 설정이 그대로 적용됩니다.
- Vercel 공식 문서에 따르면 FastAPI 앱은 단일 Vercel Function으로 배포되고 Fluid compute를 사용합니다.
- Python 함수 번들 크기 제한이 있으므로 `backend/vercel.json`에서 `.venv`, `__pycache__`, `.env` 등을 제외하도록 설정했습니다.

## 공식 문서

- FastAPI on Vercel: https://vercel.com/docs/frameworks/backend/fastapi
- Python Runtime: https://vercel.com/docs/functions/runtimes/python
- Project Configuration: https://vercel.com/docs/project-configuration/vercel-json
