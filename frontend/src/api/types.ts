export interface HealthResponse {
  status: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthStatusResponse {
  status: string;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}
