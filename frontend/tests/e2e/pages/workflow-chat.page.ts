import { expect, Locator, Page } from '@playwright/test';

/**
 * 工作流聊天页面对象模型
 * 封装聊天页面的所有交互和断言
 */
export class WorkflowChatPage {
  readonly page: Page;
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly chatContainer: Locator;
  readonly connectionStatus: Locator;
  readonly aiResponse: Locator;
  readonly userMessage: Locator;
  readonly clearChatButton: Locator;
  readonly exportChatButton: Locator;
  readonly settingsButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.messageInput = page.getByPlaceholder(/输入消息|Type your message/i);
    this.sendButton = page.getByRole('button', { name: /发送|Send/i });
    this.chatContainer = page.locator('[data-testid="chat-container"]');
    this.connectionStatus = page.locator('[data-testid="connection-status"]');
    this.aiResponse = page.locator('[data-testid="ai-response"]');
    this.userMessage = page.locator('[data-testid="user-message"]');
    this.clearChatButton = page.getByRole('button', { name: /清空聊天|Clear Chat/i });
    this.exportChatButton = page.getByRole('button', { name: /导出聊天|Export Chat/i });
    this.settingsButton = page.getByRole('button', { name: /设置|Settings/i });
  }

  /**
   * 导航到工作流聊天页面
   */
  async goto() {
    await this.page.goto('/workflow-chat');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 验证页面元素
   */
  async verifyPageElements() {
    await expect(this.page).toHaveURL(/.*workflow-chat.*/);
    await expect(this.page.getByRole('heading', { name: /工作流聊天|Workflow Chat/i })).toBeVisible();
    await expect(this.messageInput).toBeVisible();
    await expect(this.sendButton).toBeVisible();
    await expect(this.chatContainer).toBeVisible();
    await expect(this.connectionStatus).toBeVisible();
  }

  /**
   * 发送消息
   */
  async sendMessage(message: string) {
    await this.messageInput.fill(message);
    await this.sendButton.click();
  }

  /**
   * 验证消息已发送
   */
  async verifyMessageSent(message: string) {
    await expect(this.userMessage.filter({ hasText: message })).toBeVisible();
  }

  /**
   * 验证收到AI响应
   */
  async verifyAIResponse(timeout = 10000) {
    await expect(this.aiResponse.first()).toBeVisible({ timeout });
  }

  /**
   * 验证连接状态
   */
  async verifyConnectionStatus(expectedStatus: 'connected' | 'disconnected' | 'connecting') {
    const statusText = {
      connected: /连接|connected/i,
      disconnected: /断开|disconnected/i,
      connecting: /连接中|connecting/i
    };
    
    await expect(this.connectionStatus).toContainText(statusText[expectedStatus], {
      timeout: 5000
    });
  }

  /**
   * 清空聊天记录
   */
  async clearChat() {
    await this.clearChatButton.click();
    
    // 确认清空
    await this.page.getByRole('button', { name: /确认|Confirm/i }).click();
    
    // 验证聊天已清空
    await expect(this.userMessage).toHaveCount(0);
    await expect(this.aiResponse).toHaveCount(0);
  }

  /**
   * 导出聊天记录
   */
  async exportChat() {
    await this.exportChatButton.click();
    
    // 等待下载开始
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.getByRole('button', { name: /导出|Export/i }).click();
    const download = await downloadPromise;
    
    // 验证下载的文件名
    expect(download.suggestedFilename()).toMatch(/chat-export.*\.(json|txt|csv)/);
  }

  /**
   * 打开设置面板
   */
  async openSettings() {
    await this.settingsButton.click();
    await expect(this.page.locator('[data-testid="settings-panel"]')).toBeVisible();
  }

  /**
   * 更改AI模型
   */
  async changeAIModel(modelName: string) {
    await this.openSettings();
    
    // 选择模型
    await this.page.getByLabel(/AI模型|AI Model/i).selectOption(modelName);
    
    // 保存设置
    await this.page.getByRole('button', { name: /保存|Save/i }).click();
    
    // 验证设置已保存
    await expect(this.page.getByText(/设置已保存|Settings saved/i)).toBeVisible();
  }

  /**
   * 测试实时消息流
   */
  async testRealTimeMessaging() {
    const testMessages = [
      '你好，请介绍一下这个系统',
      '如何上传文档？',
      '成本估算怎么用？'
    ];
    
    for (const message of testMessages) {
      await this.sendMessage(message);
      await this.verifyMessageSent(message);
      await this.verifyAIResponse();
      
      // 等待一小段时间再发送下一条消息
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * 测试长对话
   */
  async testLongConversation() {
    const longMessage = '这是一个较长的测试消息，用于测试系统处理长文本的能力。'.repeat(10);
    await this.sendMessage(longMessage);
    await this.verifyMessageSent(longMessage);
    await this.verifyAIResponse(15000); // 给长响应更多时间
  }

  /**
   * 测试特殊字符和表情
   */
  async testSpecialCharacters() {
    const specialMessages = [
      'Hello @world! #testing',
      '测试中文和emoji 😊🎉',
      'SQL: SELECT * FROM users;',
      '代码: console.log("test");',
      '链接: https://example.com'
    ];
    
    for (const message of specialMessages) {
      await this.sendMessage(message);
      await this.verifyMessageSent(message);
      await this.verifyAIResponse();
      await this.page.waitForTimeout(500);
    }
  }
}
