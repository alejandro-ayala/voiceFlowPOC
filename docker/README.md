# Docker Infrastructure for VoiceFlow Tourism PoC

This directory contains Docker infrastructure files for the VoiceFlow project.

## 📁 Structure

```
docker/
├── scripts/
│   ├── entrypoint.sh      # Container startup script with validations
│   └── healthcheck.sh     # Health check script for Docker
└── nginx/
    └── nginx.conf         # Nginx reverse proxy configuration (production)
```

---

## 🚀 Usage

### **Development Mode** (default)

Includes hot-reload and debug mode:

```bash
# Start with hot-reload
docker compose up

# Or rebuild and start
docker compose up --build
```

Configuration:
- Loads `docker-compose.yml` + `docker-compose.override.yml` automatically
- Source code mounted as volumes (changes = instant reload)
- `DEBUG=true`, `USE_REAL_AGENTS=false`
- Port 8000 exposed

---

### **Production Mode**

With Nginx reverse proxy:

```bash
# Start production stack
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

Configuration:
- Nginx on port 80 (reverse proxy)
- Application not exposed directly
- `DEBUG=false`, `USE_REAL_AGENTS=true`
- No hot-reload, no volume mounts
- Health checks enabled

---

## 📜 Scripts

### `entrypoint.sh`

Executed before the main application starts. Performs:

- Environment validation
- Dependency checks (Python packages, ffmpeg)
- `.env` file creation from template if missing
- Warning if critical API keys are missing
- Informational startup banner

**Exit codes:**
- `0`: All checks passed, continues to CMD
- `1`: Critical error, container stops

---

### `healthcheck.sh`

Periodic health check for Docker container health status.

- Calls `/api/v1/health/` endpoint
- 5-second timeout
- Container marked unhealthy after 3 consecutive failures
- Docker can auto-restart unhealthy containers

**Check interval:** Every 30 seconds  
**Start period:** 15 seconds (grace period on startup)

---

## 🌐 Nginx Configuration

### Features

- **Static files**: Served directly by Nginx (better performance)
- **API proxy**: Forwards `/api/*` to FastAPI backend
- **Compression**: gzip enabled for text responses
- **Security headers**: X-Content-Type-Options, X-Frame-Options, etc.
- **WebSocket ready**: Upgrade headers configured
- **Max upload size**: 50MB (for audio files)

### Endpoints

| Path | Handled by | Cache |
|------|------------|-------|
| `/static/*` | Nginx directly | 7 days |
| `/api/*` | Proxy to app:8000 | No cache |
| `/` | Proxy to app:8000 | No cache |

### HTTPS Configuration

Uncomment the HTTPS server block in `nginx.conf` and configure:

1. **Install certbot** (Let's Encrypt):
   ```bash
   certbot certonly --standalone -d your-domain.com
   ```

2. **Update nginx.conf**:
   - Set `server_name your-domain.com`
   - Point to certificate paths

3. **Mount certificates** in `docker-compose.prod.yml`:
   ```yaml
   volumes:
     - /etc/letsencrypt:/etc/letsencrypt:ro
   ```

---

## 🔧 Customization

### Environment Variables

Set in `.env` or `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `VOICEFLOW_DEBUG` | `false` | Enable debug mode |
| `VOICEFLOW_USE_REAL_AGENTS` | `false` | Use real AI agents (OpenAI) |
| `VOICEFLOW_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `OPENAI_API_KEY` | - | OpenAI API key (required if USE_REAL_AGENTS=true) |
| `AZURE_SPEECH_KEY` | - | Azure Speech Services key |
| `AZURE_SPEECH_REGION` | - | Azure Speech region |

---

## 🐛 Debugging

### Check container health

```bash
docker ps
# Look for "healthy" status
```

### View health check logs

```bash
docker inspect --format='{{json .State.Health}}' voiceflowpoc-app-1 | jq
```

### Enter running container

```bash
docker compose exec app bash
```

### View entrypoint output

```bash
docker compose logs app | grep "VoiceFlow Tourism PoC"
```

---

## 📊 Monitoring

### Container stats

```bash
docker stats
```

### Application logs

```bash
# All logs
docker compose logs -f

# Only app logs
docker compose logs -f app

# Last 100 lines
docker compose logs --tail=100 app
```

---

## 🚦 Deployment

### Azure Container Instances

```bash
# Build and push image
docker build -t voiceflowpoc:latest .
docker tag voiceflowpoc:latest yourregistry.azurecr.io/voiceflowpoc:latest
docker push yourregistry.azurecr.io/voiceflowpoc:latest

# Deploy
az container create \
  --resource-group voiceflow-rg \
  --name voiceflow-app \
  --image yourregistry.azurecr.io/voiceflowpoc:latest \
  --dns-name-label voiceflow \
  --ports 80 \
  --environment-variables \
    VOICEFLOW_USE_REAL_AGENTS=true \
    VOICEFLOW_DEBUG=false \
  --secure-environment-variables \
    OPENAI_API_KEY=$OPENAI_API_KEY \
    AZURE_SPEECH_KEY=$AZURE_SPEECH_KEY
```

### Azure App Service

```bash
# Configure App Service for containers
az webapp create \
  --resource-group voiceflow-rg \
  --plan voiceflow-plan \
  --name voiceflow-app \
  --deployment-container-image-name yourregistry.azurecr.io/voiceflowpoc:latest
```

---

## 📚 References

- [Docker Compose documentation](https://docs.docker.com/compose/)
- [Nginx reverse proxy guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Docker health checks](https://docs.docker.com/engine/reference/builder/#healthcheck)
