/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { describe, it, expect, vi } from 'vitest';
import {
  extractErrorMessage,
  extractErrorCode,
  extractErrorDetails,
  formatValidationErrors,
  isApiError,
  isLegacyApiError,
  isAxiosError,
  hasValidationErrors,
  createErrorHandler,
  logError,
} from './errorUtils';

// Helper to create a mock Axios error
function makeAxiosError(overrides: {
  response?: {
    status: number;
    data: unknown;
  };
  message?: string;
  code?: string;
}) {
  return {
    isAxiosError: true as const,
    message: overrides.message ?? 'Request failed',
    code: overrides.code,
    response: overrides.response
      ? {
          status: overrides.response.status,
          data: overrides.response.data,
          headers: {},
          statusText: '',
          config: {} as never,
        }
      : undefined,
    config: {} as never,
    toJSON: () => ({}),
    name: 'AxiosError',
  };
}

// ---------------------------------------------------------------------------
// isApiError
// ---------------------------------------------------------------------------
describe('isApiError', () => {
  it('returns true for valid PacketArch API error shape', () => {
    expect(isApiError({ error: 'VALIDATION_ERROR', message: 'Invalid input' })).toBe(true);
  });

  it('returns true when extra fields are present', () => {
    expect(
      isApiError({ error: 'NOT_FOUND', message: 'Not found', details: { id: 1 } })
    ).toBe(true);
  });

  it('returns false for null', () => {
    expect(isApiError(null)).toBe(false);
  });

  it('returns false for non-object', () => {
    expect(isApiError('string')).toBe(false);
    expect(isApiError(42)).toBe(false);
  });

  it('returns false when error field is missing', () => {
    expect(isApiError({ message: 'hello' })).toBe(false);
  });

  it('returns false when message field is missing', () => {
    expect(isApiError({ error: 'CODE' })).toBe(false);
  });

  it('returns false when fields are wrong types', () => {
    expect(isApiError({ error: 123, message: 'hello' })).toBe(false);
    expect(isApiError({ error: 'CODE', message: 123 })).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// isLegacyApiError
// ---------------------------------------------------------------------------
describe('isLegacyApiError', () => {
  it('returns true for legacy format', () => {
    expect(isLegacyApiError({ detail: 'Unauthorized' })).toBe(true);
  });

  it('returns false for null', () => {
    expect(isLegacyApiError(null)).toBe(false);
  });

  it('returns false when detail is not a string', () => {
    expect(isLegacyApiError({ detail: 123 })).toBe(false);
    expect(isLegacyApiError({ detail: { message: 'x' } })).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// isAxiosError
// ---------------------------------------------------------------------------
describe('isAxiosError', () => {
  it('returns true for axios-like error', () => {
    expect(isAxiosError(makeAxiosError({ message: 'fail' }))).toBe(true);
  });

  it('returns false for plain Error', () => {
    expect(isAxiosError(new Error('oops'))).toBe(false);
  });

  it('returns false for null', () => {
    expect(isAxiosError(null)).toBe(false);
  });

  it('returns false for string', () => {
    expect(isAxiosError('error')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// hasValidationErrors
// ---------------------------------------------------------------------------
describe('hasValidationErrors', () => {
  it('returns true when validation_errors array exists', () => {
    expect(
      hasValidationErrors({
        validation_errors: [{ field: 'name', message: 'required', type: 'missing' }],
      })
    ).toBe(true);
  });

  it('returns false for undefined', () => {
    expect(hasValidationErrors(undefined)).toBe(false);
  });

  it('returns false when validation_errors is not an array', () => {
    expect(hasValidationErrors({ validation_errors: 'not_array' })).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// extractErrorMessage
// ---------------------------------------------------------------------------
describe('extractErrorMessage', () => {
  // Null / undefined
  it('returns fallback for null', () => {
    expect(extractErrorMessage(null)).toBe('An unexpected error occurred');
  });

  it('returns fallback for undefined', () => {
    expect(extractErrorMessage(undefined)).toBe('An unexpected error occurred');
  });

  it('returns custom fallback for null', () => {
    expect(extractErrorMessage(null, 'Custom fallback')).toBe('Custom fallback');
  });

  // Axios: PacketArch API error format
  it('extracts message from PacketArch API error (Axios)', () => {
    const error = makeAxiosError({
      response: {
        status: 400,
        data: { error: 'VALIDATION_ERROR', message: 'Name is required' },
      },
    });
    expect(extractErrorMessage(error)).toBe('Name is required');
  });

  // Axios: Legacy FastAPI error
  it('extracts detail from legacy FastAPI error (Axios)', () => {
    const error = makeAxiosError({
      response: {
        status: 422,
        data: { detail: 'Validation error occurred' },
      },
    });
    expect(extractErrorMessage(error)).toBe('Validation error occurred');
  });

  // Axios: network error (no response)
  it('returns network error message when no response', () => {
    const error = makeAxiosError({ message: 'Network Error' });
    expect(extractErrorMessage(error)).toBe('Network Error');
  });

  it('returns timeout message for ECONNABORTED', () => {
    const error = makeAxiosError({ message: 'timeout', code: 'ECONNABORTED' });
    expect(extractErrorMessage(error)).toBe('Request timed out. Please try again.');
  });

  it('returns network error message for ERR_NETWORK', () => {
    const error = makeAxiosError({ message: 'Network Error', code: 'ERR_NETWORK' });
    expect(extractErrorMessage(error)).toBe('Network error. Please check your connection.');
  });

  it('returns fallback for network error with no message', () => {
    const error = makeAxiosError({ message: '' });
    expect(extractErrorMessage(error)).toBe('Network error occurred');
  });

  // Axios: status-based messages
  it('returns auth required for 401', () => {
    const error = makeAxiosError({
      response: { status: 401, data: {} },
    });
    expect(extractErrorMessage(error)).toBe('Authentication required. Please log in.');
  });

  it('returns permission denied for 403', () => {
    const error = makeAxiosError({
      response: { status: 403, data: {} },
    });
    expect(extractErrorMessage(error)).toBe('Permission denied.');
  });

  it('returns not found for 404', () => {
    const error = makeAxiosError({
      response: { status: 404, data: {} },
    });
    expect(extractErrorMessage(error)).toBe('The requested resource was not found.');
  });

  it('returns rate limit message for 429', () => {
    const error = makeAxiosError({
      response: { status: 429, data: {} },
    });
    expect(extractErrorMessage(error)).toBe('Too many requests. Please wait a moment.');
  });

  it('returns server error for 500', () => {
    const error = makeAxiosError({
      response: { status: 500, data: {} },
    });
    expect(extractErrorMessage(error)).toBe('Server error. Please try again later.');
  });

  it('returns server error for 502', () => {
    const error = makeAxiosError({
      response: { status: 502, data: {} },
    });
    expect(extractErrorMessage(error)).toBe('Server error. Please try again later.');
  });

  // Axios: fallback to message
  it('falls back to axios message for unhandled status', () => {
    const error = makeAxiosError({
      response: { status: 418, data: {} },
      message: "I'm a teapot",
    });
    expect(extractErrorMessage(error)).toBe("I'm a teapot");
  });

  // Standard Error object
  it('extracts message from Error object', () => {
    expect(extractErrorMessage(new Error('Something broke'))).toBe('Something broke');
  });

  it('returns fallback for Error with empty message', () => {
    expect(extractErrorMessage(new Error(''), 'Fallback')).toBe('Fallback');
  });

  // String error
  it('returns the string directly', () => {
    expect(extractErrorMessage('Direct error string')).toBe('Direct error string');
  });

  // Object with message property
  it('extracts message from plain object with message', () => {
    expect(extractErrorMessage({ message: 'Object message' })).toBe('Object message');
  });

  it('returns fallback for object with non-string message', () => {
    expect(extractErrorMessage({ message: 42 }, 'Fallback')).toBe('Fallback');
  });

  // Unknown types
  it('returns fallback for number', () => {
    expect(extractErrorMessage(42)).toBe('An unexpected error occurred');
  });

  it('returns fallback for boolean', () => {
    expect(extractErrorMessage(true, 'Nope')).toBe('Nope');
  });

  it('returns fallback for empty object', () => {
    expect(extractErrorMessage({}, 'Fallback')).toBe('Fallback');
  });
});

// ---------------------------------------------------------------------------
// extractErrorCode
// ---------------------------------------------------------------------------
describe('extractErrorCode', () => {
  it('extracts code from PacketArch API error', () => {
    const error = makeAxiosError({
      response: {
        status: 400,
        data: { error: 'VALIDATION_ERROR', message: 'Bad input' },
      },
    });
    expect(extractErrorCode(error)).toBe('VALIDATION_ERROR');
  });

  it('returns undefined for non-axios error', () => {
    expect(extractErrorCode(new Error('oops'))).toBeUndefined();
  });

  it('returns undefined for axios error without API error format', () => {
    const error = makeAxiosError({
      response: { status: 500, data: { detail: 'Server error' } },
    });
    expect(extractErrorCode(error)).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// extractErrorDetails
// ---------------------------------------------------------------------------
describe('extractErrorDetails', () => {
  it('extracts details from PacketArch API error', () => {
    const details = { field: 'name', value: 'test' };
    const error = makeAxiosError({
      response: {
        status: 400,
        data: { error: 'VALIDATION_ERROR', message: 'Bad', details },
      },
    });
    expect(extractErrorDetails(error)).toEqual(details);
  });

  it('returns undefined when no details present', () => {
    const error = makeAxiosError({
      response: {
        status: 400,
        data: { error: 'VALIDATION_ERROR', message: 'Bad' },
      },
    });
    expect(extractErrorDetails(error)).toBeUndefined();
  });

  it('returns undefined for non-axios error', () => {
    expect(extractErrorDetails('string')).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// formatValidationErrors
// ---------------------------------------------------------------------------
describe('formatValidationErrors', () => {
  it('formats a single validation error', () => {
    const error = makeAxiosError({
      response: {
        status: 422,
        data: {
          error: 'VALIDATION_ERROR',
          message: 'Validation failed',
          details: {
            validation_errors: [
              { field: 'name', message: 'is required', type: 'missing' },
            ],
          },
        },
      },
    });
    expect(formatValidationErrors(error)).toBe('name: is required');
  });

  it('formats multiple validation errors with semicolons', () => {
    const error = makeAxiosError({
      response: {
        status: 422,
        data: {
          error: 'VALIDATION_ERROR',
          message: 'Validation failed',
          details: {
            validation_errors: [
              { field: 'name', message: 'is required', type: 'missing' },
              { field: 'port', message: 'must be positive', type: 'range' },
            ],
          },
        },
      },
    });
    expect(formatValidationErrors(error)).toBe(
      'name: is required; port: must be positive'
    );
  });

  it('falls back to extractErrorMessage when no validation details', () => {
    const error = makeAxiosError({
      response: {
        status: 400,
        data: { error: 'BAD_REQUEST', message: 'Something wrong' },
      },
    });
    expect(formatValidationErrors(error)).toBe('Something wrong');
  });

  it('uses default fallback when no useful info available', () => {
    expect(formatValidationErrors(null)).toBe('Validation failed');
  });
});

// ---------------------------------------------------------------------------
// createErrorHandler
// ---------------------------------------------------------------------------
describe('createErrorHandler', () => {
  it('calls onError with extracted message', () => {
    const onError = vi.fn();
    const handler = createErrorHandler('testContext', 'Default message', onError);

    handler(new Error('Something failed'));

    expect(onError).toHaveBeenCalledWith('Something failed');
  });

  it('uses fallback message when error has no message', () => {
    const onError = vi.fn();
    const handler = createErrorHandler('testContext', 'Default message', onError);

    handler(null);

    expect(onError).toHaveBeenCalledWith('Default message');
  });

  it('handles axios errors', () => {
    const onError = vi.fn();
    const handler = createErrorHandler('testContext', 'Default', onError);

    const axiosErr = makeAxiosError({
      response: {
        status: 400,
        data: { error: 'VALIDATION', message: 'Field required' },
      },
    });
    handler(axiosErr);

    expect(onError).toHaveBeenCalledWith('Field required');
  });
});

// ---------------------------------------------------------------------------
// logError
// ---------------------------------------------------------------------------
describe('logError', () => {
  it('logs error to console.error with context', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    logError(new Error('test error'), 'TestContext');

    expect(spy).toHaveBeenCalledWith(
      '[TestContext] test error',
      expect.objectContaining({
        code: undefined,
        details: undefined,
        originalError: expect.any(Error),
      })
    );

    spy.mockRestore();
  });

  it('logs axios error with code and details', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const error = makeAxiosError({
      response: {
        status: 400,
        data: {
          error: 'VALIDATION_ERROR',
          message: 'Bad input',
          details: { field: 'name' },
        },
      },
    });
    logError(error, 'ApiCall');

    expect(spy).toHaveBeenCalledWith(
      '[ApiCall] Bad input',
      expect.objectContaining({
        code: 'VALIDATION_ERROR',
        details: { field: 'name' },
      })
    );

    spy.mockRestore();
  });
});
