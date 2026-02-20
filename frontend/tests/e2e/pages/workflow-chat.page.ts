import { expect, Locator, Page } from '@playwright/test';

/**
 * Workflow Chat Page Object Model
 * Encapsulates all interactions and assertions of the chat page
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
    this.messageInput = page.getByPlaceholder(/Enter message|Type your message/i);
    this.sendButton = page.getByRole('button', { name: /send|Send/i });
    this.chatContainer = page.locator('[data-testid="chat-container"]');
    this.connectionStatus = page.locator('[data-testid="connection-status"]');
    this.aiResponse = page.locator('[data-testid="ai-response"]');
    this.userMessage = page.locator('[data-testid="user-message"]');
    this.clearChatButton = page.getByRole('button', { name: /Clear chat|Clear Chat/i });
    this.exportChatButton = page.getByRole('button', { name: /Export chat|Export Chat/i });
    this.settingsButton = page.getByRole('button', { name: /set up|Settings/i });
  }

  /**
   * Navigate to the workflow chat page
   */
  async goto() {
    await this.page.goto('/workflow-chat');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Validate page elements
   */
  async verifyPageElements() {
    await expect(this.page).toHaveURL(/.*workflow-chat.*/);
    await expect(this.page.getByRole('heading', { name: /Workflow chat|Workflow Chat/i })).toBeVisible();
    await expect(this.messageInput).toBeVisible();
    await expect(this.sendButton).toBeVisible();
    await expect(this.chatContainer).toBeVisible();
    await expect(this.connectionStatus).toBeVisible();
  }

  /**
   * Send message
   */
  async sendMessage(message: string) {
    await this.messageInput.fill(message);
    await this.sendButton.click();
  }

  /**
   * Verification message sent
   */
  async verifyMessageSent(message: string) {
    await expect(this.userMessage.filter({ hasText: message })).toBeVisible();
  }

  /**
   * Verify receivedAIresponse
   */
  async verifyAIResponse(timeout = 10000) {
    await expect(this.aiResponse.first()).toBeVisible({ timeout });
  }

  /**
   * Verify connection status
   */
  async verifyConnectionStatus(expectedStatus: 'connected' | 'disconnected' | 'connecting') {
    const statusText = {
      connected: /connect|connected/i,
      disconnected: /disconnect|disconnected/i,
      connecting: /Connecting|connecting/i
    };
    
    await expect(this.connectionStatus).toContainText(statusText[expectedStatus], {
      timeout: 5000
    });
  }

  /**
   * Clear chat history
   */
  async clearChat() {
    await this.clearChatButton.click();
    
    // Confirm clearing
    await this.page.getByRole('button', { name: /confirm|Confirm/i }).click();
    
    // Verify chat has been cleared
    await expect(this.userMessage).toHaveCount(0);
    await expect(this.aiResponse).toHaveCount(0);
  }

  /**
   * Export chat history
   */
  async exportChat() {
    await this.exportChatButton.click();
    
    // Wait for download to start
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.getByRole('button', { name: /Export|Export/i }).click();
    const download = await downloadPromise;
    
    // Verify downloaded file name
    expect(download.suggestedFilename()).toMatch(/chat-export.*\.(json|txt|csv)/);
  }

  /**
   * Open settings panel
   */
  async openSettings() {
    await this.settingsButton.click();
    await expect(this.page.locator('[data-testid="settings-panel"]')).toBeVisible();
  }

  /**
   * ChangeAIModel
   */
  async changeAIModel(modelName: string) {
    await this.openSettings();
    
    // Select model
    await this.page.getByLabel(/AIModel|AI Model/i).selectOption(modelName);
    
    // Save settings
    await this.page.getByRole('button', { name: /save|Save/i }).click();
    
    // Verify settings saved
    await expect(this.page.getByText(/Settings saved|Settings saved/i)).toBeVisible();
  }

  /**
   * Test real-time message flow
   */
  async testRealTimeMessaging() {
    const testMessages = [
      'Hello, please introduce this system',
      'How to upload documents?',
      'How to use cost estimation?'
    ];
    
    for (const message of testMessages) {
      await this.sendMessage(message);
      await this.verifyMessageSent(message);
      await this.verifyAIResponse();
      
      // Wait a short period of time before sending the next message
      await this.page.waitForTimeout(1000);
    }
  }

  /**
   * Test long conversations
   */
  async testLongConversation() {
    const longMessage = "This is a longer test message used to test the system's ability to handle long text.".repeat(10);
    await this.sendMessage(longMessage);
    await this.verifyMessageSent(longMessage);
    await this.verifyAIResponse(15000); // Give long responses more time
  }

  /**
   * Test special characters and emoticons
   */
  async testSpecialCharacters() {
    const specialMessages = [
      'Hello @world! #testing',
      'Test Chinese andemoji 😊🎉',
      'SQL: SELECT * FROM users;',
      'Code: console.log("test");',
      'Link: https://example.com'
    ];
    
    for (const message of specialMessages) {
      await this.sendMessage(message);
      await this.verifyMessageSent(message);
      await this.verifyAIResponse();
      await this.page.waitForTimeout(500);
    }
  }
}
