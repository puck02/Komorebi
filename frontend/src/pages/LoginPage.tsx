import { FormEvent, useState } from "react";

import { login } from "../api/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login({ email, password });
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "登录失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h1>登录</h1>
      <label>
        邮箱
        <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
      </label>
      <label>
        密码
        <input
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          type="password"
          minLength={8}
          required
        />
      </label>
      {error ? <p className="form-error">{error}</p> : null}
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "登录中..." : "登录"}
      </button>
    </form>
  );
}
