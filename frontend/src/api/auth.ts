import { apiRequest, setAccessToken } from "./client";

export type AuthCredentials = {
  email: string;
  password: string;
};

export type User = {
  id: string;
  email: string;
};

type TokenResponse = {
  access_token: string;
  token_type: "bearer";
};

export async function register(credentials: AuthCredentials) {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials)
  });
}

export async function login(credentials: AuthCredentials) {
  const token = await apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials)
  });
  setAccessToken(token.access_token);
  return token;
}

export async function getCurrentUser() {
  return apiRequest<User>("/auth/me", { auth: true });
}
