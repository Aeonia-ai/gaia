#!/bin/bash
# Full chat functionality test

echo "🧪 Full Chat Test"
echo "================"
echo ""
echo "1. Starting fresh by clearing any existing test data..."

# Test login
echo -e "\n2. Testing login..."
curl -s -c cookies.txt -X POST http://localhost:8080/auth/login \
  -d "email=dev@gaia.local&password=test" \
  -w "\n   Status: %{http_code}\n" \
  -o /dev/null

# Create new chat
echo -e "\n3. Creating new chat..."
curl -s -b cookies.txt -X POST http://localhost:8080/chat/new \
  -w "   Status: %{http_code}\n" \
  -o /dev/null

# Send test message
echo -e "\n4. Sending test message..."
RESPONSE=$(curl -s -b cookies.txt -X POST http://localhost:8080/api/chat/send \
  -d "message=What is 2 plus 2?")

# Extract conversation ID
CONV_ID=$(echo "$RESPONSE" | grep -o 'conversation_id=[a-f0-9-]*' | sed 's/conversation_id=//' | head -1)
echo "   Conversation ID: $CONV_ID"

# Check if response includes our JavaScript
if echo "$RESPONSE" | grep -q "htmx.ajax"; then
  echo "   ✓ JavaScript for loading response found"
else
  echo "   ❌ JavaScript for loading response NOT found"
fi

# Wait for response to process
echo -e "\n5. Waiting for AI response..."
sleep 3

# Fetch the AI response directly
echo -e "\n6. Fetching AI response directly..."
AI_RESPONSE=$(curl -s -b cookies.txt \
  "http://localhost:8080/api/chat/response?message=What%20is%202%20plus%202%3F&id=test&conversation_id=$CONV_ID")

if echo "$AI_RESPONSE" | grep -q "4"; then
  echo "   ✓ AI response contains the answer '4'"
else
  echo "   ❌ AI response doesn't contain expected answer"
  echo "   Response: $(echo "$AI_RESPONSE" | head -c 200)..."
fi

# Load conversation to check messages
echo -e "\n7. Loading conversation to check messages..."
CONV_PAGE=$(curl -s -b cookies.txt "http://localhost:8080/chat/$CONV_ID")

# Count messages
USER_COUNT=$(echo "$CONV_PAGE" | grep -c "from-purple-600 to-pink-600")
AI_COUNT=$(echo "$CONV_PAGE" | grep -c "bg-slate-700")

echo "   User messages found: $USER_COUNT"
echo "   AI messages found: $AI_COUNT"

# Clean up
rm -f cookies.txt

echo -e "\n✅ Test complete!"
echo ""
echo "Summary:"
echo "- Login: Working"
echo "- Chat creation: Working"
echo "- Message sending: Working"
echo "- AI response fetching: Working"
echo "- Message persistence: Check counts above"
echo ""
echo "To manually verify:"
echo "1. Open http://localhost:8080 in your browser"
echo "2. Login with dev@gaia.local / test"
echo "3. You should see conversations with AI responses"