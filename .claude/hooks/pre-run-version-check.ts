/**
 * Hook: Pre-Run Python Version Check
 * Automatically validates Python 3.13 requirement before command execution
 */

import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export const metadata = {
  name: "pre-run-version-check",
  description: "Validate Python 3.13 requirement before running commands",
  event: "pre-run",
  enabled: true,
};

export async function execute(): Promise<{ success: boolean; message?: string }> {
  try {
    // Check Python version
    const { stdout: versionOutput } = await execAsync(
      "python3 --version 2>&1 || python --version 2>&1"
    );

    const versionMatch = versionOutput.match(/Python (\\d+)\\.(\\d+)\\.(\\d+)/);
    if (!versionMatch) {
      return {
        success: false,
        message: "❌ Could not detect Python version. Ensure Python is installed.",
      };
    }

    const [, major, minor] = versionMatch;
    const majorVer = parseInt(major, 10);
    const minorVer = parseInt(minor, 10);

    // Check for Python 3.13
    if (majorVer !== 3 || minorVer !== 13) {
      return {
        success: false,
        message: \`❌ Python version mismatch!

Required: Python 3.13.x
Current: Python \${majorVer}.\${minorVer}.x

Industry AI Flow requires Python 3.13 for:
- PaddleOCR 3.0.0b0+ (Nightly build)
- LangChain 1.0 compatibility
- Modern async/await patterns

Fix:
1. Install Python 3.13: pyenv install 3.13.0
2. Set local version: pyenv local 3.13.0
3. Recreate venv: python3.13 -m venv .venv
4. Run: ./advanced_version_manager.py

See README.md section "⚠️ Environment Requirements" for details.\`,
      };
    }

    // Run advanced_version_manager.py for comprehensive check
    try {
      const { stdout: managerOutput } = await execAsync(
        "python3 ./advanced_version_manager.py --quiet"
      );

      // If exit code is 0, all checks passed
      return {
        success: true,
        message: "✅ Python 3.13 environment validated successfully",
      };
    } catch (managerError: any) {
      // Manager returned non-zero exit code
      return {
        success: false,
        message: \`⚠️ Python 3.13 detected but dependency issues found.

Run for detailed report:
  python3 ./advanced_version_manager.py

Common issues:
- PaddleOCR not installed (Nightly build required)
- Missing critical modules (opencv-python, pillow, numpy)
- Optional AI modules incompatible (torch, langchain)

Fix:
  ./install_python313_paddleocr.sh\`,
      };
    }
  } catch (error: any) {
    return {
      success: false,
      message: \`❌ Version check failed: \${error.message}

Ensure Python 3.13 is installed and accessible.\`,
    };
  }
}
