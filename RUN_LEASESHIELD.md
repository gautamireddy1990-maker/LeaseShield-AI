# Run LeaseShield AI on macOS

This guide gets the project from GitHub running locally. You will need an OpenAI API key to run lease audits. Stripe credentials are optional unless you want to test checkout.

## 1. Install prerequisites

If Homebrew is installed, run:

```bash
brew install python@3.11 node@20 tesseract poppler
```

If `brew` is not installed, install it from [brew.sh](https://brew.sh/), then run the command above.

## 2. Download the project

Open Terminal and run:

```bash
git clone https://github.com/gautamireddy1990-maker/LeaseShield-AI.git
cd LeaseShield-AI
cp .env.example .env
```

Open `.env` in a text editor and replace `OPENAI_API_KEY=replace-me` with your own key. Keep `.env` private; it is excluded from Git. For Stripe checkout, also fill in the Stripe test secret, webhook secret, and the two test Price IDs.

## 3. Start the backend

In Terminal, from the project root (`LeaseShield-AI`):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
set -a
source .env
set +a
uvicorn backend.main:app --reload --port 8000
```

Keep this terminal open. The API runs at `http://localhost:8000`; its health check is `http://localhost:8000/health`.

## 4. Start the frontend

Open a second Terminal window. From the project root, run:

```bash
cd frontend
npm install
npm run dev
```

Keep this terminal open too. Open [http://localhost:3000](http://localhost:3000) in your browser, choose **Start an audit**, and upload a PDF lease.

## 5. Optional: test Stripe Checkout

Use Stripe test-mode keys and Price IDs in `.env`. Install and sign in to the Stripe CLI, then start webhook forwarding in another terminal:

```bash
stripe listen --forward-to localhost:8000/api/payments/webhook
```

Copy the `whsec_...` value printed by the CLI into `STRIPE_WEBHOOK_SECRET` in `.env`, then restart the backend so it loads the updated value. Use Stripe's test card `4242 4242 4242 4242`, any future expiration date, and any three-digit CVC. Never use a real card for this test.

## Troubleshooting

- **`python3.11: command not found`:** confirm Homebrew installed Python 3.11 with `brew list python@3.11` and reopen Terminal.
- **`npm: command not found`:** install Node.js with `brew install node@20`, then reopen Terminal.
- **OCR errors:** install Tesseract and Poppler with `brew install tesseract poppler`.
- **Audit errors:** confirm the backend terminal has loaded a valid `OPENAI_API_KEY` from `.env` and is still running.
- **Checkout errors:** check Stripe test keys, Price IDs, and the CLI webhook secret. Restart the backend after changing `.env`.

Reports currently live in backend memory, so restarting the API clears them. This project is an MVP; review its production data-storage and security design before using it with confidential leases.
