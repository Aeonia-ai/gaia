# Troubleshooting Inter-Service Communication

This guide covers common issues when services communicate with each other, especially in cloud environments where infrastructure layers may modify requests/responses.

## "Invalid JSON Response" Errors

### Symptom
- Gateway returns: `{"detail": "Invalid JSON response from auth service"}`
- Works locally but fails on remote deployment
- Auth service logs show successful 200 OK responses
- Other services seem to be working correctly

### Common Causes

#### 1. Transparent Response Compression (Most Common on Cloud Platforms)

**What happens**: Cloud platforms like Fly.io, AWS ALB, or GCP may automatically compress HTTP responses between services to save bandwidth. If your HTTP client isn't configured to handle the compression algorithm used, it will try to parse compressed binary data as JSON.

**How to diagnose**:
1. Check gateway logs for the actual error:
   ```
   JSON error: 'utf-8' codec can't decode byte 0x8b in position 0: invalid start byte
   ```
2. Look for compression headers in responses:
   ```
   'content-encoding': 'br'  # Brotli compression
   'content-encoding': 'gzip'  # Gzip compression
   ```
3. Raw response will start with binary data instead of `{` character

**Solution for Fly.io (Brotli)**:
```python
# In requirements.txt, change:
httpx
# To:
httpx[brotli]
```

**Solution for general compression support**:
```python
# Configure HTTP client to handle all compression types
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    headers={
        "User-Agent": "GaiaGateway/1.0"
    }
    # httpx will automatically handle Accept-Encoding
)
```

#### 2. Service URL Misconfiguration

**What happens**: Gateway is calling the wrong URL or using internal DNS that's not working.

**How to diagnose**:
```bash
# Check what URLs are configured
fly ssh console -a gaia-gateway-dev
env | grep SERVICE_URL

# Test direct service connectivity
curl -v https://gaia-auth-dev.fly.dev/health
```

**Solution**: Ensure service URLs are using public HTTPS endpoints for cloud deployments:
```bash
fly secrets set -a gaia-gateway-dev \
  AUTH_SERVICE_URL="https://gaia-auth-dev.fly.dev" \
  CHAT_SERVICE_URL="https://gaia-chat-dev.fly.dev"
```

#### 3. Response Size Limits

**What happens**: Large responses get truncated or fail to parse.

**How to diagnose**:
- Check if the error occurs only with large payloads
- Look for partial JSON in error messages

**Solution**: Increase client timeout and size limits:
```python
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(60.0),  # Increase timeout
    limits=httpx.Limits(max_response_size=10_000_000)  # 10MB limit
)
```

## Debugging Steps

1. **Enable detailed logging** in the gateway:
   ```python
   try:
       response = await http_client.post(url, json=data)
       logger.debug(f"Response status: {response.status_code}")
       logger.debug(f"Response headers: {dict(response.headers)}")
       if response.status_code != 200:
           logger.error(f"Response body: {response.text}")
   except Exception as e:
       logger.error(f"Request failed: {type(e).__name__}: {e}")
       raise
   ```

2. **Test with curl** to isolate client issues:
   ```bash
   # Test gateway endpoint
   curl -v -X POST https://gaia-gateway-dev.fly.dev/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password"}'
   
   # Test auth service directly
   curl -v -X POST https://gaia-auth-dev.fly.dev/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password"}'
   ```

3. **Check infrastructure logs**:
   ```bash
   # Gateway logs
   fly logs -a gaia-gateway-dev
   
   # Auth service logs  
   fly logs -a gaia-auth-dev
   
   # Look for timing correlation
   ```

## Platform-Specific Quirks

### Fly.io
- Automatically applies Brotli compression between services
- Internal `.internal` DNS can be unreliable - use public URLs
- Health checks may cause false positives in logs

### AWS
- ALB may apply gzip compression
- Security groups can block inter-service communication
- VPC endpoints needed for private communication

### Google Cloud
- Cloud Run services need proper IAM for inter-service auth
- Automatic gzip compression on responses
- Regional restrictions may apply

## Best Practices

1. **Always configure HTTP clients for compression**:
   ```python
   # Python/httpx
   pip install httpx[brotli,http2]
   
   # Node.js/axios
   npm install axios compression
   ```

2. **Use structured logging** for debugging:
   ```python
   logger.info("Inter-service request", extra={
       "service": service_name,
       "endpoint": path,
       "method": method,
       "request_id": request_id
   })
   ```

3. **Implement retry logic** with exponential backoff:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10)
   )
   async def call_service(url, data):
       response = await http_client.post(url, json=data)
       response.raise_for_status()
       return response.json()
   ```

4. **Monitor inter-service latency**:
   - Set up alerts for response times > 1s
   - Track 5xx errors between services
   - Monitor compression ratios

## Common Error Patterns

| Error Message | Likely Cause | Solution |
|--------------|-------------|----------|
| `'utf-8' codec can't decode byte 0x8b` | Gzip compression | Add gzip support to HTTP client |
| `'utf-8' codec can't decode byte 0x1f` | Brotli compression | Install httpx[brotli] |
| `Invalid \escape: line 1 column X` | Malformed JSON in request | Check client JSON encoding |
| `Connection refused` | Wrong service URL or port | Verify service discovery config |
| `SSL: CERTIFICATE_VERIFY_FAILED` | Self-signed cert or wrong hostname | Use proper certs or disable verification (dev only) |

## Related Documentation
- [Fly.io DNS Troubleshooting](./troubleshooting-flyio-dns.md)
- [Deployment Best Practices](./deployment-best-practices.md)
- [Service Discovery Configuration](./service-registry-pattern.md)