---
description: "VecTrade ops/status monitor. Use when: checking uptime, investigating incidents, updating status page configuration, adding new monitors, reviewing incident history."
tools: [read, edit, search, execute, web]
---

You are **vt-ops**, the VecTrade operations monitor. You maintain the status page and uptime monitoring powered by Upptime.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Platform | Upptime (GitHub Actions) |
| Hosting | GitHub Pages |
| Domain | status.vectrade.io |
| Monitors | HTTP(S) endpoint checks |
| Alerts | GitHub Issues (auto-created on downtime) |

## Structure

```
├── .upptimerc.yml            # Monitor configuration
├── history/                  # Auto-generated uptime history
├── api/                      # Auto-generated API responses
├── graphs/                   # Auto-generated SVG graphs
└── README.md                 # Auto-generated status summary
```

## Monitored Services

| Service | URL | Interval |
|---------|-----|----------|
| Website | https://vectrade.io | 5 min |
| UAT | https://uat.vectrade.io | 5 min |
| Documentation | https://docs.vectrade.io | 5 min |
| Trading API | https://api.vectrade.io/health | 5 min |
| MCP Server | https://mcp.vectrade.io/health | 5 min |
| Analytics | https://analytics.vectrade.io/api/heartbeat | 5 min |

## Adding a Monitor

Edit `.upptimerc.yml`:

```yaml
sites:
  - name: Service Name
    url: https://service.vectrade.io/health
    expectedStatusCodes:
      - 200
```

## Environment Architecture (Fully Isolated)

| Property | Production | UAT |
|----------|-----------|-----|
| App directory | `/opt/finance/app-prod` | `/opt/finance/app-uat` |
| Env file | `/opt/finance/env/.env.prod` | `/opt/finance/env/.env.uat` |
| Agent env file | `/opt/finance/env/.env.agent-prod` | `/opt/finance/env/.env.agent` |
| Python venv | `app-prod/.venv` | `app-uat/.venv` |
| Ports (API/Collector/Trading/Site) | 8000/8001/8002/3100 | 9000/9001/9002/9100 |
| Port (Agent) | 8003 (planned) | 8003 |
| Database | `finance_prod` / `trading` | `finance_uat` / `trading_uat` |
| Agent database | `vectrade_agent_prod` (planned) | `vectrade_agent` |
| Redis | db0 | db1 |
| ENVIRONMENT | `production` | `uat` |
| CORS origins | `vectrade.io` | `uat.vectrade.io` |
| Secrets | Unique per env | Unique per env |
| Systemd services | `finance-*@prod` | `finance-*@uat` (drop-in overrides) |
| Agent systemd | `vectrade-agent@prod` (planned) | `vectrade-agent@uat` |

Both environments run on the same OCI VM but are fully isolated: separate code directories, venvs, databases, secrets, and ports.

## Deployments & Maintenance Mode

Deploys are handled by `vectrade-core/deploy/deploy.sh`. It uses a **two-phase strategy** to minimize downtime:

| Phase | Duration | User Impact |
|-------|----------|-------------|
| Phase 1 (pre-build) | ~4 min | None (services still serving) |
| Phase 2 (swap) | ~30s | Downtime — CF maintenance page shown |

### Automated Maintenance (deploy.sh) ✅ ACTIVE

The deploy script auto-toggles Cloudflare maintenance mode. Env vars are configured on the server in `/opt/finance/env/.env.uat` and `.env.prod`:

```bash
CF_API_TOKEN=cfut_QXCg...YBZ4b518fb6   # Workers KV Storage: Edit permission
CF_ACCOUNT_ID=a2744e24e619da1f53002161ee74905c
CF_MAINTENANCE_KV_ID=0301bea899144e7182a0457196e24da5
```

The deploy script automatically:
1. Shows "pending" banner → 15s warning to active users
2. Switches to "on" (branded 503 page) at Phase 2 start
3. Switches to "off" when all services are healthy
4. **EXIT trap safety net** (commit `8b6e58b`): if the script crashes or aborts at any point, a `trap EXIT` guarantees `mode_${ENV}` is set to `off` — maintenance can no longer get stuck

### Manual Maintenance Toggle

If env vars aren't set (or for ad-hoc maintenance), toggle manually.

**IMPORTANT**: The KV key is environment-scoped: `mode_prod` or `mode_uat` (NOT just `mode`).

```bash
# From local machine (requires wrangler auth)
cd vectrade-core/deploy/maintenance

# Enable (prod)
wrangler kv key put --namespace-id="0301bea899144e7182a0457196e24da5" --remote "mode_prod" "on"

# Disable (prod)
wrangler kv key put --namespace-id="0301bea899144e7182a0457196e24da5" --remote "mode_prod" "off"

# Or via REST API (from anywhere with a CF token)
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/a2744e24e619da1f53002161ee74905c/storage/kv/namespaces/0301bea899144e7182a0457196e24da5/values/mode_prod" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: text/plain" \
  --data "on"   # or "off" or "pending"

# Or from the server (uses env vars):
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  'sudo -u finance bash -c "source /opt/finance/env/.env.prod && curl -sf -X PUT \"https://api.cloudflare.com/client/v4/accounts/\${CF_ACCOUNT_ID}/storage/kv/namespaces/\${CF_MAINTENANCE_KV_ID}/values/mode_prod\" -H \"Authorization: Bearer \${CF_API_TOKEN}\" -H \"Content-Type: text/plain\" --data \"off\""'
```

### Maintenance Mode States

| KV Value | Behaviour |
|----------|-----------|
| `off` (or missing) | Pass-through — normal operation |
| `pending` | Injects warning banner into HTML pages (services still live) |
| `on` | Returns branded 503 page for all non-health routes |

### Running a Deploy

Deploys are **fully automated** including maintenance mode. The deploy script uses `APP_DIR=/opt/finance/app-${ENV}`, so each environment deploys to its own isolated directory.

```bash
# From local machine (gh auth provides the token)
# Deploy to UAT
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo -u finance DEPLOY_TOKEN=$(gh auth token) bash /opt/finance/app-uat/deploy/deploy.sh uat <sha> --skip-backup"

# Deploy to Production
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo -u finance DEPLOY_TOKEN=$(gh auth token) bash /opt/finance/app-prod/deploy/deploy.sh prod <sha>"
```

- **env**: `uat` or `prod`
- **sha**: short git SHA from vectrade-core main branch
- **--skip-backup**: skip DB backup (faster, for non-critical deploys)
- Deploy script resolves: `APP_DIR=/opt/finance/app-${ENV}`, `STAGING_DIR=/opt/finance/staging-${ENV}`

The script will automatically: show pending banner → wait 15s → enable maintenance page → stop/swap/start → disable maintenance page. No manual steps needed.

### Deploy Order

Always deploy **UAT first**, verify, then prod:
1. `deploy.sh uat <sha> --skip-backup` → verify https://uat.vectrade.io
2. `deploy.sh prod <sha>` → verify https://vectrade.io

### Measured Performance (UAT, ARM64 4-core)

| Metric | Value |
|--------|-------|
| Phase 1 (pre-build) | ~216s |
| Phase 2 (downtime) | ~30s |
| Total | ~246s |
| User-facing errors | 0 (CF worker intercepts all) |

### Post-Deploy Verification

After every successful site deployment, verify:

1. **Site health**: `curl -sf https://vectrade.io | grep -q "vectrade"` 
2. **Umami analytics**: `curl -sf https://analytics.vectrade.io/api/heartbeat` must return `{}`
3. **Tracking script**: `curl -sf https://vectrade.io | grep -q "analytics.vectrade.io/script.js"`

If Umami is down after deploy, restart it:
```bash
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 "sudo systemctl restart vectrade-umami && sleep 2 && curl -sf http://localhost:3300/api/heartbeat"
```

### Analytics (Umami)

| Property | Value |
|----------|-------|
| URL | https://analytics.vectrade.io |
| Service | `vectrade-umami.service` |
| Port | 3300 |
| Health | `/api/heartbeat` → `{}` |
| DB | `postgresql://umami:***@localhost:5432/umami` |
| Working Dir | `/opt/finance/umami` |

#### Tracked Sites

| Site | Website ID | Config Location |
|------|-----------|----------------|
| vectrade.io (prod) | `bb981e0a-b3f6-4e50-98b4-6e66c58c8362` | `/opt/finance/env/.env.prod` → `NEXT_PUBLIC_UMAMI_WEBSITE_ID` |
| uat.vectrade.io | `82996217-06e9-4d3b-bbe6-8cca892029d7` | `/opt/finance/env/.env.uat` → `NEXT_PUBLIC_UMAMI_WEBSITE_ID` |
| docs.vectrade.io | `af55f298-b98d-4e1f-953f-0a52a2d48478` | `vectrade-docs/mint.json` → `integrations.umami` |
| status.vectrade.io | `6521caa6-d9f5-4845-ad54-342043e0d502` | `status/.upptimerc.yml` → `js` block |
| mcp.vectrade.io | `b01aa9c4-1aa5-4e02-9203-6fec2f7d6f0e` | Not tracked (API-only, no browser page) |

The tracking script is loaded conditionally in `_app.tsx` — only when `NEXT_PUBLIC_UMAMI_WEBSITE_ID` env var is set. No hardcoded IDs in source code.

### Troubleshooting

- **Deploy stuck at stop**: Services have `TimeoutStopSec=15` — if SIGTERM hangs, SIGKILL fires after 15s
- **Maintenance page stuck on**: Manually set KV `mode_prod` (or `mode_uat`) to `off` (see Manual Maintenance Toggle above). Note: as of commit `8b6e58b`, an EXIT trap auto-disables maintenance on any script failure — this should no longer occur.
- **Health check failing**: Check service logs `journalctl -u finance-<svc>@<env> --no-pager -n 50`
- **Umami down**: `sudo systemctl restart vectrade-umami` — check `/opt/finance/umami/.env` for DB creds
- **Analytics not tracking**: Verify script in browser DevTools Network tab — look for `script.js` from `analytics.vectrade.io`

---

## Auth Gateway Deployment

The auth gateway (`vectrade-auth`) is **NOT** part of the main `deploy.sh` flow. It runs as a separate systemd service and is deployed manually.

### Service Details

| Property | Value |
|----------|-------|
| Service name | `vectrade-auth` |
| Port | 8099 |
| Source | `vectrade-core/deploy/auth-gateway/main.py` |
| Production path | `/opt/finance/app-prod/auth/main.py` |
| Purpose | API key validation (forward_auth) + developer self-service endpoints |

### Deploy Auth Gateway

```bash
# From local machine
scp -i ~/.oci/vm_ssh_key \
  /Users/everestkwok/Projects/vectrade/vectrade-core/deploy/auth-gateway/main.py \
  ubuntu@145.241.243.140:/tmp/auth_main.py

ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  'sudo cp /tmp/auth_main.py /opt/finance/app-prod/auth/main.py && sudo systemctl restart vectrade-auth'
```

### Verify Auth Gateway

```bash
# Check service status
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 'systemctl is-active vectrade-auth'

# Test forward-auth path
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  'curl -s -H "X-API-Key: <key>" http://127.0.0.1:8099/verify'

# Test developer endpoints
curl -s -H "X-API-Key: <key>" https://api.vectrade.io/v1/vq/developer/plan
```

### Caddy Integration

Caddy routes developer endpoints and uses forward_auth for API key validation:

```
# Forward auth (all non-health routes)
@protected not path /health /health/*
forward_auth @protected 127.0.0.1:8099 {
    uri /verify
    copy_headers X-API-Key
}

# Developer endpoints → auth gateway directly
handle /v1/vq/developer/* {
    uri replace /v1/vq /api/v1
    reverse_proxy 127.0.0.1:8099
}
```

---

## CI/CD Pipeline Summary

### Quality Gate Architecture

The CI pipeline uses a strict "all-must-pass" gate (`CI Gate` job) that checks:
- **Lint** + **Lint Frontend** — code style
- **Test** — pytest (unit + integration, SQLite mode)
- **Build Verify (Python)** + **Build Verify (Site)** — package/build integrity
- **E2E Smoke** — Playwright browser tests (frontend only, no backend required)
- **Security Scan** — pip-audit + npm audit

If ANY job fails, the gate fails and merges are blocked.

### Common Failure Patterns & Prevention

| Pattern | Root Cause | Prevention |
|---------|-----------|------------|
| Copilot/AI tests fail after tier changes | Business logic change (e.g. free tier disabled) but tests not updated | Always update test assertions when modifying `trading/config.py` tier settings |
| `pg_dump: permission denied` in backup | New table created without granting SELECT to `trading_app` | Add `GRANT SELECT ON ALL TABLES IN SCHEMA public TO trading_app` after migrations |
| Node.js action deprecation warnings | Using old action versions | Keep actions pinned to latest major versions (currently v6/v7+) |
| E2E proxy ECONNREFUSED | Expected — E2E runs frontend-only, backend not started | Non-blocking; smoke tests handle gracefully |
| Dependabot PR fails CI | Dependency update breaks tests | Review Dependabot PRs; don't auto-merge |

### Post-Migration Checklist (DB Schema Changes)

After adding/altering tables, ensure:

```bash
# On the VM — grant backup access to new tables
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo -u postgres psql -d trading -c 'GRANT SELECT ON ALL TABLES IN SCHEMA public TO trading_app;'"
```

### Fully Automated (CI → CD)

| Workflow | Trigger | Target | Auto-deploy? |
|----------|---------|--------|--------------|
| `ci.yml` | PR/push to main/develop | — | Tests only |
| `deploy-uat.yml` | CI passes on `develop` | UAT | ✅ Yes |
| `deploy-prod.yml` | Manual `workflow_dispatch` | Production | ⚠️ Human-gated |
| `db-backup.yml` | Cron 02:00 UTC daily | Production | ✅ Yes (see hygiene below) |
| `secret-rotation-reminder.yml` | Quarterly | — | Creates issue |

### NOT Automated (Manual Deploy)

| Component | Why | How to Deploy |
|-----------|-----|---------------|
| Auth gateway (`vectrade-auth`) | Separate service, not in main app | SCP + systemctl restart |
| Caddy config | Rarely changes | Edit `/etc/caddy/Caddyfile` + `caddy reload` |
| DB schema (auth tables) | One-time setup | Manual SQL via psql |

### Production Deploy Checklist

1. Ensure CI passes on target SHA
2. **Check GH Actions health** — verify no open issues from prior runs (see below)
3. Go to GitHub Actions → "Deploy to Production" → Run workflow
4. Enter the git SHA/tag → Run
5. Workflow: verifies CI gate → SSH → `deploy.sh prod <sha>` → health check → auto-rollback on failure
6. **Post-deploy** — confirm the Actions run completed green; close any transient issues

### Post-Deploy: Verify GH Actions

After every deployment (UAT or prod), check for GitHub Actions issues:

```bash
# List recent failed workflow runs
gh run list --repo VecTrade-io/vectrade-core --status failure --limit 5

# Check for open issues tagged by automation
gh issue list --repo VecTrade-io/vectrade-core --label "critical" --state open

# Re-run a failed job (if transient)
gh run rerun <run-id> --failed

# View specific run logs
gh run view <run-id> --log-failed
```

If a deploy workflow fails:
1. Check the run log for SSH timeout or health-check failure
2. Verify rollback executed successfully
3. Close the auto-created issue once resolved, or escalate if persistent

### Secrets Required (GitHub Environments)

| Secret | Used by |
|--------|---------|
| `ORACLE_VM_IP` | All deploy workflows |
| `ORACLE_SSH_KEY` | SSH access to VM |

### Server Details

| Property | Value |
|----------|-------|
| Host | `145.241.243.140` |
| SSH Key | `~/.oci/vm_ssh_key` |
| User | `ubuntu` (sudo) / `finance` (app owner) |
| App dir (prod) | `/opt/finance/app-prod` |
| App dir (uat) | `/opt/finance/app-uat` |
| Env files | `/opt/finance/env/.env.{uat,prod}` |
- **Worker not intercepting**: Verify routes in `deploy/maintenance/wrangler.toml` and worker is deployed

---

## DB Backup Hygiene (GH Actions)

The `db-backup.yml` workflow runs nightly at 02:00 UTC. It must stay **clean** — stale failures create noise and mask real problems.

### Ensuring Clean Runs

```bash
# Check recent backup run status
gh run list --repo VecTrade-io/vectrade-core --workflow db-backup.yml --limit 5

# Close stale backup issues (resolved failures)
gh issue list --repo VecTrade-io/vectrade-core --label "backup" --state open
gh issue close <issue-number> --comment "Resolved — backup runs healthy as of $(date +%F)"

# Re-run a failed backup manually
gh workflow run db-backup.yml --repo VecTrade-io/vectrade-core

# Verify latest backup on server
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  'sudo -u finance bash /opt/finance/app/deploy/scripts/db-verify-backup.sh prod'
```

### Common Backup Failures & Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| SSH timeout | VM resource spike | Re-run; if recurring, check `top` on VM |
| `pg_dump` OOM | Large tables | Increase `--compress` or add `--jobs=2` |
| Stale issue stays open | Auto-close not triggered | Manually close + verify next nightly passes |
| Disk full | Old backups not pruned | Run `db-backup.sh --prune` or clean `/opt/finance/backups/` |
| Permission denied | `finance` user borked | `sudo chown -R finance:finance /opt/finance/backups` |

### Routine Maintenance (weekly)

1. Confirm last 7 nightly runs are green: `gh run list --workflow db-backup.yml --limit 7`
2. Close any stale `backup` label issues
3. Verify disk space on backup volume: `ssh ... 'df -h /opt/finance/backups'`
4. Check WAL archiving isn't lagging (for point-in-time recovery)

---

## Settlement System (Trading Service)

The trading service runs a daily settlement that computes per-user equity snapshots, P&L, and fees. The leaderboard derives TWR (Time-Weighted Return) from these records.

| Property | Value |
|----------|-------|
| Config | `SETTLEMENT_HOUR_UTC=21` (9 PM UTC) |
| Trigger | Price-rule scheduler `_maybe_run_settlement()` — checked every 30s cycle |
| Table | `daily_settlements` |
| Leaderboard refresh | Every 5 min (separate scheduler) |
| TWR calculation | Requires ≥2 settlement days to produce non-zero values |

### Verify Settlement Ran

```bash
# Check logs
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo journalctl -u finance-trading@prod --since today --no-pager | grep 'Daily settlement completed'"

# Check DB
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo -u postgres psql -d trading -c \"SELECT settlement_date, COUNT(*) as users FROM daily_settlements GROUP BY settlement_date ORDER BY settlement_date;\""
```

### Backfill Missing Settlements

Use `systemd-run` to execute with the same environment as the service:

```bash
# 1. Upload backfill script
cat << 'SCRIPT' | ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 "cat > /tmp/backfill_settlement.py"
import asyncio
import sys
sys.path.insert(0, "/opt/finance/app-prod")
from datetime import date
from trading.database import async_session_factory
from trading.trade.settlement import run_daily_settlement

async def backfill():
    async with async_session_factory() as db:
        result = await run_daily_settlement(db, date(2026, 5, 28))  # <-- change date
        await db.commit()
        print("Backfilled:", len(result), "settlements")

asyncio.run(backfill())
SCRIPT

# 2. Run with systemd-run (inherits EnvironmentFile like the real service)
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo systemd-run --uid=finance --gid=finance \
    --working-directory=/opt/finance/app-prod \
    --setenv=HOME=/opt/finance \
    --property=EnvironmentFile=/opt/finance/env/.env.prod \
    /opt/finance/app-prod/.venv/bin/python3 /tmp/backfill_settlement.py"

# 3. Check result
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 \
  "sudo journalctl -u 'run-r*.service' --since '1 min ago' --no-pager"

# 4. Cleanup
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 "sudo rm /tmp/backfill_settlement.py"
```

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Leaderboard all 0% | No settlements or only 1 day of data | Verify `daily_settlements` table has ≥2 dates; backfill if missing |
| Settlement not running | Deadlock (fixed cc40426) or service crashed | Check `journalctl -u finance-trading@prod -p err`; restart if needed |
| Settlement runs but 0 users | All users inactive/suspended | Check `SELECT count(*) FROM users WHERE status='ACTIVE'` |

---

## OCI Email Delivery

Outbound email for all agent addresses (`@vectrade.io`) is sent via OCI Email Delivery.

| Property | Value |
|----------|-------|
| Region | UK South (London) |
| Email Domain | `vectrade.io` |
| OCID | `ocid1.emaildomain.oc1.uk-london-1.amaaaaaa2z522haa7rcvym76yrdfjmhay2vqgjp7jpsrwfywa4bybpwpilxa` |
| Created | 2026-05-28 |
| SPF | ✅ Configured |
| DKIM | ⏳ Pending (needs CNAME in Cloudflare) |
| SMTP Host | `smtp.email.uk-london-1.oci.oraclecloud.com` |
| SMTP Port | 587 (STARTTLS) |
| Free Tier | 100 emails/day |

### Approved Senders (to add)

- `james.whitfield@vectrade.io` (vector/CEO)
- `axon@vectrade.io` (axon/CTO)
- `oliver.hartley@vectrade.io` (relay/DevRel)
- `sophie.pearson@vectrade.io` (prism/Design)
- `nadia.okafor@vectrade.io` (quant/Research)
- `support@vectrade.io` (general)

### SMTP Credentials

Generate at: **OCI Console → Profile (top-right) → My profile → Resources → SMTP Credentials**

| Property | Value |
|----------|-------|
| Username | `ocid1.user.oc1..aaaaaaaatp6gau3nfvvi2x3uoftqzcwgkgyhsphbahhpq7hh4zzn523m6ykq@ocid1.tenancy.oc1..aaaaaaaakxgpugwzyxjxlg5ufgqbq6y44yr4ci2rgeiquzbxio4qzuddhasq.um.com` |
| Password | Stored in `.env` files only (never commit) |
| Region | `uk-london-1` |

Stored in: `/opt/finance/env/.env.agent` (on VM) or `vectrade-agent/.env` (local dev)

---

## X (Twitter) API — OAuth 1.0a (Posting)

Used by `vectrade-agent` to post tweets as `@vectrade`. Free tier: 50 posts/day.

| Property | Value |
|----------|-------|
| App Name | VecTrade |
| App ID | 32931054 |
| Account | `@vectrade` |
| Plan | Pay Per Use (Free) |
| Permissions | Read and Write |
| OAuth 2.0 Client ID | `cWZuMjA3eGc4bnNKdUNpZlVDR1o6MTpjaQ` (used for login) |

### OAuth 1.0a Credentials (for posting)

| Key | Value |
|-----|-------|
| Consumer Key (API Key) | `0gG7AFuYgXe878pgupM5iPTBE` |
| Consumer Secret (API Key Secret) | `DRQbKRlDS2jh3lrgnvLQmwRWesy4Kb8qZ5EKyjKhoLZyMloIwi` |
| Access Token | `2055016077495558144-RkMBKWjzcU6AOQhNwGvkENN7ZV2Tid` |
| Access Token Secret | `MRUxOcdq3eii665l25OaDtGIw8jUhWVAJ9RsnN9fVsuCT` |

### Env Vars (vectrade-agent)

```bash
AGENT_X_CONSUMER_KEY=0gG7AFuYgXe878pgupM5iPTBE
AGENT_X_CONSUMER_SECRET=DRQbKRlDS2jh3lrgnvLQmwRWesy4Kb8qZ5EKyjKhoLZyMloIwi
AGENT_X_ACCESS_TOKEN=2055016077495558144-RkMBKWjzcU6AOQhNwGvkENN7ZV2Tid
AGENT_X_ACCESS_TOKEN_SECRET=MRUxOcdq3eii665l25OaDtGIw8jUhWVAJ9RsnN9fVsuCT
```

Stored in: `/opt/finance/env/.env.agent` (on VM) or `vectrade-agent/.env` (local dev)

### Setup via Admin API

```bash
curl -X POST http://localhost:8003/admin/agents/shared/x/setup \
  -H "Authorization: Bearer dev-admin-token-local" \
  -H "Content-Type: application/json" \
  -d '{
    "consumer_key": "0gG7AFuYgXe878pgupM5iPTBE",
    "consumer_secret": "DRQbKRlDS2jh3lrgnvLQmwRWesy4Kb8qZ5EKyjKhoLZyMloIwi",
    "access_token": "2055016077495558144-RkMBKWjzcU6AOQhNwGvkENN7ZV2Tid",
    "access_token_secret": "MRUxOcdq3eii665l25OaDtGIw8jUhWVAJ9RsnN9fVsuCT"
  }'
```

---

## Agent UAT → Production Promotion Gate

Before promoting `vectrade-agent` from UAT to production, ALL items below must pass. Do not skip any.

### Pre-requisites (completed 2026-05-29)

- [x] Agent health endpoint responding (`/health`)
- [x] 6 agents loaded (vector, axon, prism, relay, quant, mirror)
- [x] LLM generation working (LiteLLM → Azure GPT-5-mini-EU)
- [x] Email inbound webhook → agent processing → reply via SMTP
- [x] Email escalation to human review queue (partnership/sensitive triggers)
- [x] Browser extension connectivity (CORS, admin token)
- [x] Scheduler started, 15 missions loaded
- [x] Pricing URL fix deployed (`/products` not `/pricing`)

### Gate Checklist (verify 2026-05-30)

| # | Check | How to verify | Status |
|---|-------|---------------|--------|
| 1 | Cron missions fire cleanly | Check logs after 09:00 UTC: `journalctl -u vectrade-agent@uat --since "06:00" \| grep "mission_"` — expect `axon-daily-health`, `quant-daily-analytics`, `prism-content-calendar` to show execution + completion | ⬜ |
| 2 | DKIM configured | Add OCI DKIM CNAME in Cloudflare → verify propagation: `dig CNAME <selector>._domainkey.vectrade.io` | ⬜ |
| 3 | Email deliverability | Send test email to `sophie.pearson@vectrade.io` → confirm reply lands in inbox (not spam), check SPF/DKIM pass in headers | ⬜ |
| 4 | Pricing URL in replies | Verify the test reply above contains `https://vectrade.io/products` (not `/pricing`) | ⬜ |
| 5 | X/Twitter posting | Generate a social draft via admin API → approve → confirm tweet appears on `@vectrade` | ⬜ |
| 6 | GitHub webhook (`ci_failure`) | Trigger deliberate test workflow failure OR verify webhook subscription is active: `gh api repos/VecTrade-io/vectrade-core/hooks` | ⬜ |
| 7 | No error spew in logs | `journalctl -u vectrade-agent@uat --since "06:00" -p err` — should be empty or only transient | ⬜ |

### Promotion Steps (once gate passes)

1. Create production env file: `/opt/finance/env/.env.agent-prod` (copy from UAT, update DB/Redis/auth values)
2. Create production database: `vectrade_agent_prod` with role `agent_app_prod`
3. Deploy agent to prod directory: `/opt/finance/app-prod/agent/` or as separate systemd unit `vectrade-agent@prod`
4. Add Caddy route for `api.vectrade.io/api/v1/agent/*` (same pattern as UAT)
5. Configure Cloudflare Email Worker to route prod emails (separate worker or env toggle)
6. Add status monitor: edit `.upptimerc.yml` to add agent health endpoint
7. Verify end-to-end on production domain

### Rollback

If production agent misbehaves:
```bash
# Stop agent
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 'sudo systemctl stop vectrade-agent@prod'

# Remove Caddy route (comment out agent block) + reload
ssh -i ~/.oci/vm_ssh_key ubuntu@145.241.243.140 'sudo caddy reload --config /etc/caddy/Caddyfile'

# Email routing: revert CF worker to drop/bounce agent-addressed emails
```

---

## Constraints

- DO NOT manually edit files in `history/`, `api/`, or `graphs/` (auto-generated)
- DO NOT add monitors for internal/private services
- ALWAYS use HTTPS endpoints
- ALWAYS specify expected status codes
