"""
HTML templates for mocking web pages in browser tests.
"""

CHAT_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GAIA Chat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        #chat-container { max-width: 800px; margin: 0 auto; }
        #conversation-list { border: 1px solid #ddd; padding: 10px; min-height: 100px; margin-bottom: 20px; }
        #messages { border: 1px solid #ddd; padding: 10px; min-height: 300px; margin-bottom: 20px; }
        #chat-form { display: flex; gap: 10px; }
        #chat-form textarea { flex: 1; min-height: 60px; padding: 10px; }
        #chat-form button { padding: 10px 20px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user-message { background: #e3f2fd; text-align: right; }
        .assistant-message { background: #f5f5f5; }
    </style>
</head>
<body>
    <div id="chat-container">
        <h1>GAIA Chat</h1>
        <div id="conversation-list">
            <div class="conversation-item" data-id="new">New Conversation</div>
        </div>
        <div id="messages"></div>
        <form id="chat-form">
            <textarea name="message" placeholder="Type your message here..."></textarea>
            <button type="submit">Send</button>
        </form>
    </div>
    <script>
        // Simple mock behavior for tests
        document.getElementById('chat-form').onsubmit = function(e) {
            e.preventDefault();
            const textarea = this.querySelector('textarea');
            const message = textarea.value;
            if (message) {
                // Add user message
                const messagesDiv = document.getElementById('messages');
                messagesDiv.innerHTML += '<div class="message user-message">' + message + '</div>';
                // Clear input
                textarea.value = '';
                // Mock assistant response
                setTimeout(() => {
                    messagesDiv.innerHTML += '<div class="message assistant-message">This is a test response.</div>';
                }, 100);
            }
            return false;
        };
    </script>
</body>
</html>
"""

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GAIA - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .login-container { width: 100%; max-width: 400px; padding: 20px; }
        .login-form { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .error { color: red; margin-top: 10px; display: none; }
    </style>
</head>
<body>
    <div class="login-container">
        <form class="login-form" action="/auth/login" method="post">
            <h1>Login to GAIA</h1>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Sign In</button>
            <div class="error"></div>
        </form>
    </div>
</body>
</html>
"""

REGISTER_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>GAIA - Register</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .register-container { width: 100%; max-width: 400px; padding: 20px; }
        .register-form { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #218838; }
        .error { color: red; margin-top: 10px; display: none; }
        .login-link { text-align: center; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="register-container">
        <form class="register-form" action="/auth/register" method="post">
            <h1>Create Account</h1>
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <div class="form-group">
                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
            </div>
            <button type="submit">Register</button>
            <div class="error"></div>
            <div class="login-link">
                Already have an account? <a href="/login">Sign in</a>
            </div>
        </form>
    </div>
</body>
</html>
"""

ERROR_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .error-container { text-align: center; padding: 20px; }
        h1 { color: #dc3545; }
        .error-message { margin: 20px 0; color: #666; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Error</h1>
        <div class="error-message">{message}</div>
        <a href="/">Go Home</a>
    </div>
</body>
</html>
"""