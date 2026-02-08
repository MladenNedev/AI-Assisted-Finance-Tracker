export interface HealthResponse {
  status: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}
