/** Current caller returned by GET /me; grants are not inferred from persona names. */
export interface Identity {
  ref: string;
  display_name: string;
  scope: 'plant';
  permissions: string[];
  plant_zone: string;
}

/** POST /auth/login response; token is retained in memory only. */
export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

/** Safe backend Problem envelope, not a raw exception response. */
export interface Problem {
  status: number;
  code: string;
  title: string;
  field_errors?: Record<string, string>;
}

/** Exact response revision belongs to the returned parent representation. */
export interface ApiResult<T> {
  data: T;
  etag: string | null;
}
