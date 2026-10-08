import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="auth-container">
      <div class="auth-card card">
        <div class="auth-header">
          <div class="brand-badge">
            <span class="brand-icon">⚡</span>
            <span class="brand-name">ProcureFlow</span>
          </div>
          <h1 class="auth-title">Welcome Back</h1>
          <p class="auth-subtitle">Sign in to manage procurement, vendors, and approvals</p>
        </div>

        @if (errorMessage()) {
          <div class="alert alert-danger" id="login-error-alert">
            <span>⚠️</span>
            <span>{{ errorMessage() }}</span>
          </div>
        }

        <form (ngSubmit)="onSubmit()" class="auth-form">
          <div class="form-group">
            <label class="form-label" for="login-email">Work Email</label>
            <input
              id="login-email-input"
              type="email"
              class="form-control"
              placeholder="e.g. admin@example.com"
              [(ngModel)]="email"
              name="email"
              required
              autocomplete="email"
            />
          </div>

          <div class="form-group">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <label class="form-label" for="login-password">Password</label>
              <a routerLink="/reset-password" class="forgot-link" id="login-forgot-pwd-link">Forgot password?</a>
            </div>
            <input
              id="login-password-input"
              type="password"
              class="form-control"
              placeholder="Enter your password"
              [(ngModel)]="password"
              name="password"
              required
              autocomplete="current-password"
            />
          </div>

          <button
            id="login-submit-btn"
            type="submit"
            class="btn btn-primary"
            style="width: 100%; margin-top: 0.5rem;"
            [disabled]="isLoading() || !email || !password"
          >
            @if (isLoading()) {
              <span>Authenticating...</span>
            } @else {
              <span>Sign In</span>
              <span>→</span>
            }
          </button>
        </form>

        <div class="quick-credentials">
          <p class="quick-title">Quick Demo Logins:</p>
          <div class="quick-btns">
            <button
              id="quick-login-admin"
              type="button"
              class="btn btn-secondary btn-sm"
              (click)="fillCredentials('admin@example.com', 'Admin@123456')"
            >
              👑 Admin
            </button>
            <button
              id="quick-login-proc-mgr"
              type="button"
              class="btn btn-secondary btn-sm"
              (click)="fillCredentials('proc_mgr@example.com', 'Password@123')"
            >
              📦 Procurement Lead
            </button>
            <button
              id="quick-login-finance"
              type="button"
              class="btn btn-secondary btn-sm"
              (click)="fillCredentials('finance@example.com', 'Finance@123456')"
            >
              💰 Finance Officer
            </button>
            <button
              id="quick-login-supply-chain"
              type="button"
              class="btn btn-secondary btn-sm"
              (click)="fillCredentials('supply_chain@example.com', 'SupplyChain@123456')"
            >
              🔗 Supply Chain
            </button>
            <button
              id="quick-login-vendor"
              type="button"
              class="btn btn-secondary btn-sm"
              (click)="fillCredentials('vendor_user@example.com', 'Vendor@123456')"
            >
              🚚 Vendor Partner
            </button>
            <button
              id="quick-login-auditor"
              type="button"
              class="btn btn-secondary btn-sm"
              (click)="fillCredentials('auditor@example.com', 'Auditor@123456')"
            >
              📋 Auditor
            </button>
          </div>
        </div>

        <div class="auth-footer">
          <span>Need an enterprise account?</span>
          <a routerLink="/register" class="register-link" id="login-go-to-register">Create Account</a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: calc(100vh - 80px);
      padding: 1.5rem;
    }
    .auth-card {
      width: 100%;
      max-width: 440px;
      padding: 2.25rem 2rem;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    }
    .auth-header {
      text-align: center;
      margin-bottom: 1.75rem;
    }
    .brand-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: 9999px;
      padding: 0.35rem 0.85rem;
      margin-bottom: 1rem;
    }
    .brand-icon {
      font-size: 1.1rem;
    }
    .brand-name {
      font-weight: 700;
      font-size: 0.85rem;
      letter-spacing: 0.05em;
      color: #60a5fa;
      text-transform: uppercase;
    }
    .auth-title {
      font-size: 1.6rem;
      margin-bottom: 0.35rem;
    }
    .auth-subtitle {
      color: var(--text-muted);
      font-size: 0.875rem;
    }
    .forgot-link {
      font-size: 0.8rem;
      color: #60a5fa;
      transition: color 0.2s;
    }
    .forgot-link:hover {
      color: #93c5fd;
      text-decoration: underline;
    }
    .quick-credentials {
      margin-top: 1.5rem;
      padding: 0.9rem;
      background: rgba(15, 23, 42, 0.5);
      border: 1px dashed var(--border-subtle);
      border-radius: var(--radius-md);
    }
    .quick-title {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }
    .quick-btns {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.4rem;
    }
    .quick-btns .btn-sm {
      font-size: 0.78rem;
      padding: 0.4rem 0.5rem;
      text-align: left;
      justify-content: flex-start;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    @media (max-width: 440px) {
      .quick-btns {
        grid-template-columns: 1fr;
      }
    }
    .auth-footer {
      margin-top: 1.5rem;
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
      display: flex;
      justify-content: center;
      gap: 0.4rem;
    }
    .register-link {
      color: #60a5fa;
      font-weight: 600;
    }
    .register-link:hover {
      text-decoration: underline;
    }
  `]
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  email = '';
  password = '';
  isLoading = signal(false);
  errorMessage = signal<string | null>(null);

  fillCredentials(e: string, p: string): void {
    this.email = e;
    this.password = p;
    this.errorMessage.set(null);
  }

  onSubmit(): void {
    if (!this.email || !this.password) return;
    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.authService.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.isLoading.set(false);
        const detail = err.error?.detail || 'Authentication failed. Please check credentials.';
        this.errorMessage.set(detail);
      }
    });
  }
}
