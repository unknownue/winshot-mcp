# MCP (Model-Client Protocol) Specification

## Overview

MCP is a simple protocol for communication between clients and Large Language Models (LLMs). The protocol is implemented over WebSocket, uses JSON as the message format, and supports real-time bidirectional communication.

## Message Format

All MCP messages should use JSON format and contain the following basic fields:

### Request Message

```json
{
  "id": "Unique message ID",
  "type": "Message type",
  "content": "Message content"
}
```

### Response Message

```json
{
  "id": "Unique response ID",
  "request_id": "Corresponding request ID",
  "type": "Response type",
  "content": "Response content"
}
```

## Message Types

The MCP protocol supports the following message types:

1. **text** - Plain text message
2. **function_call** - Function call request
3. **function_result** - Function call result
4. **error** - Error message
5. **status** - Status update
6. **window_list_request** - Request list of available windows
7. **window_list_response** - Response with available windows
8. **window_screenshot_request** - Request a screenshot of a specific window
9. **window_screenshot_response** - Response with window screenshot data

## Example Interactions

### Text Message Example

**Client Request:**
```json
{
  "id": "client-msg-1",
  "type": "text",
  "content": "Hello, model! How are you today?"
}
```

**Server Response:**
```json
{
  "id": "model-resp-1",
  "request_id": "client-msg-1",
  "type": "text",
  "content": "Hello! I'm functioning well today. How can I assist you?"
}
```

### Function Call Example

**Client Request:**
```json
{
  "id": "client-msg-2",
  "type": "function_call",
  "content": {
    "function_name": "get_weather",
    "arguments": {
      "location": "New York",
      "units": "celsius"
    }
  }
}
```

**Server Response:**
```json
{
  "id": "model-resp-2",
  "request_id": "client-msg-2",
  "type": "function_result",
  "content": {
    "status": "success",
    "result": {
      "temperature": 22,
      "condition": "sunny",
      "humidity": 45
    }
  }
}
```

## Window Screenshot Extension

The MCP protocol includes window screenshot functionality with the following message types:

### Window List Example

**Client Request:**
```json
{
  "id": "client-msg-3",
  "type": "window_list_request",
  "content": {}
}
```

**Server Response:**
```json
{
  "id": "model-resp-3",
  "request_id": "client-msg-3",
  "type": "window_list_response",
  "content": {
    "windows": [
      {
        "id": "Chrome:Google Chrome",
        "title": "Google Chrome",
        "process": "Chrome"
      },
      {
        "id": "Code:Visual Studio Code",
        "title": "Visual Studio Code",
        "process": "Code"
      }
    ]
  }
}
```

### Window Screenshot Example

**Client Request:**
```json
{
  "id": "client-msg-4",
  "type": "window_screenshot_request",
  "content": {
    "window_id": "Chrome:Google Chrome"
  }
}
```

**Server Response:**
```json
{
  "id": "model-resp-4",
  "request_id": "client-msg-4",
  "type": "window_screenshot_response",
  "content": {
    "status": "success",
    "image_data": "base64_encoded_image_data",
    "format": "png"
  }
}
```

## Error Handling

When an error occurs, the server should send a response with the `error` type:

```json
{
  "id": "model-error-1",
  "request_id": "client-msg-3",
  "type": "error",
  "content": {
    "code": "invalid_format",
    "message": "The request format is invalid"
  }
}
```

## Extensions

The MCP protocol can be extended in the following ways:

1. Adding new message types
2. Adding metadata to message content
3. Implementing streaming support
4. Adding authentication mechanisms

## Security Considerations

When implementing the MCP protocol, the following security measures should be considered:

1. Using TLS/SSL encryption for WebSocket connections
2. Implementing appropriate authentication and authorization mechanisms
3. Validating all input data
4. Limiting message size and frequency to prevent abuse
5. Handling sensitive window content with appropriate privacy measures 