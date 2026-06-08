import { CheckCircle2, KeyRound, LogOut, Mail, Save, Server, UserRound } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { getAdminPermissions, getAiSettings, updateAiSettings } from "../api/admin";
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
  const adminPermissionsQuery = useQuery({ queryFn: getAdminPermissions, queryKey: ["admin-permissions"] });

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

      {adminPermissionsQuery.data?.canManageAiSettings ? <AiSettingsPanel /> : null}
    </section>
  );
}

const MODEL_OPTIONS = ["gpt-5.5", "gpt-5.4-mini", "gpt-4.1", "gpt-4.1-mini", "o3"];

function AiSettingsPanel() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({ queryFn: getAiSettings, queryKey: ["ai-settings"] });
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("gpt-5.5");
  const [reviewModel, setReviewModel] = useState("gpt-5.4-mini");
  const updateMutation = useMutation({
    mutationFn: updateAiSettings,
    onSuccess: (settings) => {
      setApiKey("");
      setBaseUrl(settings.baseUrl);
      setModel(settings.model);
      setReviewModel(settings.reviewModel);
      queryClient.setQueryData(["ai-settings"], settings);
    }
  });

  useEffect(() => {
    const settings = settingsQuery.data;
    if (!settings) {
      return;
    }
    setBaseUrl(settings.baseUrl);
    setModel(settings.model);
    setReviewModel(settings.reviewModel);
  }, [settingsQuery.data]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateMutation.mutate({
      apiKey: apiKey.trim() || undefined,
      baseUrl: baseUrl.trim(),
      model: model.trim() || "gpt-5.5",
      reviewModel: reviewModel.trim() || "gpt-5.4-mini"
    });
  }

  return (
    <form className="account-ai-settings" onSubmit={handleSubmit}>
      <div className="account-ai-heading">
        <div>
          <span>管理员</span>
          <h2>AI 服务</h2>
        </div>
        <span className={settingsQuery.data?.hasApiKey ? "ai-key-status is-ready" : "ai-key-status"}>
          <CheckCircle2 size={15} />
          {settingsQuery.data?.hasApiKey ? "Key 已配置" : "Key 未配置"}
        </span>
      </div>

      {settingsQuery.error instanceof Error ? <p className="form-error">{settingsQuery.error.message}</p> : null}
      {updateMutation.error instanceof Error ? <p className="form-error">{updateMutation.error.message}</p> : null}
      {updateMutation.isSuccess ? <p className="form-success">AI 配置已保存</p> : null}

      <div className="ai-settings-grid">
        <label className="ai-settings-field is-wide">
          <span>
            <Server size={15} />
            Base URL
          </span>
          <input
            autoComplete="off"
            placeholder="https://api.openai.com/v1"
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
          />
        </label>

        <label className="ai-settings-field is-wide">
          <span>
            <KeyRound size={15} />
            API Key
          </span>
          <input
            autoComplete="new-password"
            placeholder={settingsQuery.data?.hasApiKey ? "已保存，输入新 Key 覆盖" : "输入 API Key"}
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
          />
        </label>

        <label className="ai-settings-field">
          <span>生成模型</span>
          <input list="ai-model-options" value={model} onChange={(event) => setModel(event.target.value)} />
        </label>

        <label className="ai-settings-field">
          <span>评审模型</span>
          <input list="ai-model-options" value={reviewModel} onChange={(event) => setReviewModel(event.target.value)} />
        </label>
      </div>

      <datalist id="ai-model-options">
        {MODEL_OPTIONS.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>

      <div className="ai-settings-actions">
        <Button type="submit" disabled={settingsQuery.isLoading || updateMutation.isPending}>
          <Save size={16} />
          {updateMutation.isPending ? "保存中" : "保存配置"}
        </Button>
      </div>
    </form>
  );
}
