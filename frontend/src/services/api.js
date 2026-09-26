/**
 * NEXVAULT API Client
 * Enterprise HTTP client communicating with FastAPI Control Plane (Port 8000)
 */

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
// Standardize origin without trailing slash
const API_ORIGIN = RAW_BASE_URL.replace(/\/api(\/v1)?\/?$/, '').replace(/\/+$/, '');

/**
 * Standardized NEXVAULT API Error Class
 * Distinguishes HTTP status codes and distributed system failures
 */
export class NexvaultApiError extends Error {
  constructor(message, status = 0, code = 'UNKNOWN_ERROR', data = null) {
    super(message);
    this.name = 'NexvaultApiError';
    this.status = status;
    this.code = code;
    this.data = data;
    this.isNetworkError = status === 0;
  }

  static getErrorCode(status) {
    switch (status) {
      case 401: return 'UNAUTHORIZED';
      case 403: return 'FORBIDDEN';
      case 404: return 'NOT_FOUND';
      case 409: return 'CONFLICT';
      case 422: return 'VALIDATION_ERROR';
      case 429: return 'RATE_LIMITED';
      case 500: return 'INTERNAL_SERVER_ERROR';
      case 502: return 'BAD_GATEWAY';
      case 503: return 'STORAGE_NODE_UNAVAILABLE';
      case 504: return 'QUORUM_TIMEOUT';
      default: return 'API_ERROR';
    }
  }

  static formatDetailMessage(status, detail) {
    if (detail) return typeof detail === 'string' ? detail : JSON.stringify(detail);
    switch (status) {
      case 401: return 'Authentication required. Please sign in to access NEXVAULT.';
      case 403: return 'Access denied. Administrative role required for this operation.';
      case 404: return 'The requested bucket, object, or storage node was not found.';
      case 409: return 'Resource conflict. Bucket already exists or version conflict detected.';
      case 422: return 'Invalid request payload or malformed storage key.';
      case 429: return 'Request rate limit exceeded on control plane.';
      case 500: return 'Internal control plane database failure.';
      case 503: return 'Storage node unavailable. Minimum write or read quorum could not be achieved.';
      case 504: return 'Quorum timeout waiting for storage node replica acknowledgments.';
      default: return `Unexpected HTTP error (${status})`;
    }
  }
}

class ApiClient {
  constructor(origin) {
    this.origin = origin;
    this.baseUrl = `${origin}/api/v1`;
  }

  getToken() {
    return localStorage.getItem('nexvault_auth_token');
  }

  /**
   * Check if development fallback is enabled
   * Can be toggled via localStorage 'nexvault_dev_fallback_mode' = 'false' or env
   */
  isDevFallbackEnabled() {
    const override = localStorage.getItem('nexvault_dev_fallback_mode');
    if (override !== null) return override === 'true';
    return import.meta.env.VITE_ENABLE_DEV_FALLBACK !== 'false';
  }

  resolveUrl(endpoint) {
    if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
      return endpoint;
    }
    const formatted = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    // If endpoint already includes /api/v1 or /api
    if (formatted.startsWith('/api/v1') || formatted.startsWith('/api')) {
      return `${this.origin}${formatted}`;
    }
    // Default to /api/v1
    return `${this.origin}/api/v1${formatted}`;
  }

  async request(endpoint, options = {}) {
    const url = this.resolveUrl(endpoint);
    const token = this.getToken();

    // Guard: Prevent unauthenticated admin or chaos requests from leaving the browser
    if ((endpoint.includes('/admin') || endpoint.includes('/chaos')) && !token) {
      throw new NexvaultApiError(
        'Authentication token required. Protected administrative endpoint cannot be called without valid credentials.',
        401,
        'UNAUTHORIZED'
      );
    }

    const headers = {
      ...(options.isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    const config = {
      ...options,
      headers,
    };

    let response;
    try {
      response = await fetch(url, config);
    } catch (networkErr) {
      // Real network failure (e.g. backend offline / connection refused)
      const err = new NexvaultApiError(
        `Failed to connect to NEXVAULT Control Plane at ${url}. Network error or backend offline.`,
        0,
        'CONNECTION_REFUSED',
        networkErr
      );
      throw err;
    }

    if (response.status === 401) {
      localStorage.removeItem('nexvault_auth_token');
    }

    if (!response.ok) {
      let errorData = null;
      let detailMsg = null;
      try {
        errorData = await response.json();
        detailMsg = errorData.detail || errorData.message;
      } catch {
        // Not a JSON response
      }

      const message = NexvaultApiError.formatDetailMessage(response.status, detailMsg);
      const code = NexvaultApiError.getErrorCode(response.status);
      throw new NexvaultApiError(message, response.status, code, errorData);
    }

    if (options.responseType === 'blob') {
      return await response.blob();
    }

    // Check if response has JSON body
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    return response;
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: options.isFormData ? body : JSON.stringify(body),
    });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: options.isFormData ? body : JSON.stringify(body),
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const api = new ApiClient(API_ORIGIN);
export default api;
