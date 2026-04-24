```markdown
# fleshrag Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill documents the development patterns and workflows used in the `fleshrag` repository, a Python-based project with a multi-service architecture. The codebase spans backend services, Docker configurations, and frontend components, supporting complex feature rollouts and infrastructure changes. This guide covers coding conventions, workflow steps, testing patterns, and common developer commands.

## Coding Conventions

### File Naming
- **Convention:** camelCase
- **Example:**  
  ```
  myModule.py
  indexerService.py
  ```

### Import Style
- **Convention:** Relative imports within Python modules.
- **Example:**
  ```python
  from .utils import fetchData
  from ..db import models
  ```

### Export Style
- **Convention:** Default exports (Python modules expose their contents by default).
- **Example:**
  ```python
  # In myModule.py
  def my_function():
      pass
  # No explicit export needed; all top-level functions/classes are available.
  ```

## Workflows

### Multi-Service Feature or Integration Update
**Trigger:** When rolling out a major feature or infrastructure change that affects backend, frontend, Docker, and tests simultaneously (e.g., enabling CUDA, migrating APIs, or adding a new service).  
**Command:** `/multi-service-update`

**Step-by-step Instructions:**

1. **Update backend service code**
    - Modify or add files in `backend/app/api/*.py`, `backend/app/indexer/*.py`, `backend/app/db/*.py`, or `backend/app/config.py`.
    - Example:
      ```python
      # backend/app/api/newFeature.py
      from ..db import models

      def new_feature():
          # implementation
          pass
      ```

2. **Update or add Dockerfiles and docker-compose.yml**
    - Edit `backend/Dockerfile`, `embed-service/Dockerfile`, or `docker-compose.yml` as needed.
    - Example:
      ```dockerfile
      # backend/Dockerfile
      FROM python:3.10
      COPY . /app
      WORKDIR /app
      RUN pip install -r requirements.txt
      ```

3. **Update environment files**
    - Edit `.env` and `.env.example` to add or modify environment variables required for the new feature.

4. **Update or add frontend components**
    - Modify or add files in `frontend/src/components/*.tsx`.
    - Example:
      ```tsx
      // frontend/src/components/NewFeature.tsx
      export default function NewFeature() {
        return <div>New Feature Enabled!</div>;
      }
      ```

5. **Add or update tests**
    - Add or modify test files, e.g., `backend/tests/*.py`.
    - Example:
      ```python
      # backend/tests/test_new_feature.py
      def test_new_feature():
          assert new_feature() == expected_result
      ```

6. **Update documentation if relevant**
    - Edit or add markdown files such as `TZ_Multimodal_RAG*.md` to document the new feature or changes.

7. **Update .gitignore**
    - Add new directories or files to `.gitignore` as necessary to prevent committing build artifacts or sensitive files.

## Testing Patterns

- **Framework:** Unknown (not explicitly detected).
- **File Pattern:** `*.test.ts` (suggests some frontend or TypeScript-based tests).
- **Python Tests:** Located in `backend/tests/*.py`.
- **Example:**
  ```python
  # backend/tests/test_api.py
  def test_api_returns_200():
      response = client.get("/api/endpoint")
      assert response.status_code == 200
  ```

## Commands

| Command                | Purpose                                                                 |
|------------------------|-------------------------------------------------------------------------|
| /multi-service-update  | Start a workflow for major feature/integration updates across services.  |

```
