# CLI Reference

All commands for the `xpersonas` CLI.

---

## Global options

```bash
xpersonas --help        # Show help
xpersonas --version     # Show version
```

---

## init

Initialize the database and create the first tenant.

```bash
xpersonas init setup --db <path> --tenant-name <name>
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db` | `xpersonas.db` | Database file path |
| `--tenant-name` | `Default` | Name of the first tenant |

Example:
```bash
xpersonas init setup --db xpersonas.db --tenant-name "Acme Corp"
```

---

## tenant

Manage tenants.

### tenant create

```bash
xpersonas tenant create <name> --db <path> [--mode brand|personal]
```

Example:
```bash
xpersonas tenant create "Acme Corp" --db xpersonas.db --mode brand
```

### tenant list

```bash
xpersonas tenant list --db <path>
```

Output:
```
  t_abc123  Acme Corp  mode=brand
  t_def456  Personal   mode=personal
```

---

## persona

Manage personas.

### persona create

```bash
xpersonas persona create --db <path> --tenant-id <id> --handle <handle> --display-name <name> [--strategy <strategy>]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--db` | `xpersonas.db` | Database file path |
| `--tenant-id` | (required) | Tenant ID |
| `--handle` | (required) | Platform handle (without @) |
| `--display-name` | (required) | Display name |
| `--strategy` | `active` | Engagement strategy |

The persona mode is set in the JSON config (`"mode": "brand"` or `"mode": "personal"`). Default mode is `brand`.

Example:
```bash
xpersonas persona create \
  --db xpersonas.db \
  --tenant-id t_abc123 \
  --handle "devtoolsfan" \
  --display-name "Dev Tools Fan" \
  --strategy "active"
```

### persona list

```bash
xpersonas persona list --db <path> [--tenant-id <id>]
```

### persona import

Import a persona from a JSON file:

```bash
xpersonas persona import --db <path> --file <persona.json>
```

The JSON is validated before import. If validation fails, the import will show the error.

### persona export

Export a persona to a JSON file:

```bash
xpersonas persona export --db <path> --persona-id <id> --output <file.json>
```

---

## agent

Control running agents.

### agent start

Start an agent for a persona. Runs forever until stopped.

```bash
xpersonas agent start <persona_id> --db <path> [--visible]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--visible` | `false` | Show browser window (non-headless) |

Example:
```bash
xpersonas agent start p_abc123 --db xpersonas.db
```

The agent will:
1. Load the persona from the database
2. Start a Playwright browser session
3. Navigate to X/Twitter home
4. Run the agent loop (scroll, decide, engage, repeat)

Press `Ctrl+C` to stop.

### agent stop

Mark an agent as stopped in the database.

```bash
xpersonas agent stop <persona_id> --db <path>
```

Note: If the agent is running in the API server, use `POST /api/v1/agents/stop/{persona_id}` instead.

### agent status

Show running agents from the database.

```bash
xpersonas agent status --db <path>
```

Output:
```
  @devtoolsfan (Dev Tools Fan), running, 15 cycles
  @researchbot (Research Bot), on_break (1200s), 8 cycles
```

### agent once

Run a single agent cycle (for testing).

```bash
xpersonas agent once <persona_id> --db <path> [--dry-run]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--dry-run` | `false` | Build graph but don't execute |

Example:
```bash
# Just validate the graph builds correctly
xpersonas agent once p_abc123 --db xpersonas.db --dry-run

# Run one actual cycle
xpersonas agent once p_abc123 --db xpersonas.db
```

---

## product

Manage products for UGC seeding (brand mode).

### product create

```bash
xpersonas product create --db <path> --tenant-id <id> --name <name> [--description <desc>] [--pain-points <p1,p2,...>] [--buy-url <url>]
```

Example:
```bash
xpersonas product create \
  --db xpersonas.db \
  --tenant-id t_abc123 \
  --name "FastBuild" \
  --description "CI/CD tool that's 10x faster" \
  --pain-points "slow builds,ci is slow,build times" \
  --buy-url "https://fastbuild.dev"
```

### product list

```bash
xpersonas product list --db <path> [--tenant-id <id>]
```

---

## contact

Manage contacts and relationships (personal mode).

### contact list

```bash
xpersonas contact list <persona_id> --db <path>
```

### contact ready

Show contacts ready for direct connection:

```bash
xpersonas contact ready <persona_id> --db <path>
```

---

## serve

Start the API server.

```bash
xpersonas serve --db <path> [--host <host>] [--port <port>]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8000` | Port number |

Example:
```bash
xpersonas serve --db xpersonas.db --port 8000
```

Then open http://localhost:8000/docs for the Swagger UI.

---

## Examples

### Complete workflow

```bash
# 1. Initialize
xpersonas init setup --db xpersonas.db --tenant-name "Acme Corp"

# 2. Create a persona
xpersonas persona create \
  --db xpersonas.db \
  --tenant-id t_abc123 \
  --handle "devtoolsfan" \
  --display-name "Dev Tools Fan" \
  --strategy "active"

# 3. Add a product (brand mode)
xpersonas product create \
  --db xpersonas.db \
  --tenant-id t_abc123 \
  --name "FastBuild" \
  --pain-points "slow builds,ci is slow"

# 4. Start the agent
xpersonas agent start p_abc123 --db xpersonas.db

# 5. In another terminal, check status
xpersonas agent status --db xpersonas.db

# 6. Or start the API server
xpersonas serve --db xpersonas.db
```

### Testing with dry-run

```bash
# Validate graph builds correctly
xpersonas agent once p_abc123 --db xpersonas.db --dry-run

# Run one cycle (needs OpenAI API key + Playwright)
xpersonas agent once p_abc123 --db xpersonas.db
```

### Managing via API

```bash
# Start server
xpersonas serve --db xpersonas.db &

# Create persona via API
curl -X POST http://localhost:8000/api/v1/personas \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "t_abc123", "handle": "mybot", "display_name": "My Bot", "config": {"mode": "brand", "identity": {"handle": "mybot", "display_name": "My Bot"}}}'

# Start agent
curl -X POST http://localhost:8000/api/v1/agents/start/p_abc123

# Check status
curl http://localhost:8000/api/v1/agents/status

# View activity
curl http://localhost:8000/api/v1/activity/p_abc123/stats
```
