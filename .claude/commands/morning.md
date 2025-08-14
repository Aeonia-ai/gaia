Perform morning development setup:

1. **Git Status**
   ```bash
   git status
   git pull origin main
   ```

2. **Docker Services**
   ```bash
   docker compose ps
   ```
   Verify all services are running

3. **Quick Health Check**
   ```bash
   ./scripts/test.sh --local health
   ```

4. **Recent Test Status**
   Check for any failing tests from previous session:
   ```bash
   ls -la logs/tests/pytest/test-run-*.log | tail -5
   ```

5. **Environment Check**
   - Verify .env file exists
   - Check critical env vars (SUPABASE_SERVICE_KEY, API_KEY)

6. **TODO Status**
   List any pending tasks or known issues

**Provide Summary:**
- Branch status
- Service health
- Any failing tests
- Missing configurations
- Priority tasks for today