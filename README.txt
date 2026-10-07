# Weltrade GitHub MT5 test

This folder contains a read-only connection test.

## GitHub Secrets required

Repository → Settings → Secrets and variables → Actions → New repository secret:

- `WELTRADE_LOGIN` = your MT5 account number
- `WELTRADE_PASSWORD` = your MT5 trading password
- `WELTRADE_SERVER` = `Weltrade-Real`

Never put the password directly in code.

## Run

GitHub → Actions → **Weltrade MT5 Connection Test** → Run workflow.

The workflow performs DNS/network checks and then attempts a read-only MT5 connection. It does not place, modify, or close trades.

Important: this is a connectivity proof-of-concept, not a 24/7 trading server. GitHub-hosted runners are temporary machines.
