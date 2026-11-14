# LeaseShield AI

Commercial lease risk review with page-cited findings, tenant counter-clauses, and downloadable reports. AI output is informational and is not legal advice.

## Local setup

Requirements: Python 3.11+, Node.js 20+, Tesseract OCR, and Poppler utilities. Install backend dependencies with `pip install -r backend/requirements.txt`; install frontend dependencies with `cd frontend && npm install`. Copy `.env.example` to `.env`, then set the OpenAI key, Stripe test keys and configured Stripe Price IDs. Start the API from the repository root with `uvicorn backend.main:app --reload --port 8000`. Start Next.js in another terminal with `cd frontend && npm run dev`. Visit `http://localhost:3000`.

Set `NEXT_PUBLIC_API_URL` to the browser-reachable API URL, `FRONTEND_URL` to the app origin, and `LLM_BASE_URL` if using a compatible non-OpenAI endpoint. Stripe checkout requires Price IDs for the $49 one-time and $99/month recurring products.

## Stripe webhooks

Install and authenticate the Stripe CLI, then run `stripe listen --forward-to localhost:8000/api/payments/webhook`. Copy the CLI-provided `whsec_...` value to `STRIPE_WEBHOOK_SECRET`. Use Stripe test mode and test cards; the webhook unlocks a report only after a verified `checkout.session.completed` event. In production, register `/api/payments/webhook` in Stripe and use that endpoint's signing secret.

## Docker Compose

Copy `.env.example` to `.env`, populate the values, then run `docker compose up --build`. The frontend is at port 3000 and API at port 8000. The named `leaseshield_tmp` volume stores only temporary uploads; cleanup removes files older than 24 hours. Reports currently live in process memory and are lost when the backend restarts.

## Deployment

Build and deploy the backend image from the repository root using `backend/Dockerfile`; deploy the frontend from `frontend/Dockerfile`. Configure the environment variables in the hosting platform, expose HTTPS origins, set `CORS_ORIGINS`, `FRONTEND_URL`, and `NEXT_PUBLIC_API_URL` to the public app/API URLs, and configure Stripe webhook delivery. Use persistent storage only for the dedicated temporary upload directory. For production multi-instance deployments, replace in-memory report storage with a database and coordinate webhook access to it; configure retention and access controls for report data.
