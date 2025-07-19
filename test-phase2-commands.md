# Phase 2 mTLS + JWT Testing Commands

Run these commands to verify Phase 2 is working correctly:

## 1. Test Certificate Loading
```bash
# Check all certificates exist
ls -la certs/
ls -la certs/gateway/
ls -la certs/auth-service/
ls -la certs/asset-service/
ls -la certs/chat-service/
ls -la certs/web-service/
```

## 2. Test JWT Token Generation
```bash
# Request a service token from auth service
curl -X POST http://localhost:8666/internal/service-token \
  -H "Content-Type: application/json" \
  -H "X-API-Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE" \
  -d '{"service_name": "gateway"}'
```

## 3. Test JWT Validation
```bash
# First get a token (save the token from above command)
TOKEN="<paste-token-here>"

# Validate the token
curl -X POST http://localhost:8666/auth/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE" \
  -d "{\"token\": \"$TOKEN\"}"
```

## 4. Run the Full Test Suite
```bash
# Make the test script executable
chmod +x ./scripts/test-mtls-connections.py

# Run the test
python3 ./scripts/test-mtls-connections.py
```

## 5. Check Service Logs for Certificate Loading
```bash
# Check auth service
docker compose logs auth-service | grep -E "(JWT|Certificate|TLS|Loaded)"

# Check gateway
docker compose logs gateway | grep -E "(JWT|Certificate|TLS|Loaded)"

# Check for any SSL/TLS errors
docker compose logs | grep -E "(SSL|TLS|certificate|handshake)" | grep -i error
```

## 6. Test Service-to-Service Communication
```bash
# This tests if gateway can call auth service
curl -X GET http://localhost:8666/health \
  -H "X-API-Key: FJUeDkZRy0uPp7cYtavMsIfwi7weF9-RT7BeOlusqnE"
```

## Expected Results

✅ **Success indicators:**
- All certificates exist in the certs/ directory
- JWT token generation returns a token
- JWT validation returns `{"valid": true, "service": "gateway", ...}`
- No SSL/TLS errors in service logs
- Health checks return successful status

❌ **Failure indicators:**
- Missing certificates
- 500 errors when generating tokens
- SSL handshake errors in logs
- Services can't communicate with each other

## Quick Debug Commands
```bash
# If services aren't starting
docker compose ps
docker compose logs <service-name> --tail 50

# If certificates aren't loading
docker compose exec auth-service ls -la /app/certs/

# Test direct service access (bypass gateway)
docker compose exec gateway curl http://auth-service:8000/health
```

## Next Steps
Once all tests pass:
1. Update todo list to mark Phase 2 as complete
2. Document any issues encountered
3. Proceed to Phase 3: Client migration to Supabase JWTs