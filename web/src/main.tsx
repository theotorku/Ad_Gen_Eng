import { useEffect, useState } from "react";
import React from "react";
import {
  ClerkProvider,
  SignInButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
} from "@clerk/clerk-react";
import ReactDOM from "react-dom/client";
import { setAuthTokenProvider } from "./api";
import App from "./App";
import LandingPage from "./components/LandingPage";
import "./styles.css";

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function ClerkAppShell() {
  const { getToken, isLoaded } = useAuth();
  const [view, setView] = useState<"landing" | "studio">("landing");

  useEffect(() => {
    setAuthTokenProvider(async () => {
      if (!isLoaded) return null;
      return getToken();
    });
    return () => setAuthTokenProvider(null);
  }, [getToken, isLoaded]);

  if (view === "landing") {
    return <LandingPage onLaunchStudio={() => setView("studio")} />;
  }

  return (
    <>
      <SignedOut>
        <main className="auth-screen">
          <section className="auth-panel">
            <p className="eyebrow">Ad Generation Engine</p>
            <h1>Sign in to your campaign workspace</h1>
            <p>
              Clerk protects the dashboard and keeps generated campaigns scoped to
              your authenticated workspace.
            </p>
            <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
              <button
                className="ghost-action"
                type="button"
                onClick={() => setView("landing")}
              >
                Back to Home
              </button>
              <SignInButton mode="modal">
                <button className="primary-action" type="button" style={{ margin: 0 }}>
                  Sign in
                </button>
              </SignInButton>
            </div>
          </section>
        </main>
      </SignedOut>
      <SignedIn>
        <div className="session-toolbar" style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            className="ghost-action"
            type="button"
            onClick={() => setView("landing")}
            style={{ minHeight: "32px", fontSize: "12.5px" }}
          >
            Home
          </button>
          <UserButton />
        </div>
        <App onBackToLanding={() => setView("landing")} />
      </SignedIn>
    </>
  );
}

function NonClerkAppShell() {
  const [view, setView] = useState<"landing" | "studio">("landing");

  if (view === "landing") {
    return <LandingPage onLaunchStudio={() => setView("studio")} />;
  }
  return <App onBackToLanding={() => setView("landing")} />;
}

function Root() {
  if (!CLERK_PUBLISHABLE_KEY) {
    setAuthTokenProvider(null);
    return <NonClerkAppShell />;
  }

  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <ClerkAppShell />
    </ClerkProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
