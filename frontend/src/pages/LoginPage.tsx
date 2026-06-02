import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login } from "../api/auth";
import { Button } from "../components/ui/button";

type LoginPageProps = {
  onAuthenticated?: () => void;
};

export default function LoginPage({ onAuthenticated }: LoginPageProps) {
  const navigate = useNavigate();
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
      onAuthenticated?.();
      navigate("/", { replace: true });
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "登录失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="login-scene">
      <form className="auth-form login-form" onSubmit={handleSubmit}>
        <p className="login-brand">Komorebi</p>
        <h1>LOGIN</h1>
        <label>
          <span>邮箱</span>
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            autoComplete="email"
            required
          />
        </label>
        <label>
          <span>密码</span>
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
            minLength={8}
            required
          />
        </label>
        {error ? <p className="form-error login-error">{error}</p> : null}
        <Link className="auth-switch-link login-register-link" to="/register">
          注册
        </Link>
        <Button className="auth-submit-glow login-submit" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "登录中..." : "登录"}
        </Button>
      </form>
    </section>
  );
}
