import { LogOut, Mail, UserRound } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getCurrentUser } from "../api/auth";
import { clearAccessToken } from "../api/client";
import { Button } from "../components/ui/button";

type AccountPageProps = {
  onLogout: () => void;
};

export default function AccountPage({ onLogout }: AccountPageProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const userQuery = useQuery({ queryFn: getCurrentUser, queryKey: ["current-user"] });

  function handleLogout() {
    clearAccessToken();
    queryClient.clear();
    onLogout();
    navigate("/login", { replace: true });
  }

  return (
    <section className="account-page">
      <header className="account-header">
        <div>
          <p className="eyebrow">Studio pass</p>
          <h1>账号</h1>
          <p>管理当前工作室身份和登录状态。</p>
        </div>
      </header>

      <div className="account-panel">
        <div className="account-avatar" aria-hidden="true">
          <UserRound size={30} />
        </div>
        <div className="account-info">
          <span>当前登录</span>
          {userQuery.isLoading ? <p>正在加载账号信息...</p> : null}
          {userQuery.error instanceof Error ? <p className="form-error">{userQuery.error.message}</p> : null}
          {userQuery.data ? (
            <p>
              <Mail size={16} />
              {userQuery.data.email}
            </p>
          ) : null}
        </div>
        <div className="account-stamp" aria-hidden="true">
          Komorebi
        </div>
        <Button className="account-logout" type="button" variant="outline" onClick={handleLogout}>
          <LogOut size={17} />
          退出登录
        </Button>
      </div>
    </section>
  );
}
