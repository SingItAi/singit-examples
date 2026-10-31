# Contributing to singit-examples

Thanks for taking a look. New examples, fixes and documentation are welcome.

## Adding an example

- One folder per framework, with its own `package.json`, lockfile, README and tests.
- It must run offline in `npm test` (use local mocks), and its default mode must need no key and make
  no payment.
- Paid mode must stay off unless the user sets explicit variables, including per-call and per-day
  limits.
- Add the folder to the matrix in `.github/workflows/ci.yml` and to the table in `README.md`.

## Set up

Node.js 20 or newer.

```bash
cd langchain            # or vercel-ai-sdk
npm ci
npm test
```

Tests must never send a real payment.

## Pull requests

- Branch from `main` and keep each pull request to one change.
- Describe what changed, why, and how you checked it. Say what you did **not** check.
- Never put a real private key, API key or wallet address in a file, a test or a pull request.
- Security problems: do not open a public issue. See [SECURITY.md](SECURITY.md).
- Do not rewrite history on a branch someone has already reviewed.
