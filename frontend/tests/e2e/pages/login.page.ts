import { expect, Locator, Page } from '@playwright/test';

/**
 * 登录页面对象模型
 * 封装登录页面的所有交互和断言
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
    this.emailInput = page.getByLabel(/邮箱|Email/i);
    this.passwordInput = page.getByLabel(/密码|Password/i);
    this.loginButton = page.getByRole('button', { name: /登录|Sign In/i });
    this.registerLink = page.getByRole('link', { name: /注册|Register/i });
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.successMessage = page.locator('[data-testid="success-message"]');
  }

  /**
   * 导航到登录页面
   */
  async goto() {
    await this.page.goto('/login');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 填写登录表单
   */
  async fillLoginForm(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
  }

  /**
   * 提交登录表单
   */
  async submitLoginForm() {
    await this.loginButton.click();
  }

  /**
   * 执行完整登录流程
   */
  async login(email: string, password: string) {
    await this.fillLoginForm(email, password);
    await this.submitLoginForm();
  }

  /**
   * 导航到注册页面
   */
  async gotoRegister() {
    await this.registerLink.click();
    await this.page.waitForURL(/.*register.*/);
  }

  /**
   * 验证登录页面元素
   */
  async verifyPageElements() {
    await expect(this.page).toHaveTitle(/Industry AI Flow/);
    await expect(this.page.getByRole('heading', { name: /登录|Sign In/i })).toBeVisible();
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
    await expect(this.loginButton).toBeVisible();
    await expect(this.registerLink).toBeVisible();
  }

  /**
   * 验证错误消息
   */
  async verifyErrorMessage(expectedMessage: string) {
    await expect(this.errorMessage).toBeVisible();
    await expect(this.errorMessage).toContainText(expectedMessage);
  }

  /**
   * 验证成功消息
   */
  async verifySuccessMessage(expectedMessage: string) {
    await expect(this.successMessage).toBeVisible();
    await expect(this.successMessage).toContainText(expectedMessage);
  }

  /**
   * 验证重定向到仪表板
   */
  async verifyRedirectToDashboard() {
    await this.page.waitForURL(/.*dashboard.*/);
    await expect(this.page.getByRole('heading', { name: /仪表板|Dashboard/i })).toBeVisible();
  }
}
