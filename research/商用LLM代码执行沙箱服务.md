<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 调研下目前商用的LLM 代码执行的sanbox服务和价格.

目前，商用LLM代码执行沙箱服务主要包括E2B、Northflank、Koyeb、Modal和Vercel Sandbox等，这些平台提供隔离的微VM或容器环境，支持AI代理安全运行生成的代码。[^1_1][^1_2][^1_3]

## 主要服务概述

这些服务针对LLM代理设计，使用Firecracker或gVisor等技术实现隔离，支持Python/JS等语言，长会话和GPU选项。[^1_4][^1_5][^1_1]

- E2B：AI-first SDK，Fortune 100公司使用，支持自定义CPU/RAM，会话至24小时。[^1_3]
- Northflank：生产级微VM，无限会话，支持BYOC，处理数百万隔离任务。[^1_1][^1_4]
- Koyeb：无服务器容器，网络隔离，唤醒<200ms，支持GPU和CI/CD。[^1_2][^1_5]
- Modal：函数级执行，快速冷启动，云卷挂载，适合数据管道。[^1_6][^1_2]
- Vercel Sandbox：微VM，支持Node.js/Python，执行至5小时，集成Vercel生态。[^1_7]


## 定价比较

多数采用按使用付费（pay-as-you-go），有免费额度。以下表格总结关键定价（2026年数据，美元，约合CAD 1.35倍；GPU更高）：[^1_5][^1_3][^1_4][^1_6][^1_7]


| 服务 | 免费额度 | CPU定价示例 | 内存定价示例 | 月费/其他 |
| :-- | :-- | :-- | :-- | :-- |
| E2B | \$100使用+ Hobby免费 | \$0.000014/vCPU/秒 (1 vCPU) | \$0.0000045/GiB/秒 | Pro \$150/月 + 使用 |
| Northflank | Sandbox免费计划 | \$0.01667/vCPU/小时 | \$0.00833/GB/小时 | GPU H100 \$2.74/小时全包 |
| Koyeb | 免费层 + \$0.000001/秒起 | ~\$0.0036/小时起 | 包含在计算中 | Pro \$29/月 + \$100计算 |
| Modal | \$0/\$30/\$250免费计算/月 | \$0.00003942/核心/秒 | \$0.00000672/GiB/秒 | 按周期付费，无闲置费 |
| Vercel | Hobby 5小时CPU/420GB-hr | \$0.128/小时 (Pro起) | \$0.0212/GB-hr | 创建\$0.60/百万 |

实际成本依运行时长/资源而定，轻量任务每月<10美元，重负载需GPU则更高。[^1_8][^1_4]
<span style="display:none">[^1_10][^1_11][^1_12][^1_13][^1_14][^1_15][^1_16][^1_17][^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_9]</span>

<div align="center">⁂</div>

[^1_1]: https://northflank.com/blog/best-code-execution-sandbox-for-ai-agents

[^1_2]: https://www.koyeb.com/blog/top-sandbox-code-execution-platforms-for-ai-code-execution-2026

[^1_3]: https://e2b.dev/pricing

[^1_4]: https://northflank.com/blog/top-ai-sandbox-platforms-for-code-execution

[^1_5]: https://www.koyeb.com/blog/koyeb-sandboxes-fast-scalable-fully-isolated-environments-for-ai-agents

[^1_6]: https://modal.com/pricing

[^1_7]: https://vercel.com/docs/vercel-sandbox/pricing

[^1_8]: https://betterstack.com/community/comparisons/best-sandbox-runners/

[^1_9]: https://simonw.substack.com/p/llm-predictions-for-2026-shared-with

[^1_10]: https://www.softwareseni.com/understanding-ai-agent-sandboxing-why-production-deployment-remains-unsolved-in-2026

[^1_11]: https://mcpmarket.com/server/sandbox-1

[^1_12]: https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025

[^1_13]: https://flexprice.io/blog/replit-ai-pricing-guide

[^1_14]: https://vndee.github.io/llm-sandbox/

[^1_15]: https://www.reddit.com/r/LocalLLM/comments/1kgq8c6/sandboxer_forkable_code_execution_server_for_llms/

[^1_16]: https://www.reddit.com/r/LocalLLaMA/comments/1n2u7yk/a_flatrate_api_for_open_llms_20mo_for_100/

[^1_17]: https://aiagentsdirectory.com/agent/e2b

[^1_18]: https://replit.com/pricing

[^1_19]: https://northflank.com/blog/top-vercel-sandbox-alternatives-for-secure-ai-code-execution-and-sandbox-environments

[^1_20]: https://e2b.dev

[^1_21]: https://northflank.com/pricing

[^1_22]: https://northflank.com/docs/v1/application/billing/pricing-on-northflank

[^1_23]: https://northflank.com/blog/codesandbox-alternatives

[^1_24]: https://northflank.com

[^1_25]: https://www.koyeb.com/pricing

[^1_26]: https://onecompiler.com/apis/pricing

[^1_27]: https://www.daytona.io/pricing

[^1_28]: https://vercel.com/pricing

[^1_29]: https://www.g2.com/products/northflank/pricing


---

# 调研下中国的sandbox服务商,然后再对比下上述总结的厂商,注意汇率换算.

中国商用LLM代码沙箱服务以阿里云AgentRun Code Interpreter和PPIO Agent沙箱为主，前者支持Python/JS代码执行、文件管理和会话控制，目前免费试用（仅函数资源计费）；后者兼容E2B接口，提供<200ms启动、多语言和浏览器模拟。[^2_1][^2_2]

腾讯云有LLM Sandbox模板，但更偏Agent Runtime而非独立商用API。[^2_3][^2_4]

## 服务对比

国际服务（如E2B/Northflank）生态成熟、GPU支持强；中国服务成本更低、延迟优化（针对国内访问），但功能稍简（PPIO强于浏览器/文件，阿里云强于API集成）。汇率：1 USD ≈ 7.2 CNY，1 USD ≈ 1.38 CAD（2026.2数据）。[^2_5][^2_6]


| 服务 | 免费额度/试用 | CPU定价 (USD/CNY/CAD) 示例 | 内存定价 (USD/CNY/CAD) 示例 | 优势/劣势 |
| :-- | :-- | :-- | :-- | :-- |
| **阿里云 Code Interpreter** | 免费试用，仅资源计费 | 未公开，按FC函数 ~\$0.0000167/GB-s (~0.00012 CNY / 0.000023 CAD) | 同上 | API丰富、低成本；需阿里账号，无GPU显式。 |
| **PPIO Agent沙箱** | 内测申请 | 未精确，按示例1核5min ~0.01 CNY (~0.0014 USD / 0.0019 CAD) | 分项按秒，节省40%+ | E2B兼容、毫秒启动；内测阶段。 |
| E2B | \$100 + Hobby | \$0.000014/s (~0.0001 CNY / 0.000019 CAD) | \$0.0000045/GiB/s | 成熟SDK；稍贵。[^2_5] |
| Northflank | Sandbox免费 | \$0.01667/hr (~0.12 CNY / 0.023 CAD) | \$0.00833/GB/hr | 生产级；小时计费贵于秒。[^2_6] |
| Modal | \$0-250免费计算/月 | \$0.00003942/s (~0.00028 CNY / 0.000054 CAD) | \$0.00000672/GiB/s | 快启动；函数导向。[^2_7] |

中国服务对Calgary用户访问可能需VPN，PPIO示例显示小任务极低成本（<0.01 CNY），适合测试；国际服务免费额度高，适合开发。[^2_8]
<span style="display:none">[^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_19][^2_20][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://ppio.cn/ai-computing/sandbox

[^2_2]: https://help.aliyun.com/zh/functioncompute/fc/sandbox-sandbox-code-interepreter

[^2_3]: interests.local_large_language_models

[^2_4]: https://cloud.tencent.com/document/product/1207/122668

[^2_5]: https://cloud.tencent.com/document/practice/1207/122668

[^2_6]: https://e2b.dev/pricing

[^2_7]: https://northflank.com/blog/top-ai-sandbox-platforms-for-code-execution

[^2_8]: https://modal.com/pricing

[^2_9]: https://betterstack.com/community/comparisons/best-sandbox-runners/

[^2_10]: https://www.fortinet.com/cn/products/fortiaigate

[^2_11]: https://www.w3.org/2024/01/webevolve-series-events/annual-2025/slides/xinyi-ren.pdf

[^2_12]: https://github.com/yzfly/Awesome-MCP-ZH

[^2_13]: https://github.com/HqWu-HITCS/Awesome-Chinese-LLM

[^2_14]: https://github.com/leezhuuuuu/Code-Interpreter-Api

[^2_15]: https://ppio.com/docs/llms-full.txt?from=ppinfra

[^2_16]: https://ppio.com/ai-computing/sandbox

[^2_17]: https://help.aliyun.com/zh/functioncompute/fc/aio-sandbox

[^2_18]: https://cloud.tencent.cn/document/product/851/107877

[^2_19]: https://help.aliyun.com/zh/model-studio/code-interpreter

[^2_20]: https://github.com/songquanpeng/one-api


---

# 这些中国厂商与国际LLM sandbox的性能基准对比

中国厂商（如阿里云AIO Sandbox/PPIO）和国际LLM沙箱（如E2B/Northflank/Modal）的性能基准有限，直接对比数据稀缺，主要来自厂商自测或通用LLM评估（非沙箱专属）。PPIO/AIO强调启动<200ms和文件I/O 15x提升，E2B在代码执行准确率/速度领先OpenAI等。[^3_1][^3_2][^3_3][^3_4]

## 关键基准指标

- **启动延迟**：PPIO/AIO <200ms（高并发优），E2B/Modal ~100-500ms，Northflank容器~秒级。[^3_2][^3_5][^3_3]
- **代码执行**：E2B 92%准确/1.2s（512MB），优于GPT-3 (87%/2.5s)；阿里云AIO文件读写0.15s（15x vs 多容器2.3s）。[^3_4][^3_1]
- **隔离/并发**：PPIO Firecracker VM级隔离，支持大规模并发；E2B gVisor/Firecracker类似，Modal函数级快。[^3_5][^3_6]
- **LLM整体性能**：中国模型（如DeepSeek/Qwen）在Arena/数学基准超国际（1446 vs 1413），间接利好沙箱。[^3_7][^3_8]


## 对比表格

| 指标 | 中国厂商 (阿里云/PPIO) | 国际 (E2B/Modal/Northflank) | 胜出方/备注 |
| :-- | :-- | :-- | :-- |
| 启动时间 | <200ms [^3_2][^3_3] | 100ms-1s [^3_1][^3_5] | 中国（高频Agent优） |
| 执行速度 | 文件I/O 0.15s (15x提升) [^3_4] | 1.2s代码任务 [^3_1] | 中国I/O强，E2B代码准确92% |
| 内存效率 | 低开销VM [^3_6] | 512MB-2GB [^3_1] | 平手，依任务 |
| 并发/隔离 | VM级，高并发 [^3_6] | 微VM/gVisor，高安全 [^3_5] | 平手，PPIO国内低延迟 |
| 基准准确率 | LLM级87-91% [^3_8] | 沙箱92% [^3_1] | E2B专属强 |

中国服务延迟对亚洲优（10-50ms浏览器），国际生态/SDK更全；实际选型依场景测试。[^3_9][^3_7]
<span style="display:none">[^3_10][^3_11][^3_12][^3_13][^3_14][^3_15][^3_16]</span>

<div align="center">⁂</div>

[^3_1]: https://cheatsheet.md/zh/llm-leaderboard/e2b-code-interpreter

[^3_2]: https://blog.csdn.net/bumblexbee/article/details/148879175

[^3_3]: https://ppio.cn/docs/sandbox/overview

[^3_4]: https://blog.csdn.net/u012094427/article/details/154502631

[^3_5]: https://e2b.dev/blog/e2b-sandbox

[^3_6]: https://www.ciie.org/hall/f/exhibition-hall/exhibits/1f5982426f2140679114b961ebbc2326/view

[^3_7]: https://pinggy.io/blog/usa_europe_china_llm_comparison/

[^3_8]: https://www.nature.com/articles/s41598-025-23973-1

[^3_9]: interests.local_large_language_models

[^3_10]: https://juejin.cn/post/7567040496050405395

[^3_11]: https://github.com/uhub/awesome-chatgpt

[^3_12]: https://developer.aliyun.com/article/1672573

[^3_13]: https://docs.feishu.cn/v/wiki/DyF5w3btkirb4Nk7iWWcuK6Nn0c/a5

[^3_14]: https://www.aneasystone.com/category/llm/

[^3_15]: https://github.com/CoderSJX/AI-Resources-Central

[^3_16]: https://am.vontobel.com/en/insights/2026-large-language-models-outlook


---

# 国际沙箱如E2B支持哪些编程语言

E2B等国际沙箱主要支持Python（核心，用于数据分析）和JavaScript/TypeScript（Node.js环境，支持ESM/await），Beta阶段扩展R、Java和Bash；自定义模板可加任意语言。[^4_1][^4_2][^4_3]

## 支持语言详情

- **Python**：完整pip、matplotlib/数据科学库，AI代码首选。[^4_4][^4_2]
- **JavaScript/TypeScript**：Node.js运行，自动Promise解析。[^4_3][^4_1]
- **其他**：R（数据）、Java（Beta）、Bash（脚本）；Northflank/Modal支持任意Docker语言。[^4_2][^4_5]


## 快速对比

| 服务 | 核心语言 | 扩展语言 | 自定义支持 |
| :-- | :-- | :-- | :-- |
| E2B | Python, JS/TS | R, Java, Bash (Beta) | 是（模板）[^4_2] |
| Northflank | 任意（Docker） | 全语言 | OCI镜像 |
| Modal | Python（SDK） | 任意自定义镜像 | 是[^4_5] |
| Koyeb | 容器任意 | 全语言 | Docker[^4_6] |

E2B SDK简单集成LLM，适合你的AI开发栈（如Python/Swift项目）。[^4_7][^4_4]
<span style="display:none">[^4_10][^4_11][^4_12][^4_13][^4_14][^4_15][^4_16][^4_8][^4_9]</span>

<div align="center">⁂</div>

[^4_1]: https://www.npmjs.com/package/e2b/v/0.16.2-beta.57

[^4_2]: https://e2b.dev/docs/code-interpreting/supported-languages

[^4_3]: https://e2b.dev/docs/code-interpreting/supported-languages/javascript

[^4_4]: https://github.com/e2b-dev/code-interpreter

[^4_5]: https://northflank.com/blog/top-modal-sandboxes-alternatives-for-secure-ai-code-execution

[^4_6]: https://www.koyeb.com/blog/top-sandbox-code-execution-platforms-for-ai-code-execution-2026

[^4_7]: https://github.com/e2b-dev/e2b

[^4_8]: https://e2b.dev/docs

[^4_9]: https://e2b.dev

[^4_10]: https://vndee.github.io/llm-sandbox/languages/

[^4_11]: https://mcp.so/server/e2b

[^4_12]: https://northflank.com/blog/best-code-execution-sandbox-for-ai-agents

[^4_13]: https://aiagentsdirectory.com/agent/e2b

[^4_14]: https://e2b.dev/docs/sandbox/list

[^4_15]: https://github.com/e2b-dev/e2b/blob/main/README.md

[^4_16]: https://adasci.org/mastering-ai-code-execution-in-secure-sandboxes-with-e2b/
