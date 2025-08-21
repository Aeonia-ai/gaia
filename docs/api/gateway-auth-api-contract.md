# Gateway Authentication API Contract

This document defines the expected HTTP status codes and response formats for authentication endpoints accessed through the Gateway service.

## API Versions

The Gateway provides authentication endpoints in two API versions with **identical behavior**:
- **v1**: `/api/v1/auth/*` endpoints
- **v0.3**: `/api/v0.3/auth/*` endpoints ✅

✅ **Token Interoperability**: Tokens from v1 login work with v0.3 validate and vice versa.

✅ **Behavioral Identity**: All v0.3 auth endpoints route to the same v1 handlers, ensuring identical responses.

## **POST /api/v1/auth/login** • **POST /api/v0.3/auth/login**

✅ **Both endpoints have identical behavior and responses**

### **✅ Successful Login**
**HTTP Status:** `200 OK`  
**Response Body:**
```json
{
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "token_type": "bearer"
  },
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "email_confirmed_at": "2025-08-08T01:30:00Z",
    "created_at": "2025-08-07T10:00:00Z",
    "user_metadata": {
      "name": "John Doe"
    }
  }
}
```

### **❌ Invalid Credentials**
**HTTP Status:** `401 Unauthorized`  
**Response Body:**
```json
{
  "detail": "Invalid login credentials"
}
```

### **❌ Malformed Request**
**HTTP Status:** `400 Bad Request`  
**Response Body:**
```json
{
  "detail": "Missing required field: email"
}
```
*Or similar validation error message*

### **❌ Email Format Invalid**  
**HTTP Status:** `422 Unprocessable Entity`  
**Response Body:**
```json
{
  "detail": "Invalid email format"
}
```

### **❌ Server Error**
**HTTP Status:** `500 Internal Server Error`  
**Response Body:**
```json
{
  "detail": "Service temporarily unavailable"
}
```

---

## **POST /api/v1/auth/register** • **POST /api/v0.3/auth/register**

✅ **Both endpoints have identical behavior and responses**

### **✅ Successful Registration**
**HTTP Status:** `200 OK`  
**Response Body:**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440001", 
    "email": "newuser@example.com",
    "email_confirmed_at": null,
    "created_at": "2025-08-08T01:30:00Z",
    "confirmation_sent_at": "2025-08-08T01:30:00Z"
  }
}
```

### **❌ Email Already Registered**
**HTTP Status:** `400 Bad Request`  
**Response Body:**
```json
{
  "detail": "A user with this email address has already been registered"
}
```

### **❌ Password Too Weak**
**HTTP Status:** `422 Unprocessable Entity`  
**Response Body:**
```json
{
  "detail": "Password must be at least 6 characters"
}
```

### **❌ Invalid Email Format**
**HTTP Status:** `422 Unprocessable Entity`  
**Response Body:**
```json
{
  "detail": "Invalid email format"
}
```

---

## **POST /api/v1/auth/validate** • **POST /api/v0.3/auth/validate**

✅ **Both endpoints have identical behavior and responses**

✅ **Cross-version token validation**: v1 tokens work with v0.3 validate, v0.3 tokens work with v1 validate

### **✅ Valid JWT Token**
**HTTP Status:** `200 OK`  
**Response Body:**
```json
{
  "valid": true,
  "auth_type": "jwt",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": null
}
```

### **❌ Invalid/Expired JWT**
**HTTP Status:** `200 OK` *(validation endpoint returns 200 with valid=false)*  
**Response Body:**
```json
{
  "valid": false,
  "auth_type": null,
  "user_id": null,
  "error": "Token expired"
}
```

---

## **POST /api/v1/auth/refresh** • **POST /api/v0.3/auth/refresh**

✅ **Both endpoints have identical behavior and responses**

### **✅ Successful Token Refresh**
**HTTP Status:** `200 OK`  
**Response Body:**
```json
{
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "token_type": "bearer"
  }
}
```

### **❌ Invalid Refresh Token**
**HTTP Status:** `401 Unauthorized`  
**Response Body:**
```json
{
  "detail": "Invalid refresh token"
}
```

---

## **Client Implementation Guidelines:**

### **Error Handling:**
```javascript
// Works with both v1 and v0.3 endpoints
try {
  const response = await fetch('/api/v1/auth/login', { // or '/api/v0.3/auth/login'
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (response.status === 200) {
    const data = await response.json();
    // Store access_token, redirect to app
    localStorage.setItem('access_token', data.session.access_token);
  } else if (response.status === 401) {
    // Show "Invalid credentials" message
    showError('Invalid email or password');
  } else if (response.status === 400) {
    // Show validation error
    const error = await response.json();
    showError(error.detail);
  } else {
    // Server error - show generic message
    showError('Login temporarily unavailable');
  }
} catch (error) {
  // Network error
  showError('Connection failed');
}
```

### **Success Flow:**
1. Store `access_token` securely
2. Use token in `Authorization: Bearer <token>` header for subsequent requests
3. Redirect user to authenticated area
4. Handle token refresh before expiry using the refresh token

### **Security Considerations:**
- Always use HTTPS in production
- Store tokens securely (not in localStorage for sensitive apps)
- Implement proper token refresh logic before expiry
- Clear tokens on logout
- Validate token on app startup

## **HTTP Status Code Reference:**

| Status Code | Meaning | When to Use |
|-------------|---------|-------------|
| 200 | OK | Successful authentication/operation |
| 400 | Bad Request | Malformed request, missing fields |
| 401 | Unauthorized | Invalid credentials, expired tokens |
| 422 | Unprocessable Entity | Valid format but invalid data |
| 500 | Internal Server Error | Server/database errors only |

This contract ensures predictable, standards-compliant authentication behavior through the Gateway service.