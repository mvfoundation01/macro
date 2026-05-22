# Deployment guide

## Auto-deploy on push (after this PR merges)

Every push to `main` triggers `.github/workflows/deploy.yml` which:
1. Runs pytest + ruff + bandit (gate)
2. Builds Docker image, pushes to GHCR
3. Pushes dashboard to Hugging Face Space at https://huggingface.co/spaces/mvfoundation01/macro-dashboard

## One-time setup (secrets)

Owner must configure these in GitHub repo -> Settings -> Secrets and variables -> Actions:

- `HF_TOKEN`: Hugging Face write token from https://huggingface.co/settings/tokens
  Required for HF Space push.

- `DISCORD_WEBHOOK_URL` (optional): Discord channel webhook for deploy notifications.

`GITHUB_TOKEN` is auto-provided by Actions runtime.

## Manual deployment fallback

If auto-deploy fails:

```bash
docker build -t ghcr.io/mvfoundation01/macro:latest .
docker push ghcr.io/mvfoundation01/macro:latest
# Then manually push to HF Space remote
```

## Status

- [x] Workflow file installed: `.github/workflows/deploy.yml`
- [ ] HF_TOKEN secret configured (owner action)
- [ ] First deploy verified (next push triggers)
