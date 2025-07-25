#\!/bin/bash

# Test dev login
echo "Testing dev login..."
curl -X POST http://localhost:8080/auth/dev-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=jason@aeonia.ai" \
  -c cookies.txt \
  -L \
  -v

echo -e "\n\nChecking if we can access /chat..."
curl http://localhost:8080/chat \
  -b cookies.txt \
  -H "Accept: text/html" \
  -v

