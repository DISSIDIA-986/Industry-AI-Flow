import { expect, Locator, Page } from '@playwright/test';

/**
 * Login page object model
 * Encapsulates all interactions and assertions of the login page
 */
export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly registerLink: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel(/Mail|Email/i);
    this.passwordInput = page.getByLabel(/password|Password/i);
    this.loginButton = page.getByRole('button', { name: /Log in|Sign In/i });
    this.registerLink = page.getByRole('link', { name: /register|Register/i });
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.successMessage = page.locator('[data-testid="success-message"]');
  }

  /**
   * Navigate to the login page
   */
  async goto() {
    await this.page.goto('/login');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Fill out the login form
   */
  async fillLoginForm(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
  }

  /**
   * Submit login form
   */
  async submitLoginForm() {
    await this.loginButton.click();
  }

  /**
   * Perform the complete login process
   */
  async login(email: string, password: string) {
    await this.fillLoginForm(email, password);
    await this.submitLoginForm();
  }

  /**
   * Navigate to registration page
   */
  async gotoRegister() {
    await this.registerLink.click();
    await this.page.waitForURL(/.*register.*/);
  }

  /**
   * Validate login page elements
   */
  async verifyPageElements() {
    await expect(this.page).toHaveTitle(/Industry AI Flow/);
    await expect(this.page.getByRole('heading', { name: /Log in|Sign In/i })).toBeVisible();
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
    await expect(this.loginButton).toBeVisible();
    await expect(this.registerLink).toBeVisible();
  }

  /**
   * Validation error message
   */
  async verifyErrorMessage(expectedMessage: string) {
    await expect(this.errorMessage).toBeVisible();
    await expect(this.errorMessage).toContainText(expectedMessage);
  }

  /**
   * Verification success message
   */
  async verifySuccessMessage(expectedMessage: string) {
    await expect(this.successMessage).toBeVisible();
    await expect(this.successMessage).toContainText(expectedMessage);
  }

  /**
   * Verify redirect to dashboard
   */
  async verifyRedirectToDashboard() {
    await this.page.waitForURL(/.*dashboard.*/);
    await expect(this.page.getByRole('heading', { name: /Dashboard|Dashboard/i })).toBeVisible();
  }
}
