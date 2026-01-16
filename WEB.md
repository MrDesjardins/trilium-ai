# Web Interface Guide

Trilium AI includes a clean, modern web interface for querying your notes without using the command line.

## Quick Start

### Development Mode

```bash
# Start with auto-reload (for development)
uv run trilium-ai web --reload

# Custom port
uv run trilium-ai web --port 8080

# Custom host (e.g., localhost only)
uv run trilium-ai web --host 127.0.0.1 --port 8080
```

Then open http://localhost:3000 in your browser.

### Production Mode

```bash
# Install systemd service (recommended for production)
sudo ./scripts/install-service.sh
```

The web interface will automatically start and be available at the configured port.

## Configuration

Edit `config/config.yaml`:

```yaml
web:
  enabled: true
  host: "0.0.0.0"  # 0.0.0.0 = all interfaces, 127.0.0.1 = localhost only
  port: 3000       # Change if port is already in use
```

### Changing the Port

If port 3000 is already in use by another service:

```yaml
web:
  port: 8080  # or any available port
```

Then restart the service:

```bash
sudo systemctl restart trilium-ai-web.service
```

## Features

### Search Interface
- **Clean, modern UI** with responsive design
- **Real-time search** with loading states
- **Advanced options** for customizing results
- **Example queries** to get started quickly

### Results Display
- **Answer section** with AI-generated response
- **Source attribution** with direct links to notes in Trilium
- **Note hierarchy** showing location in your note tree
- **Clickable links** to open notes directly in Trilium

### Status Indicator
- Shows connection status to Weaviate
- Displays total number of indexed chunks
- Updates automatically

## API Endpoints

The web interface exposes a REST API:

### POST /api/query
Query your notes using natural language.

**Request:**
```json
{
  "query": "What are my notes about Python?",
  "top_k": 5,
  "provider": "openai",  // optional
  "model": "gpt-4-turbo"  // optional
}
```

**Response:**
```json
{
  "answer": "Your notes about Python include...",
  "sources": [
    {
      "title": "Python Basics",
      "note_id": "abc123",
      "url": "http://localhost:8080/#root/abc123",
      "path": "root > Programming > Python"
    }
  ],
  "chunks_found": 5
}
```

### GET /api/status
Check system status.

**Response:**
```json
{
  "weaviate_connected": true,
  "total_chunks": 1234,
  "config_valid": true
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Using the API Programmatically

### cURL Example

```bash
curl -X POST http://localhost:3000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my project goals?"}'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:3000/api/query",
    json={
        "query": "What are my notes about machine learning?",
        "top_k": 10
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])}")
```

### JavaScript Example

```javascript
fetch('http://localhost:3000/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'Summarize my meeting notes',
    top_k: 5
  })
})
  .then(response => response.json())
  .then(data => {
    console.log('Answer:', data.answer);
    console.log('Sources:', data.sources);
  });
```

## Production Deployment

### Systemd Service

The web interface runs as a systemd service:

```bash
# Status
sudo systemctl status trilium-ai-web.service

# Logs
sudo journalctl -u trilium-ai-web.service -f

# Restart
sudo systemctl restart trilium-ai-web.service

# Stop
sudo systemctl stop trilium-ai-web.service

# Start
sudo systemctl start trilium-ai-web.service
```

### Reverse Proxy Setup

For production, use a reverse proxy like Nginx:

```nginx
server {
    listen 80;
    server_name trilium-ai.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS with Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d trilium-ai.example.com
```

## Security Considerations

### Network Access

By default, the web interface binds to `0.0.0.0` (all interfaces). For security:

**Localhost only:**
```yaml
web:
  host: "127.0.0.1"  # Only accessible from the same machine
```

**Specific interface:**
```yaml
web:
  host: "192.168.1.100"  # Only accessible on this network interface
```

### Authentication

The web interface does not include built-in authentication. For production:

1. **Use a reverse proxy** with authentication (Nginx + basic auth, Caddy, etc.)
2. **Use a VPN** to restrict access
3. **Firewall rules** to limit IP addresses
4. **OAuth proxy** like oauth2-proxy

Example Nginx with basic auth:

```nginx
location / {
    auth_basic "Trilium AI";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:3000;
}
```

Create password file:
```bash
sudo apt-get install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd username
```

### HTTPS

Always use HTTPS in production to encrypt traffic containing note content.

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :3000

# Or use netstat
sudo netstat -tulpn | grep 3000
```

Solution: Change the port in config.yaml

### Service Won't Start

```bash
# Check service logs
sudo journalctl -u trilium-ai-web.service -n 50

# Check configuration
uv run trilium-ai web --host 127.0.0.1 --port 3001

# Verify dependencies
cd /opt/trilium-ai
uv sync
```

### Cannot Connect to Weaviate

1. Check if Weaviate is running:
```bash
docker ps | grep weaviate
```

2. Check Weaviate logs:
```bash
cd /opt/trilium-ai/docker
docker compose logs weaviate
```

3. Restart Weaviate:
```bash
cd /opt/trilium-ai/docker
docker compose restart weaviate
```

### Slow Response Times

- **Reduce top_k**: Lower the number of results retrieved
- **Optimize embedding model**: Use a faster model in config
- **Increase resources**: Allocate more RAM/CPU to Weaviate

## Customization

### Styling

Edit `/src/trilium_ai/web/static/css/style.css` to customize the appearance.

### Frontend Logic

Edit `/src/trilium_ai/web/static/js/app.js` to modify behavior.

### Templates

Edit `/src/trilium_ai/web/templates/index.html` to change the HTML structure.

After making changes, restart the service:

```bash
sudo systemctl restart trilium-ai-web.service
```

Or in development mode with auto-reload:

```bash
uv run trilium-ai web --reload
```

## Performance

### Concurrent Requests

The web interface uses Uvicorn with default settings. For high traffic:

```bash
# Run with more workers
uv run uvicorn trilium_ai.web.app:app \
  --host 0.0.0.0 \
  --port 3000 \
  --workers 4
```

### Caching

Consider adding caching for frequently asked questions:
- Redis for query result caching
- Browser caching for static assets

## Monitoring

### Access Logs

```bash
# Real-time logs
sudo journalctl -u trilium-ai-web.service -f

# Last 100 lines
sudo journalctl -u trilium-ai-web.service -n 100

# Since yesterday
sudo journalctl -u trilium-ai-web.service --since yesterday
```

### Health Checks

Monitor the `/health` endpoint:

```bash
curl http://localhost:3000/health
```

Set up monitoring with tools like:
- Uptime Kuma
- Prometheus + Grafana
- Netdata

## FAQ

### Can I disable the web interface?

Yes, set `enabled: false` in config.yaml and don't start the service.

### Can I run multiple instances?

Yes, use different ports for each instance.

### Does it support multiple users?

The interface itself doesn't have user authentication. Implement authentication via reverse proxy or VPN.

### Can I use it remotely?

Yes, but ensure you use HTTPS and authentication for security.

### What browsers are supported?

All modern browsers: Chrome, Firefox, Safari, Edge (latest versions).

---

For more information, see:
- [README.md](README.md) - General documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- [CLAUDE.md](CLAUDE.md) - Development guide
