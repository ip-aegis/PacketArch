/**
 * Shared error handling utilities for consistent error extraction across the frontend.
 *
 * This module provides utilities for:
 * 1. Extracting user-friendly error messages from various error types
 * 2. Type guards for API error responses
 * 3. Error logging with context
 */

import type { AxiosError } from 'axios';

/**
 * Standard API error response format from PacketArch backend.
 */
export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Validation error details from Pydantic.
 */
export interface ValidationErrorDetails {
  validation_errors: Array<{
    field: string;
    message: string;
    type: string;
  }>;
}

/**
 * Legacy error format (FastAPI HTTPException).
 */
export interface LegacyApiError {
  detail: string;
}

/**
 * Type guard to check if an error response is a PacketArch API error.
 */
export function isApiError(error: unknown): error is ApiError {
  if (typeof error !== 'object' || error === null) {
    return false;
  }
  const obj = error as Record<string, unknown>;
  return typeof obj.error === 'string' && typeof obj.message === 'string';
}

/**
 * Type guard to check if an error response is a legacy FastAPI error.
 */
export function isLegacyApiError(error: unknown): error is LegacyApiError {
  if (typeof error !== 'object' || error === null) {
    return false;
  }
  const obj = error as Record<string, unknown>;
  return typeof obj.detail === 'string';
}

/**
 * Type guard to check if error details contain validation errors.
 */
export function hasValidationErrors(
  details: Record<string, unknown> | undefined
): details is ValidationErrorDetails {
  if (!details || typeof details !== 'object') {
    return false;
  }
  return Array.isArray((details as ValidationErrorDetails).validation_errors);
}

/**
 * Extract a user-friendly error message from any error type.
 *
 * Handles:
 * - PacketArch API errors (ApiError)
 * - Legacy FastAPI HTTPException errors
 * - Axios errors with response data
 * - Plain Error objects
 * - String errors
 * - Unknown error types
 *
 * @param error - The error to extract a message from
 * @param fallback - Fallback message if extraction fails
 * @returns A user-friendly error message
 *
 * @example
 * ```ts
 * try {
 *   await apiCall();
 * } catch (error) {
 *   const message = extractErrorMessage(error, 'Failed to load data');
 *   setError(message);
 * }
 * ```
 */
export function extractErrorMessage(
  error: unknown,
  fallback: string = 'An unexpected error occurred'
): string {
  // Handle null/undefined
  if (error == null) {
    return fallback;
  }

  // Handle Axios errors
  if (isAxiosError(error)) {
    const responseData = error.response?.data;

    // PacketArch API error format
    if (isApiError(responseData)) {
      return responseData.message;
    }

    // Legacy FastAPI error format
    if (isLegacyApiError(responseData)) {
      return responseData.detail;
    }

    // Network error (no response)
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        return 'Request timed out. Please try again.';
      }
      if (error.code === 'ERR_NETWORK') {
        return 'Network error. Please check your connection.';
      }
      return error.message || 'Network error occurred';
    }

    // HTTP status-based messages
    const status = error.response.status;
    if (status === 401) {
      return 'Authentication required. Please log in.';
    }
    if (status === 403) {
      return 'Permission denied.';
    }
    if (status === 404) {
      return 'The requested resource was not found.';
    }
    if (status === 429) {
      return 'Too many requests. Please wait a moment.';
    }
    if (status >= 500) {
      return 'Server error. Please try again later.';
    }

    // Fall through to message extraction
    return error.message || fallback;
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return error.message || fallback;
  }

  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }

  // Handle objects with message property
  if (typeof error === 'object' && 'message' in error) {
    const msg = (error as { message: unknown }).message;
    if (typeof msg === 'string') {
      return msg;
    }
  }

  return fallback;
}

/**
 * Extract the error code from a PacketArch API error.
 *
 * @param error - The error to extract a code from
 * @returns The error code or undefined if not available
 */
export function extractErrorCode(error: unknown): string | undefined {
  if (isAxiosError(error) && isApiError(error.response?.data)) {
    return error.response.data.error;
  }
  return undefined;
}

/**
 * Extract error details from a PacketArch API error.
 *
 * @param error - The error to extract details from
 * @returns The error details or undefined if not available
 */
export function extractErrorDetails(
  error: unknown
): Record<string, unknown> | undefined {
  if (isAxiosError(error) && isApiError(error.response?.data)) {
    return error.response.data.details;
  }
  return undefined;
}

/**
 * Format validation errors into a user-friendly string.
 *
 * @param error - The error containing validation details
 * @returns Formatted validation error message
 */
export function formatValidationErrors(error: unknown): string {
  const details = extractErrorDetails(error);

  if (hasValidationErrors(details)) {
    const errors = details.validation_errors;
    if (errors.length === 1) {
      return `${errors[0].field}: ${errors[0].message}`;
    }
    return errors.map((e) => `${e.field}: ${e.message}`).join('; ');
  }

  return extractErrorMessage(error, 'Validation failed');
}

/**
 * Type guard to check if an error is an Axios error.
 */
export function isAxiosError(error: unknown): error is AxiosError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'isAxiosError' in error &&
    (error as AxiosError).isAxiosError === true
  );
}

/**
 * Log an error with context for debugging.
 *
 * @param error - The error to log
 * @param context - Additional context about where the error occurred
 */
export function logError(error: unknown, context: string): void {
  const message = extractErrorMessage(error);
  const code = extractErrorCode(error);
  const details = extractErrorDetails(error);

  console.error(`[${context}] ${message}`, {
    code,
    details,
    originalError: error,
  });
}

/**
 * Create an error handler for async operations in stores.
 *
 * @param context - Description of the operation for logging
 * @param fallbackMessage - Fallback message for the error state
 * @param onError - Callback to set error state
 * @returns Error handler function
 *
 * @example
 * ```ts
 * const handleError = createErrorHandler(
 *   'fetchDevices',
 *   'Failed to load devices',
 *   (message) => set({ error: message })
 * );
 *
 * try {
 *   await apiCall();
 * } catch (error) {
 *   handleError(error);
 * }
 * ```
 */
export function createErrorHandler(
  context: string,
  fallbackMessage: string,
  onError: (message: string) => void
): (error: unknown) => void {
  return (error: unknown) => {
    logError(error, context);
    const message = extractErrorMessage(error, fallbackMessage);
    onError(message);
  };
}
