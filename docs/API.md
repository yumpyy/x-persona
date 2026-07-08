# API Reference

REST API for managing tenants, personas, agents, and activity.

---

## Base URL

```
http://localhost:8000/api/v1
```

Start the server:
```bash
xpersonas serve --db xpersonas.db --port 8000
```

Auto-generated docs at http://localhost:8000/docs (Swagger UI).

---

## Authentication

Generate an API key:
```bash
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/api-keys
```

Include in requests:
```bash
curl -H "X-API-Key: sk-..." http://localhost:8000/api/v1/personas
```

---

## Tenants

### Create tenant

```http
POST /api/v1/tenants
Content-Type: application/json

{
  "name": "MyCompany",
  "mode": "brand",
  "config": {}
}
```

Response:
```json
{
  "id": "t_abc123",
  "name": "MyCompany",
  "mode": "brand",
  "config": {},
  "is_active": true,
  "created_at": "2026-01-01T00:00:00"
}
```

### Get tenant

```http
GET /api/v1/tenants/{tenant_id}
```

### List tenants

```http
GET /api/v1/tenants
```

### Update tenant

```http
PATCH /api/v1/tenants/{tenant_id}
Content-Type: application/json

{
  "name": "NewName",
  "mode": "brand",
  "config": {"max_personas": 20}
}
```

### Delete tenant

```http
DELETE /api/v1/tenants/{tenant_id}
```

### Generate API key

```http
POST /api/v1/tenants/{tenant_id}/api-keys
```

Response:
```json
{
  "api_key": "sk-...",
  "tenant_id": "t_abc123"
}
```

---

## Personas

### Create persona

```http
POST /api/v1/personas
Content-Type: application/json

{
  "tenant_id": "t_abc123",
  "platform": "x",
  "handle": "mybot",
  "display_name": "My Bot",
  "config": {
    "mode": "brand",
    "identity": {"handle": "mybot", "display_name": "My Bot"},
    "engagement": {"strategy": "active"}
  }
}
```

### List personas

```http
GET /api/v1/personas?tenant_id=t_abc123
```

### Get persona

```http
GET /api/v1/personas/{persona_id}
```

### Update persona

```http
PATCH /api/v1/personas/{persona_id}
Content-Type: application/json

{
  "config": {
    "engagement": {"strategy": "selective"}
  }
}
```

### Delete persona

```http
DELETE /api/v1/personas/{persona_id}
```

---

## Agents

### Start agent

```http
POST /api/v1/agents/start/{persona_id}
```

Response:
```json
{
  "persona_id": "p_abc123",
  "status": "running",
  "strategy": "active",
  "cycles_completed": 0,
  "started_at": "2026-01-01T00:00:00",
  "last_cycle_at": null,
  "error_message": null
}
```

### Stop agent

```http
POST /api/v1/agents/stop/{persona_id}
```

### List running agents

```http
GET /api/v1/agents/status
```

### Get agent status

```http
GET /api/v1/agents/status/{persona_id}
```

---

## Activity

### Get activity log

```http
GET /api/v1/activity/{persona_id}?page=1&limit=50
```

Response:
```json
{
  "entries": [
    {
      "id": 1,
      "timestamp": "2026-01-01T12:00:00",
      "platform": "x",
      "action_type": "reply",
      "target_post_id": "123456",
      "target_author": "@someone",
      "content": "Great post! I've been using...",
      "score": 8.5,
      "reason": "Relevant to CI/CD topic",
      "success": true,
      "error": null
    }
  ],
  "total": 142
}
```

### Get statistics

```http
GET /api/v1/activity/{persona_id}/stats
```

Response:
```json
{
  "total_actions": 142,
  "actions_by_type": {"like": 80, "reply": 35, "quote": 15, "repost": 12},
  "success_rate": 0.94,
  "actions_last_24h": 23
}
```

---

## Products (brand mode)

### Create product

```http
POST /api/v1/products?tenant_id=t_abc123
Content-Type: application/json

{
  "name": "FastBuild",
  "description": "CI/CD tool that's 10x faster",
  "features": ["parallel builds", "caching", "distributed"],
  "pricing": "$49/mo",
  "buy_url": "https://fastbuild.dev",
  "pain_points": ["slow builds", "ci is slow", "build times"],
  "frequency_cap_per_week": 3
}
```

### List products

```http
GET /api/v1/products?tenant_id=t_abc123
```

### Get product

```http
GET /api/v1/products/{product_id}
```

### Delete product

```http
DELETE /api/v1/products/{product_id}
```

---

## Contacts (personal mode)

### List contacts

```http
GET /api/v1/contacts/{persona_id}
```

### Connection-ready contacts

```http
GET /api/v1/contacts/{persona_id}/ready
```

Returns contacts whose `stage` is `connect_ready`: relationships warm enough for DM or direct outreach.

### Networking stats

```http
GET /api/v1/contacts/{persona_id}/stats
```

Response:
```json
{
  "total": 47,
  "by_stage": {"stranger": 20, "acquainted": 15, "familiar": 10, "connect_ready": 2},
  "average_rapport": 4.2
}
```

---

## Escalations

### List escalations

```http
GET /api/v1/escalations/{persona_id}
```

### Acknowledge escalation

```http
POST /api/v1/escalations/{escalation_id}/ack
```

---

## Health

```http
GET /api/v1/health
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "platforms": ["x"]
}
```

---

## Error responses

All errors follow the format:

```json
{
  "detail": "Error message"
}
```

Common status codes:
- `400`: Bad request (invalid input)
- `404`: Not found
- `422`: Validation error
- `503`: Agent runner not available (server not started)
