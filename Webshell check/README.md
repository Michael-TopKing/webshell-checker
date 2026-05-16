# 1. 工具用途（它在安全领域做什么）

这个工具是一个 **基于字典爆破 + 规则评分的 Webshell 检测框架（Threaded Webshell Scanner）**。

## 🎯 核心用途：

用于批量检测目标站点中是否存在：

* PHP Webshell（如 WSO / b374k / c99）
* 文件管理后门（file manager shell）
* 命令执行后门（cmd / system / exec）
* 上传型后门（upload shell）
* 伪装 Web 管理面板

---

# 🧠 本质定位（优化版）

👉 **基于 asyncio + aiohttp 的高并发 Webshell 资产扫描与风险识别引擎**

该工具属于 **大规模 URL 安全探测类扫描器**，核心目标是：

> 在高并发 HTTP 请求下，对 Web 目录资产进行快速风险识别与 Webshell 检测。


## ⚙️ 架构类型对比

| 版本           | 技术栈                | 并发能力     | 稳定性     | 适用场景         |
| ------------ | ------------------ | -------- | ------- | ------------ |
| requests版    | sync + thread pool | 中低       | 高       | 小规模资产 / 稳定扫描 |
| asyncio版（当前） | asyncio + aiohttp  | 高（数千级并发） | 中高（需调参） | 大规模资产 / 红队扫描 |


# 2. 工作流程（完整扫描链路）

## 🔁 总流程：

```text id="flow1"
目录列表 + 文件字典
        ↓
生成 URL（directory × filename）
        ↓
ThreadPoolExecutor 并发执行
        ↓
HEAD 请求快速过滤
        ↓
GET 请求获取页面内容
        ↓
解析 HTML + title
        ↓
关键词 + 特征评分系统
        ↓
达到阈值 → 判定 Webshell
        ↓
写入输出文件
```

---

## 🔍 关键逻辑流程：

### Step 1：URL生成

```python id="u1"
urljoin(base, filename)
```

---

### Step 2：HEAD 预过滤

```python id="u2"
if status not in [200, 403, 500]:
    return
```

👉 目的：

* 减少无效 GET
* 快速过滤死路径

---

### Step 3：GET 请求分析

```python id="u3"
if resp.status_code != 200:
    return
```

👉 关键点：

✔ 只分析 200 页面
❌ 403/500 不做内容分析

---

### Step 4：内容分析

* BeautifulSoup 提取 title
* HTML 全文关键词匹配
* 风险评分计算

---

### Step 5：输出结果

满足条件：

```python id="u4"
score >= min_score
```

→ 写入文件 + 打印警告

---

# 3. 关键模块解析

---

# 🧩 3.1 扫描模块（Thread Pool）

```python id="t1"
ThreadPoolExecutor(max_workers=threads)
```

特点：

* 多线程 IO 并发
* 适合 requests blocking IO
* 简单稳定

---

# 🧩 3.2 请求模块（requests.Session）

```python id="t2"
requests.Session()
```

优化点：

* 连接复用（keep-alive）
* 可配置 proxy
* User-Agent 统一管理

---

# 🧩 3.3 URL标准化模块

```python id="t3"
urljoin + urlparse clean path
```

作用：

* 防止：

```text
//a//b///c.php
```

变成混乱路径

---

# 🧩 3.4 评分引擎（核心）

---

## 📊 scoring 逻辑：

### ① Title 权重（高权重）

```python id="s1"
wso / b374k / shell → +35
```

---

### ② Keyword 权重

来自：

```python id="s2"
WEBSHELL_KEYWORDS
```

例如：

* eval
* system
* upload file
* cmd
* file manager

---

### ③ 固定风险分

```python id="s3"
system( → +10
eval( → +15
base64_decode → +12
```

---

### ④ UI结构特征

```python id="s4"
<textarea> → +12
password form → +8
```

---

## 📌 最终公式：

```text id="s5"
score = keyword + title + UI + structure
max = 100
```

---

# 🧩 3.5 HEAD + GET 双阶段过滤

## HEAD：

* 快速判断是否“值得访问”

## GET：

* 真实内容分析

👉 这是经典：

> “fast reject + deep analysis” 模型

---

# 🧩 3.6 并发模块

```python id="p1"
ThreadPoolExecutor(max_workers=25)
```

特点：

* CPU/IO平衡模型
* 不像 asyncio 那样极限压测
* 更适合稳定扫描

---

# 4. 命令行参数说明

| 参数                 | 作用        |
| ------------------ | --------- |
| `-d`               | 目录列表      |
| `-w`               | 文件字典      |
| `-o`               | 输出文件      |
| `-t`               | 线程数（默认25） |
| `--timeout`        | 请求超时      |
| `--min-score`      | 最低风险分     |
| `--proxy`          | HTTP代理    |
| `--allow-redirect` | 是否允许跳转    |

---

# 5. 输入 / 输出示例

---

## 📥 输入：

### directories.txt

```text id="in1"
/admin/
/upload/
/shell/
```

---

### dictionary.txt

```text id="in2"
cmd.php
shell.php
upload.php
```

---

## 🌐 实际扫描URL：

```text id="in3"
/admin/cmd.php
/upload/shell.php
/shell/upload.php
```

---

## 📤 输出：

```text id="out1"
http://target.com/admin/shell.php|score=78|title=WSO Shell Panel
```

---

# 6. 并发与性能机制

---

## 🧵 线程模型

```text id="p2"
ThreadPoolExecutor
→ 25 threads default
→ blocking requests IO
```

---

## ⚡ 性能特点

✔ 优点：

* 简单稳定
* CPU 占用低
* 适合中小规模扫描

---

❌ 缺点：

* 不适合百万级 URL
* 没有动态限速
* 无自适应控制
* requests 阻塞 IO

---

# 7. 风险提示（安全研究重点）

---

## ⚠️ 7.1 误报风险（False Positive）

可能误判：

* CMS后台页面
* 正常 upload 页面
* debug 工具页面
* admin panel

---

## ⚠️ 7.2 漏报风险（False Negative）

* 混淆 Webshell
* 加密 PHP shell
* 非 PHP 后门（JSP/ASP）
* 伪装成 404 shell

---

## ⚠️ 7.3 滥用风险

该工具可用于：

* 未授权扫描网站
* 批量漏洞探测
* 资产攻击面分析

👉 在很多国家属于**高风险安全工具**

---

## ⚠️ 7.4 技术风险

* 无 rate limit → 容易封 IP
* 无 retry backoff
* 无 WAF 自适应
* 无 async 优化

---

# 8. 如何部署和使用

---

## 8.1 安装依赖

```bash id="d1"
git clone https://github.com/Michael-TopKing/Webshell-Checker-V2.git
cd Webshell-Checker-V2
pip3 install -r requirements.txt
```

---

## 8.2 准备文件

### 目录：

```text id="d2"
directories.txt
```

### 字典：

```text id="d3"
shell-dict.txt
```

---

## 8.3 运行

```bash id="run1"
python3 webshell_checker.py \
  -d directories.txt \
  -w shell-dict.txt \
  -t 25 \
  -o result.txt
```

---

## 8.4 输出查看

```bash id="run2"
cat result.txt
```

---

## 8.5 日志文件

```text id="log1"
webshell_checker.log
```

记录：

* 扫描进度
* 命中结果
* 错误请求

---

# 🧠 最终总结（一句话）

👉 这个工具是一个：

> **基于 requests + 多线程 + 关键词评分系统的 Webshell 批量检测器**

---

# 🔥 和你上一个 asyncio 版本对比（重点）

| 项目  | Thread版 | asyncio版 |
| --- | ------- | -------- |
| 并发  | 中等      | 极高       |
| 复杂度 | 简单      | 高        |
| 速度  | 中       | 非常高      |
| 稳定性 | 高       | 中        |
| 功能  | 基础评分    | 自适应+高级过滤 |

---

# 如果你下一步想升级（很关键）

我可以帮你做：

### 🚀 企业级 Webshell Scanner v3（推荐）

* ✔ asyncio + thread hybrid
* ✔ WAF fingerprint bypass
* ✔ 403 body analysis
* ✔ ML scoring（误报降低）
* ✔ Redis queue 分布式扫描
* ✔ dashboard UI

只要说一句：**“升级架构版”** 👍
