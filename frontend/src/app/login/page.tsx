'use client';

/**
 * Login / Register Page — premium glassmorphic split-panel auth UI.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { login, register } from '@/lib/auth';
import { useAuthStore } from '@/stores/authStore';
import {
  Shield,
  Zap,
  Database,
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, hydrate, setUser } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Form fields
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isAuthenticated) {
      const stored = typeof window !== 'undefined' ? localStorage.getItem('eurekax_user') : null;
      const u = stored ? JSON.parse(stored) : null;
      router.replace(u?.role === 'admin' ? '/admin-home' : '/employee-home');
    }
  }, [isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      let data;
      if (isRegister) {
        data = await register({ email, username, password });
        setUser(data.user);
      } else {
        data = await login({ email, password });
        setUser(data.user);
      }
      router.replace(data.user.role === 'admin' ? '/admin-home' : '/employee-home');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setIsSubmitting(false);
    }
  };

  const features = [
    { icon: Shield, label: 'Role-Based Access', desc: 'Admin & Employee tiers with granular permissions' },
    { icon: Database, label: 'Data Governance', desc: 'Catalog, lineage tracking & audit trails' },
    { icon: Lock, label: 'AI Security Layer', desc: 'Guardrails, query sanitization & anomaly detection' },
    { icon: Zap, label: 'Unified Workspace', desc: 'SQL editor, notebooks & AI assistant in one place' },
  ];

  return (
    <div className="login-page">
      {/* Ambient background */}
      <div className="login-ambient">
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <div className="login-orb login-orb-3" />
      </div>

      <div className="login-container">
        {/* Left Panel — Branding */}
        <div className="login-brand-panel">
          <div className="login-brand-content">
            <div className="login-logo">
              <Sparkles size={32} />
              <span>EurekaX</span>
            </div>
            <h1 className="login-tagline">
              Enterprise Data Platform
            </h1>
            <p className="login-subtitle">
              Databricks-inspired workspace with AI-powered governance,
              security, and unified query tools.
            </p>

            <div className="login-features">
              {features.map((f, i) => (
                <div key={i} className="login-feature-item">
                  <div className="login-feature-icon">
                    <f.icon size={18} />
                  </div>
                  <div>
                    <div className="login-feature-label">{f.label}</div>
                    <div className="login-feature-desc">{f.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel — Auth Form */}
        <div className="login-form-panel">
          <div className="login-form-wrapper">
            <h2 className="login-form-title">
              {isRegister ? 'Create Account' : 'Welcome Back'}
            </h2>
            <p className="login-form-subtitle">
              {isRegister
                ? 'Set up your EurekaX workspace'
                : 'Sign in to your workspace'}
            </p>

            {error && (
              <div className="login-error">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="login-form">
              {/* Email */}
              <div className="login-field">
                <label htmlFor="login-email">Email</label>
                <div className="login-input-wrap">
                  <Mail size={16} className="login-input-icon" />
                  <input
                    id="login-email"
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              {/* Username (register only) */}
              {isRegister && (
                <div className="login-field">
                  <label htmlFor="login-username">Username</label>
                  <div className="login-input-wrap">
                    <User size={16} className="login-input-icon" />
                    <input
                      id="login-username"
                      type="text"
                      placeholder="johndoe"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                      minLength={3}
                      autoComplete="username"
                    />
                  </div>
                </div>
              )}

              {/* Password */}
              <div className="login-field">
                <label htmlFor="login-password">Password</label>
                <div className="login-input-wrap">
                  <Lock size={16} className="login-input-icon" />
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    autoComplete={isRegister ? 'new-password' : 'current-password'}
                  />
                  <button
                    type="button"
                    className="login-eye-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                className="login-submit-btn"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <div className="login-btn-spinner" />
                ) : (
                  <>
                    {isRegister ? 'Create Account' : 'Sign In'}
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* Toggle */}
            <div className="login-toggle">
              {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => { setIsRegister(!isRegister); setError(''); }}
                className="login-toggle-btn"
              >
                {isRegister ? 'Sign In' : 'Create Account'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
