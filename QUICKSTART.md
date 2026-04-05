# Security Fabric — Quick Start

## Prerequisites
- Docker Desktop (https://docker.com/products/docker-desktop)
- That's it.

## Start Everything (one command)

```bash
docker compose up --build
```

Wait about 2 minutes for all services to start. The API Gateway automatically runs
database migrations and seeds demo data on first boot.

## Open the App

| Service        | URL                          | Login            |
|----------------|------------------------------|------------------|
| **Dashboard**  | http://localhost:5173        | admin@demo.io / demo1234 |
| API Docs       | http://localhost:8000/docs   | —                |
| Grafana        | http://localhost:3000        | admin / admin    |
| Kafka UI       | http://localhost:8080        | —                |
| Email (MailHog)| http://localhost:8025        | —                |
| Prometheus     | http://localhost:9090        | —                |

## Demo Accounts

| Email              | Password  | Plan         |
|--------------------|-----------|--------------|
| admin@demo.io      | demo1234  | Professional |
| analyst@demo.io    | demo1234  | Starter      |
| free@demo.io       | demo1234  | Free         |

## Try the Threat Detection

1. Log in at http://localhost:5173
2. Go to **Telemetry** page
3. Click **START** to begin traffic simulation
4. Watch live threats appear on the **Dashboard**

## Stop Everything

```bash
docker compose down
```

## Stop and Delete All Data

```bash
docker compose down -v
```
