class McpClientError(RuntimeError):
    pass
class McpConnectionError(McpClientError):
    pass
class McpDiscoveryError(McpClientError):
    pass
class McpToolNotFoundError(McpClientError):
    pass
class McpToolTimeoutError(McpClientError):
    pass
class McpToolExecutionError(McpClientError):
    pass
class InvalidMcpToolResultError(McpClientError):
    pass
