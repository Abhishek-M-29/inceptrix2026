# Codebase Documentation

This document provides a technical breakdown of the files in the `inceptrix2026` project, detailing their specific functionalities, inputs, and outputs.

## File Reference

### 1. `app/main.py`
**Functionality**: 
The entry point for the FastAPI application. It initializes the `FastAPI` app instance and includes the API routes.
- **Inputs**: None directly (server startup).
- **Outputs**: Run the HTTP server.

### 2. `app/api/routes.py`
**Functionality**: 
Defines the HTTP endpoints for the API. Handles request validation and response formatting.

#### Endpoint: `POST /scan`
- **Function**: `start_scan`
- **What it does**: Generates a UUID `engagement_id`, sets status to "Queued" in Redis, and pushes a task to the Celery queue.
- **Input (JSON Body)**:
  ```json
  { "target_url": "http://example.com" }
  ```
- **Output (JSON)**:
  ```json
  { "engagement_id": "uuid-string", "status": "Queued" }
  ```

#### Endpoint: `GET /status/{engagement_id}`
- **Function**: `get_status`
- **What it does**: Queries Redis for the current status of a specific job.
- **Input (Path Param)**: `engagement_id` (string)
- **Output (JSON)**:
  ```json
  { "engagement_id": "uuid-string", "status": "Queued|Running|Completed|Failed" }
  ```

#### Endpoint: `GET /report/{engagement_id}`
- **Function**: `get_report`
- **What it does**: Retrieves the final scan result from Redis. Only works if status is "Completed".
- **Input (Path Param)**: `engagement_id` (string)
- **Output (JSON)**: Arbitrary JSON object containing scan findings (dependent on worker output).

### 3. `app/schemas.py`
**Functionality**: 
Defines Pydantic models for data validation and serialization.

- **`ScanRequest`**:
  - Validates that `target_url` is a valid HTTP URL.
- **`ScanResponse`**:
  - Ensures responses strictly follow the `{ engagement_id, status }` format.

### 4. `app/worker/tasks.py`
**Functionality**: 
The core logic executed by the Celery worker.

#### Task: `run_scan_task`
- **Inputs**: `engagement_id` (str), `target_url` (str)
- **Logic**:
  1. Updates Redis status to "Running".
  2. Checks if Docker is available.
  3. **If Docker is available**: 
     - Pulls/Runs an `alpine` container.
     - Executes a command to simulate a tool outputting JSON.
     - Captures container logs (stdout).
  4. **If Docker is missing**: 
     - Waits 5 seconds (Mock Mode).
     - Generates static dummy data.
  5. Saves the JSON result to Redis key `job:{id}:report`.
  6. Updates Redis status to "Completed".

### 5. `app/worker/celery_app.py`
**Functionality**: 
Configures the Celery application instance.
- **Settings**:
  - Broker: Redis (default `redis://localhost:6379/0`)
  - Backend: Redis
  - Serialization: JSON

### 6. `app/core/redis.py`
**Functionality**: 
Singleton Redis client initialization.
- **Exports**: `redis_client` object used by both API and Worker to ensure consistent connection settings.

### 7. `docker-compose.yml`
**Functionality**: 
Infrastructure orchestration using Docker.
- **Services**:
  - `redis`: Image `redis:alpine`. Maps port `6379`.

### 8. `requirements.txt`
**Functionality**: 
List of Python package dependencies.
- `fastapi`, `uvicorn`: Web server.
- `redis`: Redis client.
- `celery`: Task queue.
- `docker`: Docker engine API client.
- `pydantic`: Data validation.
- `pyngrok`: A Python wrapper for ngrok.

## Setup & Usage with ngrok

To expose your local server to the internet using ngrok:

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set your ngrok authtoken**:
    Get your authtoken from the [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).
    ```bash
    python setup_ngrok.py <YOUR_AUTHTOKEN>
    ```

3.  **Run the application**:
    ```bash
    uvicorn app.main:app --reload
    ```
    The application will automatically start an ngrok tunnel and print the public URL in the console.
