"use client";

import Script from "next/script";
import { useEffect, useEffectEvent, useRef, useState } from "react";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (result: { credential: string }) => void }) => void;
          renderButton: (element: HTMLElement, config: Record<string, unknown>) => void;
        };
      };
    };
  }
}

export function GoogleSignInButton({
  onCredential,
  disabled = false,
}: {
  onCredential: (credential: string) => void;
  disabled?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [scriptReady, setScriptReady] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  const handleCredential = useEffectEvent(onCredential);
  const googleUnavailable =
    scriptReady && typeof window !== "undefined" && !window.google;

  useEffect(() => {
    if (!scriptReady || !clientId || !container.current) return;
    if (!window.google) return;
    const element = container.current;
    element.replaceChildren();
    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: ({ credential }) => handleCredential(credential),
      });
      window.google.accounts.id.renderButton(element, {
        type: "standard",
        theme: "outline",
        size: "large",
        shape: "pill",
        text: "continue_with",
        width: Math.min(element.clientWidth || 400, 400),
        locale: "vi",
      });
    } catch {
      queueMicrotask(() => setLoadError(true));
    }
  }, [clientId, scriptReady]);

  if (!clientId) {
    return (
      <p className="rounded-xl bg-zinc-50 px-4 py-3 text-center text-xs text-zinc-500">
        Google OAuth chưa được cấu hình.
      </p>
    );
  }

  if (loadError || googleUnavailable) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-center text-xs text-red-600">
        Không thể tải đăng nhập Google. Vui lòng kiểm tra kết nối và thử lại.
      </p>
    );
  }

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onReady={() => setScriptReady(true)}
        onError={() => setLoadError(true)}
      />
      <div
        ref={container}
        aria-busy={!scriptReady || disabled}
        className={`flex min-h-11 w-full justify-center ${disabled ? "pointer-events-none opacity-60" : ""}`}
      >
        {!scriptReady && <span className="text-xs text-zinc-500">Đang tải đăng nhập Google...</span>}
      </div>
    </>
  );
}
