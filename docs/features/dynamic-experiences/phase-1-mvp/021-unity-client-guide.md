# Unity Client Implementation Guide: V0.3 Streaming Conversation ID

**Target Unity Versions**: 2022.3 LTS and newer
**Platforms**: PC, Mac, Android, iOS, VR (Quest, PICO, Vive)
**Performance Target**: Sub-100ms conversation_id extraction
**VR/AR Optimized**: ✅ Frame-rate friendly patterns

## Overview

This guide provides Unity-specific implementation patterns for V0.3 streaming conversation_id delivery, addressing Unity's unique challenges like main thread requirements, GameObject lifecycle, and VR/AR performance constraints.

## Quick Start: Minimal Implementation

### 1. Basic Conversation Manager

```csharp
using System;
using System.Collections;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;
using Newtonsoft.Json;

[System.Serializable]
public class StreamEvent
{
    public string type;
    public string conversation_id;
    public string model;
    public long timestamp;
    public Delta delta;
}

[System.Serializable]
public class Delta
{
    public string content;
}

[System.Serializable]
public class ChatRequest
{
    public string message;
    public string model = "claude-3-5-sonnet-20241022";
    public bool stream = true;
    public string conversation_id;
}

public class GaiaConversationManager : MonoBehaviour
{
    [Header("Configuration")]
    public string baseUrl = "http://localhost:8666";
    public string apiKey = "your-api-key";

    [Header("Current Conversation")]
    public string currentConversationId;

    private HttpClient httpClient;

    void Start()
    {
        httpClient = new HttpClient();
        httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);
    }

    void OnDestroy()
    {
        httpClient?.Dispose();
    }

    public async Task<string> SendMessage(string message, string conversationId = null)
    {
        try
        {
            var request = new ChatRequest
            {
                message = message,
                conversation_id = conversationId ?? currentConversationId
            };

            var json = JsonConvert.SerializeObject(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            using var response = await httpClient.PostAsync($"{baseUrl}/api/v0.3/chat", content);
            response.EnsureSuccessStatusCode();

            // Extract conversation_id from first event
            var extractedId = await ExtractConversationIdFromStream(response);

            if (!string.IsNullOrEmpty(extractedId))
            {
                currentConversationId = extractedId;
                Debug.Log($"💬 Conversation ID: {currentConversationId}");
            }

            return currentConversationId;
        }
        catch (Exception ex)
        {
            Debug.LogError($"❌ Chat error: {ex.Message}");
            return null;
        }
    }

    private async Task<string> ExtractConversationIdFromStream(HttpResponseMessage response)
    {
        using var stream = await response.Content.ReadAsStreamAsync();
        using var reader = new System.IO.StreamReader(stream);

        // Unity VR optimization: Only read first few chunks for conversation_id
        int chunksRead = 0;
        const int maxChunksForId = 3;

        string line;
        while ((line = await reader.ReadLineAsync()) != null && chunksRead < maxChunksForId)
        {
            if (line.StartsWith("data: "))
            {
                var eventData = line.Substring(6);
                chunksRead++;

                if (eventData == "[DONE]") break;

                try
                {
                    var streamEvent = JsonConvert.DeserializeObject<StreamEvent>(eventData);

                    if (streamEvent.type == "metadata" && !string.IsNullOrEmpty(streamEvent.conversation_id))
                    {
                        Debug.Log($"✅ Extracted conversation_id in chunk {chunksRead}");
                        return streamEvent.conversation_id;
                    }
                }
                catch (JsonException ex)
                {
                    Debug.LogWarning($"⚠️ Failed to parse stream event: {ex.Message}");
                }
            }
        }

        Debug.LogWarning("⚠️ No conversation_id found in first few chunks");
        return null;
    }
}
```

## Advanced Unity Patterns

### 2. Thread-Safe Conversation Manager with Coroutines

```csharp
using System.Collections;
using System.Collections.Concurrent;
using System.Threading;
using UnityEngine;

public class ThreadSafeConversationManager : MonoBehaviour
{
    [Header("Configuration")]
    public string baseUrl = "http://localhost:8666";
    public string apiKey = "your-api-key";

    [Header("Performance")]
    [Range(1, 10)]
    public int maxConcurrentRequests = 3;

    [Header("Current State")]
    public string currentConversationId;
    public bool isProcessing = false;

    // Thread-safe collections
    private readonly ConcurrentQueue<ChatMessage> messageQueue = new();
    private readonly ConcurrentDictionary<string, string> conversationCache = new();

    private HttpClient httpClient;
    private CancellationTokenSource cancellationTokenSource;
    private SemaphoreSlim requestSemaphore;

    [System.Serializable]
    public class ChatMessage
    {
        public string id;
        public string content;
        public string conversationId;
        public bool isResponse;
        public System.DateTime timestamp;
    }

    void Start()
    {
        httpClient = new HttpClient();
        httpClient.DefaultRequestHeaders.Add("X-API-Key", apiKey);

        cancellationTokenSource = new CancellationTokenSource();
        requestSemaphore = new SemaphoreSlim(maxConcurrentRequests, maxConcurrentRequests);

        // Start message processing coroutine
        StartCoroutine(ProcessMessageQueue());
    }

    void OnDestroy()
    {
        cancellationTokenSource?.Cancel();
        httpClient?.Dispose();
        requestSemaphore?.Dispose();
    }

    /// <summary>
    /// Thread-safe method to send a message (can be called from any thread)
    /// </summary>
    public void QueueMessage(string message, string conversationId = null)
    {
        var chatMessage = new ChatMessage
        {
            id = System.Guid.NewGuid().ToString(),
            content = message,
            conversationId = conversationId ?? currentConversationId,
            isResponse = false,
            timestamp = System.DateTime.Now
        };

        messageQueue.Enqueue(chatMessage);
        Debug.Log($"📝 Queued message: {message.Substring(0, Mathf.Min(50, message.Length))}...");
    }

    /// <summary>
    /// Coroutine that processes messages on main thread
    /// </summary>
    private IEnumerator ProcessMessageQueue()
    {
        while (!cancellationTokenSource.Token.IsCancellationRequested)
        {
            if (messageQueue.TryDequeue(out ChatMessage message))
            {
                isProcessing = true;
                yield return StartCoroutine(ProcessSingleMessage(message));
                isProcessing = false;
            }

            yield return new WaitForSeconds(0.1f); // Prevent busy waiting
        }
    }

    /// <summary>
    /// Process a single message using Unity coroutines
    /// </summary>
    private IEnumerator ProcessSingleMessage(ChatMessage message)
    {
        Debug.Log($"🔄 Processing message: {message.id}");

        // Use Task.Run for HTTP operations, then return to main thread
        Task<string> conversationTask = Task.Run(async () =>
        {
            try
            {
                await requestSemaphore.WaitAsync(cancellationTokenSource.Token);
                return await SendMessageInternal(message.content, message.conversationId);
            }
            finally
            {
                requestSemaphore.Release();
            }
        });

        // Wait for completion without blocking main thread
        yield return new WaitUntil(() => conversationTask.IsCompleted);

        if (conversationTask.IsCompletedSuccessfully)
        {
            var conversationId = conversationTask.Result;
            if (!string.IsNullOrEmpty(conversationId))
            {
                currentConversationId = conversationId;
                conversationCache.TryAdd(message.id, conversationId);

                // Trigger Unity events on main thread
                OnConversationUpdated?.Invoke(conversationId);
                Debug.Log($"✅ Message processed: {message.id} → {conversationId}");
            }
        }
        else
        {
            Debug.LogError($"❌ Message failed: {message.id} → {conversationTask.Exception?.GetBaseException().Message}");
            OnConversationError?.Invoke(message.id, conversationTask.Exception?.GetBaseException().Message);
        }
    }

    /// <summary>
    /// Internal async method for HTTP operations
    /// </summary>
    private async Task<string> SendMessageInternal(string message, string conversationId)
    {
        try
        {
            var request = new ChatRequest
            {
                message = message,
                conversation_id = conversationId
            };

            var json = JsonConvert.SerializeObject(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            using var response = await httpClient.PostAsync(
                $"{baseUrl}/api/v0.3/chat",
                content,
                cancellationTokenSource.Token
            );

            response.EnsureSuccessStatusCode();
            return await ExtractConversationIdOptimized(response);
        }
        catch (OperationCanceledException)
        {
            Debug.Log("🛑 Request cancelled");
            return null;
        }
        catch (Exception ex)
        {
            Debug.LogError($"❌ HTTP error: {ex.Message}");
            return null;
        }
    }

    /// <summary>
    /// VR-optimized conversation_id extraction (minimal processing)
    /// </summary>
    private async Task<string> ExtractConversationIdOptimized(HttpResponseMessage response)
    {
        using var stream = await response.Content.ReadAsStreamAsync();
        using var reader = new System.IO.StreamReader(stream);

        // VR Performance: Read only first 512 bytes for conversation_id
        char[] buffer = new char[512];
        int bytesRead = await reader.ReadAsync(buffer, 0, buffer.Length);
        string firstChunk = new string(buffer, 0, bytesRead);

        // Look for metadata event in first chunk
        var lines = firstChunk.Split('\n');
        foreach (var line in lines)
        {
            if (line.StartsWith("data: "))
            {
                try
                {
                    var eventData = line.Substring(6);
                    var streamEvent = JsonConvert.DeserializeObject<StreamEvent>(eventData);

                    if (streamEvent?.type == "metadata" && !string.IsNullOrEmpty(streamEvent.conversation_id))
                    {
                        return streamEvent.conversation_id;
                    }
                }
                catch (JsonException)
                {
                    continue; // Skip malformed events
                }
            }
        }

        return null;
    }

    // Unity Events (assign in Inspector)
    public UnityEngine.Events.UnityEvent<string> OnConversationUpdated;
    public UnityEngine.Events.UnityEvent<string, string> OnConversationError;
}
```

### 3. VR/AR Optimized Manager with Object Pooling

```csharp
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Pool;

/// <summary>
/// VR/AR optimized conversation manager with object pooling and memory management
/// </summary>
public class VRConversationManager : MonoBehaviour
{
    [Header("VR Configuration")]
    [Range(60, 120)]
    public int targetFrameRate = 90; // VR frame rate target

    [Range(1, 5)]
    public int maxSimultaneousRequests = 2; // Limit for VR performance

    [Header("Memory Management")]
    [Range(10, 100)]
    public int maxCachedConversations = 50;

    [Range(1, 10)]
    public int poolSize = 5; // Object pool size

    // Object pooling for memory efficiency
    private ObjectPool<ChatRequest> requestPool;
    private ObjectPool<StreamEvent> eventPool;

    // Conversation cache with LRU eviction
    private readonly Dictionary<string, ConversationData> conversationCache = new();
    private readonly Queue<string> conversationLRU = new();

    [System.Serializable]
    public class ConversationData
    {
        public string id;
        public string title;
        public System.DateTime lastAccessed;
        public List<string> messageHistory;
        public bool isPersistent; // Don't evict important conversations
    }

    void Start()
    {
        // Set VR frame rate
        Application.targetFrameRate = targetFrameRate;
        QualitySettings.vSyncCount = 0; // Disable VSync for VR

        // Initialize object pools
        requestPool = new ObjectPool<ChatRequest>(
            createFunc: () => new ChatRequest(),
            actionOnGet: req => ResetRequest(req),
            actionOnRelease: req => { }, // No cleanup needed
            actionOnDestroy: req => { },
            collectionCheck: false,
            defaultCapacity: poolSize,
            maxCapacity: poolSize * 2
        );

        eventPool = new ObjectPool<StreamEvent>(
            createFunc: () => new StreamEvent(),
            actionOnGet: evt => ResetEvent(evt),
            actionOnRelease: evt => { },
            actionOnDestroy: evt => { },
            collectionCheck: false,
            defaultCapacity: poolSize,
            maxCapacity: poolSize * 2
        );

        Debug.Log($"🥽 VR Conversation Manager initialized (Target FPS: {targetFrameRate})");
    }

    /// <summary>
    /// VR-friendly message sending with frame rate protection
    /// </summary>
    public void SendMessageVR(string message, string conversationId = null)
    {
        // Frame rate protection: defer if frame time is high
        if (Time.unscaledDeltaTime > 1.0f / (targetFrameRate * 0.8f))
        {
            Debug.Log("⏱️ Deferring request due to frame rate protection");
            StartCoroutine(DeferredMessageSend(message, conversationId));
            return;
        }

        StartCoroutine(SendMessageCoroutine(message, conversationId));
    }

    private IEnumerator DeferredMessageSend(string message, string conversationId)
    {
        // Wait for frame rate to stabilize
        yield return new WaitUntil(() => Time.unscaledDeltaTime <= 1.0f / (targetFrameRate * 0.9f));
        yield return StartCoroutine(SendMessageCoroutine(message, conversationId));
    }

    private IEnumerator SendMessageCoroutine(string message, string conversationId)
    {
        // Get pooled request object
        var request = requestPool.Get();
        request.message = message;
        request.conversation_id = conversationId;

        try
        {
            // Process in chunks to maintain frame rate
            yield return StartCoroutine(ProcessRequestInChunks(request));
        }
        finally
        {
            // Return to pool
            requestPool.Release(request);
        }
    }

    private IEnumerator ProcessRequestInChunks(ChatRequest request)
    {
        const int maxProcessingTimeMs = 2; // Max 2ms per frame for VR

        var stopwatch = System.Diagnostics.Stopwatch.StartNew();

        // Chunk 1: Prepare HTTP request
        var httpTask = PrepareHttpRequest(request);
        yield return new WaitUntil(() => httpTask.IsCompleted);

        if (stopwatch.ElapsedMilliseconds > maxProcessingTimeMs)
        {
            yield return null; // Yield frame
            stopwatch.Restart();
        }

        // Chunk 2: Send request and get response
        if (httpTask.IsCompletedSuccessfully)
        {
            var response = httpTask.Result;
            var extractTask = ExtractConversationIdFast(response);
            yield return new WaitUntil(() => extractTask.IsCompleted);

            if (extractTask.IsCompletedSuccessfully)
            {
                UpdateConversationCache(extractTask.Result, request.message);
            }
        }

        stopwatch.Stop();
    }

    /// <summary>
    /// Ultra-fast conversation_id extraction for VR
    /// </summary>
    private async Task<string> ExtractConversationIdFast(HttpResponseMessage response)
    {
        // VR Ultra-optimization: Read only first 256 bytes
        using var stream = await response.Content.ReadAsStreamAsync();
        byte[] buffer = new byte[256];
        int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);

        string chunk = System.Text.Encoding.UTF8.GetString(buffer, 0, bytesRead);

        // Fast string parsing without JSON deserialization
        int dataIndex = chunk.IndexOf("data: ");
        if (dataIndex >= 0)
        {
            int conversationIndex = chunk.IndexOf("\"conversation_id\":", dataIndex);
            if (conversationIndex >= 0)
            {
                int startQuote = chunk.IndexOf("\"", conversationIndex + 18);
                int endQuote = chunk.IndexOf("\"", startQuote + 1);

                if (startQuote >= 0 && endQuote >= 0)
                {
                    return chunk.Substring(startQuote + 1, endQuote - startQuote - 1);
                }
            }
        }

        return null;
    }

    /// <summary>
    /// Memory-efficient conversation caching with LRU eviction
    /// </summary>
    private void UpdateConversationCache(string conversationId, string lastMessage)
    {
        if (string.IsNullOrEmpty(conversationId)) return;

        // Update existing or create new
        if (conversationCache.ContainsKey(conversationId))
        {
            var existing = conversationCache[conversationId];
            existing.lastAccessed = System.DateTime.Now;
            existing.messageHistory.Add(lastMessage);

            // Move to end of LRU queue
            var tempQueue = new Queue<string>();
            while (conversationLRU.Count > 0)
            {
                var id = conversationLRU.Dequeue();
                if (id != conversationId)
                    tempQueue.Enqueue(id);
            }
            while (tempQueue.Count > 0)
                conversationLRU.Enqueue(tempQueue.Dequeue());
            conversationLRU.Enqueue(conversationId);
        }
        else
        {
            // Add new conversation
            var newConversation = new ConversationData
            {
                id = conversationId,
                title = lastMessage.Length > 30 ? lastMessage.Substring(0, 30) + "..." : lastMessage,
                lastAccessed = System.DateTime.Now,
                messageHistory = new List<string> { lastMessage },
                isPersistent = false
            };

            conversationCache[conversationId] = newConversation;
            conversationLRU.Enqueue(conversationId);
        }

        // Evict old conversations if cache is full
        while (conversationCache.Count > maxCachedConversations)
        {
            if (conversationLRU.Count > 0)
            {
                var oldestId = conversationLRU.Dequeue();
                if (conversationCache.TryGetValue(oldestId, out var oldest) && !oldest.isPersistent)
                {
                    conversationCache.Remove(oldestId);
                    Debug.Log($"🗑️ Evicted conversation: {oldestId}");
                }
            }
            else
            {
                break; // Safety check
            }
        }
    }

    // Object pool reset methods
    private void ResetRequest(ChatRequest request)
    {
        request.message = null;
        request.conversation_id = null;
        request.model = "claude-3-5-sonnet-20241022";
        request.stream = true;
    }

    private void ResetEvent(StreamEvent evt)
    {
        evt.type = null;
        evt.conversation_id = null;
        evt.model = null;
        evt.timestamp = 0;
        evt.delta = null;
    }

    // Public API for VR applications
    public ConversationData GetConversation(string conversationId)
    {
        return conversationCache.TryGetValue(conversationId, out var conversation) ? conversation : null;
    }

    public void SetConversationPersistent(string conversationId, bool persistent)
    {
        if (conversationCache.TryGetValue(conversationId, out var conversation))
        {
            conversation.isPersistent = persistent;
        }
    }

    public List<ConversationData> GetRecentConversations(int count = 10)
    {
        var recent = new List<ConversationData>();
        var sorted = new List<ConversationData>(conversationCache.Values);
        sorted.Sort((a, b) => b.lastAccessed.CompareTo(a.lastAccessed));

        for (int i = 0; i < Mathf.Min(count, sorted.Count); i++)
        {
            recent.Add(sorted[i]);
        }

        return recent;
    }

    // Performance monitoring
    void Update()
    {
        // Monitor frame rate in VR
        if (Time.unscaledDeltaTime > 1.0f / (targetFrameRate * 0.7f))
        {
            Debug.LogWarning($"⚠️ Frame rate drop detected: {1.0f / Time.unscaledDeltaTime:F1} FPS");
        }
    }

    void OnGUI()
    {
        if (Debug.isDebugBuild)
        {
            GUILayout.Label($"FPS: {1.0f / Time.unscaledDeltaTime:F1}");
            GUILayout.Label($"Conversations: {conversationCache.Count}/{maxCachedConversations}");
            GUILayout.Label($"Pool Usage: Requests={requestPool.CountActive}/{poolSize}, Events={eventPool.CountActive}/{poolSize}");
        }
    }
}
```

## Unity-Specific Best Practices

### 4. Error Handling and Resilience

```csharp
public class ResilientConversationManager : MonoBehaviour
{
    [Header("Resilience Configuration")]
    [Range(1, 5)]
    public int maxRetries = 3;

    [Range(0.5f, 5.0f)]
    public float baseRetryDelay = 1.0f;

    [Range(5, 60)]
    public int timeoutSeconds = 30;

    /// <summary>
    /// Robust message sending with exponential backoff
    /// </summary>
    public async Task<string> SendMessageRobust(string message, string conversationId = null)
    {
        for (int attempt = 0; attempt < maxRetries; attempt++)
        {
            try
            {
                using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));

                var result = await SendMessageWithTimeout(message, conversationId, cts.Token);

                if (!string.IsNullOrEmpty(result))
                {
                    if (attempt > 0)
                    {
                        Debug.Log($"✅ Succeeded on retry {attempt + 1}");
                    }
                    return result;
                }
            }
            catch (TaskCanceledException)
            {
                Debug.LogWarning($"⏱️ Timeout on attempt {attempt + 1}");
            }
            catch (HttpRequestException ex)
            {
                Debug.LogWarning($"🌐 Network error on attempt {attempt + 1}: {ex.Message}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"❌ Unexpected error on attempt {attempt + 1}: {ex.Message}");

                // Don't retry on unexpected errors
                break;
            }

            // Exponential backoff
            if (attempt < maxRetries - 1)
            {
                float delay = baseRetryDelay * Mathf.Pow(2, attempt);
                Debug.Log($"⏳ Retrying in {delay:F1}s...");
                await Task.Delay(TimeSpan.FromSeconds(delay));
            }
        }

        // Final fallback: use local conversation ID
        var fallbackId = $"local-{System.Guid.NewGuid().ToString("N")[..8]}";
        Debug.LogWarning($"🔄 Using fallback conversation ID: {fallbackId}");
        return fallbackId;
    }

    /// <summary>
    /// Network health monitoring
    /// </summary>
    public void MonitorNetworkHealth()
    {
        StartCoroutine(NetworkHealthCheck());
    }

    private IEnumerator NetworkHealthCheck()
    {
        while (true)
        {
            if (Application.internetReachability == NetworkReachability.NotReachable)
            {
                Debug.LogWarning("📡 No internet connection");
                OnNetworkUnavailable?.Invoke();
            }
            else
            {
                // Quick ping to verify server availability
                StartCoroutine(PingServer());
            }

            yield return new WaitForSeconds(10f); // Check every 10 seconds
        }
    }

    private IEnumerator PingServer()
    {
        using var ping = new UnityEngine.Networking.UnityWebRequest($"{baseUrl}/health");
        ping.timeout = 5;

        yield return ping.SendWebRequest();

        if (ping.result != UnityEngine.Networking.UnityWebRequest.Result.Success)
        {
            Debug.LogWarning($"🏥 Server health check failed: {ping.error}");
            OnServerUnavailable?.Invoke();
        }
    }

    // Unity Events for UI integration
    public UnityEngine.Events.UnityEvent OnNetworkUnavailable;
    public UnityEngine.Events.UnityEvent OnServerUnavailable;
}
```

### 5. Scene Persistence and State Management

```csharp
using UnityEngine;

/// <summary>
/// Conversation state that persists across scene changes
/// </summary>
public class PersistentConversationState : MonoBehaviour
{
    [Header("Persistence Configuration")]
    public bool saveToPlayerPrefs = true;
    public bool encryptSavedData = false;

    // Singleton pattern for scene persistence
    public static PersistentConversationState Instance { get; private set; }

    [System.Serializable]
    public class ConversationState
    {
        public string currentConversationId;
        public string[] recentConversationIds;
        public System.DateTime lastActivity;
        public string userName;
        public int messageCount;
    }

    [SerializeField] private ConversationState state;

    void Awake()
    {
        // Singleton enforcement
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        DontDestroyOnLoad(gameObject);

        LoadState();
    }

    void OnApplicationPause(bool pauseStatus)
    {
        if (pauseStatus)
        {
            SaveState(); // Save when app goes to background
        }
    }

    void OnApplicationFocus(bool hasFocus)
    {
        if (!hasFocus)
        {
            SaveState(); // Save when app loses focus
        }
    }

    public void UpdateConversationId(string conversationId)
    {
        if (string.IsNullOrEmpty(conversationId)) return;

        state.currentConversationId = conversationId;
        state.lastActivity = System.DateTime.Now;
        state.messageCount++;

        // Update recent conversations list
        var recentList = new System.Collections.Generic.List<string>(state.recentConversationIds ?? new string[0]);
        recentList.RemoveAll(id => id == conversationId); // Remove if already exists
        recentList.Insert(0, conversationId); // Add to front

        // Keep only last 10 conversations
        if (recentList.Count > 10)
        {
            recentList.RemoveRange(10, recentList.Count - 10);
        }

        state.recentConversationIds = recentList.ToArray();

        // Auto-save every 10 messages
        if (state.messageCount % 10 == 0)
        {
            SaveState();
        }
    }

    private void LoadState()
    {
        if (saveToPlayerPrefs && PlayerPrefs.HasKey("ConversationState"))
        {
            try
            {
                string json = PlayerPrefs.GetString("ConversationState");

                if (encryptSavedData)
                {
                    json = DecryptString(json);
                }

                state = JsonUtility.FromJson<ConversationState>(json);
                Debug.Log($"📂 Loaded conversation state: {state.currentConversationId}");
            }
            catch (System.Exception ex)
            {
                Debug.LogWarning($"⚠️ Failed to load conversation state: {ex.Message}");
                state = new ConversationState();
            }
        }
        else
        {
            state = new ConversationState();
        }
    }

    private void SaveState()
    {
        if (!saveToPlayerPrefs) return;

        try
        {
            string json = JsonUtility.ToJson(state);

            if (encryptSavedData)
            {
                json = EncryptString(json);
            }

            PlayerPrefs.SetString("ConversationState", json);
            PlayerPrefs.Save();

            Debug.Log($"💾 Saved conversation state: {state.currentConversationId}");
        }
        catch (System.Exception ex)
        {
            Debug.LogError($"❌ Failed to save conversation state: {ex.Message}");
        }
    }

    // Simple XOR encryption for demonstration (use proper encryption in production)
    private string EncryptString(string text)
    {
        var key = System.Text.Encoding.UTF8.GetBytes("MySecretKey12345"); // Use proper key management
        var data = System.Text.Encoding.UTF8.GetBytes(text);

        for (int i = 0; i < data.Length; i++)
        {
            data[i] = (byte)(data[i] ^ key[i % key.Length]);
        }

        return System.Convert.ToBase64String(data);
    }

    private string DecryptString(string encryptedText)
    {
        var key = System.Text.Encoding.UTF8.GetBytes("MySecretKey12345");
        var data = System.Convert.FromBase64String(encryptedText);

        for (int i = 0; i < data.Length; i++)
        {
            data[i] = (byte)(data[i] ^ key[i % key.Length]);
        }

        return System.Text.Encoding.UTF8.GetString(data);
    }

    // Public API
    public string GetCurrentConversationId() => state.currentConversationId;
    public string[] GetRecentConversationIds() => state.recentConversationIds ?? new string[0];
    public System.DateTime GetLastActivity() => state.lastActivity;
    public int GetMessageCount() => state.messageCount;

    public void ClearState()
    {
        state = new ConversationState();
        SaveState();
        Debug.Log("🗑️ Conversation state cleared");
    }
}
```

## Performance Optimization Tips

### Unity-Specific Performance Considerations

1. **Main Thread Management**
   ```csharp
   // ❌ Don't block main thread
   var result = await httpClient.PostAsync(url, content); // Blocks main thread

   // ✅ Use coroutines for async operations
   yield return StartCoroutine(SendMessageCoroutine(message));
   ```

2. **Memory Management**
   ```csharp
   // ✅ Use object pooling for frequent allocations
   private ObjectPool<StreamEvent> eventPool;

   // ✅ Dispose HttpClient properly
   void OnDestroy() { httpClient?.Dispose(); }
   ```

3. **VR Frame Rate Protection**
   ```csharp
   // ✅ Monitor frame time and defer heavy operations
   if (Time.unscaledDeltaTime > 1.0f / (targetFrameRate * 0.8f))
   {
       StartCoroutine(DeferredOperation());
   }
   ```

4. **Network Optimization**
   ```csharp
   // ✅ Limit conversation_id extraction to first chunk
   const int maxBytesForConversationId = 512;
   byte[] buffer = new byte[maxBytesForConversationId];
   ```

## Common Unity Challenges & Solutions

### Challenge 1: Threading Issues
**Problem**: HTTP operations on background threads can't access Unity objects
**Solution**: Use coroutines and Task.Run pattern
```csharp
yield return StartCoroutine(ProcessAsync(() => Task.Run(HttpOperation)));
```

### Challenge 2: Scene Loading
**Problem**: Conversation state lost when changing scenes
**Solution**: Singleton pattern with DontDestroyOnLoad
```csharp
DontDestroyOnLoad(gameObject);
```

### Challenge 3: VR Performance
**Problem**: Network operations cause frame drops
**Solution**: Chunked processing and frame time monitoring
```csharp
if (stopwatch.ElapsedMilliseconds > maxFrameTimeMs) { yield return null; }
```

### Challenge 4: Mobile Backgrounding
**Problem**: App suspension interrupts conversations
**Solution**: Save state on pause and implement reconnection
```csharp
void OnApplicationPause(bool pauseStatus) { if (pauseStatus) SaveState(); }
```

## Integration with Unity UI

### Simple UI Integration Example

```csharp
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class ConversationUI : MonoBehaviour
{
    [Header("UI References")]
    public TMP_InputField messageInput;
    public Button sendButton;
    public TextMeshProUGUI conversationDisplay;
    public TextMeshProUGUI conversationIdLabel;

    private GaiaConversationManager conversationManager;

    void Start()
    {
        conversationManager = FindObjectOfType<GaiaConversationManager>();
        sendButton.onClick.AddListener(SendMessage);

        // Enable send on Enter key
        messageInput.onEndEdit.AddListener(OnInputEndEdit);
    }

    private void OnInputEndEdit(string text)
    {
        if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter))
        {
            SendMessage();
        }
    }

    private async void SendMessage()
    {
        string message = messageInput.text.Trim();
        if (string.IsNullOrEmpty(message)) return;

        // Disable UI during processing
        sendButton.interactable = false;
        messageInput.interactable = false;

        try
        {
            // Add user message to display
            conversationDisplay.text += $"\n<color=blue>You:</color> {message}";
            messageInput.text = "";

            // Send message and get conversation ID
            string conversationId = await conversationManager.SendMessage(message);

            if (!string.IsNullOrEmpty(conversationId))
            {
                conversationIdLabel.text = $"Conversation: {conversationId[..8]}...";
                conversationDisplay.text += $"\n<color=green>✅ Message sent (ID: {conversationId[..8]}...)</color>";
            }
            else
            {
                conversationDisplay.text += $"\n<color=red>❌ Failed to send message</color>";
            }
        }
        finally
        {
            // Re-enable UI
            sendButton.interactable = true;
            messageInput.interactable = true;
            messageInput.Select();
        }
    }
}
```

This comprehensive Unity implementation guide addresses the key challenges Unity developers face when implementing V0.3 streaming conversation_id delivery, with special attention to VR/AR performance requirements and Unity-specific patterns.