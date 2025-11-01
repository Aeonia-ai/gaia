# Troubleshooting Fly.io Internal DNS Issues

## Problem Description

**Symptoms:**
- Gateway health check shows "degraded" status
- Individual services are healthy when tested directly  
- Error messages like "Service chat unavailable" or 503 errors
- `curl` from gateway to service.internal fails with "connection refused"

**Root Cause:**
Fly.io's `.internal` DNS occasionally stops working - this is a [documented issue](https://community.fly.io/t/internal-dns-occasionally-stops-working-for-some-apps/5748) where apps stop advertising themselves via internal DNS.

## Quick Fix

```bash
# Switch gateway to use public URLs instead of internal DNS
fly secrets set -a gaia-gateway-dev \
  "CHAT_SERVICE_URL=https://gaia-chat-dev.fly.dev" \
  "AUTH_SERVICE_URL=https://gaia-auth-dev.fly.dev" \
  "ASSET_SERVICE_URL=https://gaia-asset-dev.fly.dev"

# Test the fix
./scripts/test.sh --url https://gaia-gateway-dev.fly.dev health
```

## Diagnosis Steps

1. **Check gateway status**
   ```bash
   ./scripts/test.sh --url https://gaia-gateway-dev.fly.dev health
   # Look for: "status": "degraded"
   ```

2. **Verify individual services work**
   ```bash
   curl -H "X-API-Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE" \
     https://gaia-chat-dev.fly.dev/health
   # Should return: healthy status
   ```

3. **Test internal DNS connectivity**
   ```bash
   fly ssh console -a gaia-gateway-dev \
     --command "curl -I http://gaia-chat-dev.internal:8000/health"
   # Will show: "Failed to connect to gaia-chat-dev.internal"
   ```

## Prevention

Always use **public URLs** for service-to-service communication on Fly.io:

```bash
# ❌ Unreliable internal DNS
AUTH_SERVICE_URL=http://gaia-auth-dev.internal:8000

# ✅ Reliable public URLs
AUTH_SERVICE_URL=https://gaia-auth-dev.fly.dev
```

## Configuration Updates

The `fly.gateway.dev.toml` has been updated to use public URLs by default:

```toml
# Full microservices URLs (dev environment) - Using public URLs (internal DNS unreliable)
AUTH_SERVICE_URL = "https://gaia-auth-dev.fly.dev"
ASSET_SERVICE_URL = "https://gaia-asset-dev.fly.dev"
CHAT_SERVICE_URL = "https://gaia-chat-dev.fly.dev"
```

## Notes

- **Staging/Production**: Use embedded services (`localhost:8000`) so internal DNS issues don't apply
- **Security**: Public URLs are still secure - communication is encrypted via HTTPS
- **Performance**: Minimal impact - requests still stay within Fly.io's network
- **Cost**: No additional cost for using public URLs vs internal DNS

## References

- [Fly.io Internal DNS Issues](https://community.fly.io/t/internal-dns-occasionally-stops-working-for-some-apps/5748)
- [Fly.io Private Networking Documentation](https://fly.io/docs/networking/private-networking/)
- [Fly.io Troubleshooting Guide](https://fly.io/docs/getting-started/troubleshooting/)