import { useState, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authApi } from "../services/api";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";

export function Login() {
  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();
  const toast = useToast();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await authApi.login({
        username_or_email: usernameOrEmail,
        password: password,
      });

      localStorage.setItem("token", response.access_token);
      toast.success("Successfully logged in!");

      // Force trigger state reload on navigate
      window.location.href = "/";
    } catch (err: any) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          "Login failed. Please check your credentials.",
      );
      toast.error("Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-ethara-bg p-4 relative overflow-hidden">
      {/* Background hexagon overlay */}
      <div className="fixed inset-0 bg-hex-pattern opacity-30 pointer-events-none" />

      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-ethara-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-ethara-secondary/10 rounded-full blur-3xl pointer-events-none" />

      <Card className="w-full max-w-md relative z-10 p-8 border border-ethara-border bg-ethara-card/85 backdrop-blur-md shadow-2xl">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4 select-none">
            <img
              src="/loginlogo.svg"
              alt="Ethara.Ai"
              className="h-16 object-contain"
            />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight text-white mb-1">
            Ethara Admin Portal
          </CardTitle>
          <p className="text-sm text-ethara-text-secondary">
            Sign in to manage employees, seats, and projects.
          </p>
        </CardHeader>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-ethara-error/10 border border-ethara-error/20 text-ethara-error text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              className="block text-sm font-medium text-white mb-2"
              htmlFor="usernameOrEmail"
            >
              Username or Email
            </label>
            <input
              id="usernameOrEmail"
              type="text"
              required
              className="w-full bg-ethara-bg/50 border border-ethara-border hover:border-ethara-primary/30 focus:border-ethara-primary text-white rounded-lg px-4 py-2.5 outline-none transition-all duration-200"
              placeholder="Enter your username or email"
              value={usernameOrEmail}
              onChange={(e) => setUsernameOrEmail(e.target.value)}
            />
          </div>

          <div>
            <label
              className="block text-sm font-medium text-white mb-2"
              htmlFor="password"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              className="w-full bg-ethara-bg/50 border border-ethara-border hover:border-ethara-primary/30 focus:border-ethara-primary text-white rounded-lg px-4 py-2.5 outline-none transition-all duration-200"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <Button
            type="submit"
            className="w-full text-center py-3 bg-gradient-to-r from-ethara-secondary to-ethara-primary hover:from-ethara-secondary/95 hover:to-ethara-primary/95 text-white font-semibold rounded-lg shadow-lg hover:shadow-ethara-primary/20 transition-all duration-300"
            loading={loading}
          >
            Log In
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-ethara-text-secondary">First time here? </span>
          <Link
            to="/signup"
            className="text-ethara-primary hover:text-ethara-secondary transition-colors font-medium"
          >
            Create an admin account
          </Link>
        </div>

        {/* Demo Credentials helper */}
        <div className="mt-6 p-4 rounded-lg bg-secondary/50 border border-border text-xs space-y-2">
          <p className="font-semibold text-foreground">Demo Accounts:</p>
          <div className="flex flex-col gap-1 text-muted-foreground">
            <div className="flex justify-between">
              <span>
                <strong>Admin Username:</strong> admin
              </span>
              <span>admin123</span>
            </div>
            <div className="flex justify-between">
              <span>
                <strong>HR Username:</strong> hr
              </span>
              <span>hrpassword</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
