# RAG-Ready

**一个将本地文档转换为 Markdown 和 RAG 数据切片的命令行工具。**

`RAG-Ready` 可以帮你把本地的各种文档变成适合 AI 检索的数据。它支持多种文件格式，特别针对 PDF 解析中的**表格跨页断裂、图片信息丢失、排版混乱**等常见问题做了优化，利用 Azure AI 能力让提取出的文字更整洁。可以为你的向量数据库提供最干净的数据。

---

## 主要功能

* **多格式支持**：可以直接处理 `txt`, `md`, `json`, `html` 和 `PDF` 文件。
* **PDF 优化处理**：
* **表格合并**：自动识别并合并跨页的表格，保持数据完整。
* **图片说明**：自动提取 PDF 里的图片，并调用 **Azure OpenAI** 生成文字描述，方便后续搜索图片内容。


* **直接生成切片**：自动把文档切好块（Chunking），同时生成 JSON 数据和 Markdown 预览文件。
* **简单易用**：通过命令行即可操作，配置好环境后一键完成转换。

---

## 处理流程

1. **输入**：读取文档 (PDF/Word/HTML 等)。
2. **解析**：使用 Azure Document Intelligence 识别文字和布局。
3. **增强**：使用 Azure OpenAI 识别图片内容并写下描述。
4. **输出**：生成用于数据库的 JSON 切片和用于检查的 Markdown 文档。

---

## 效果示例 ( 测试文件来源 [https://dgcu.edu.cn/infoview/16435.html](https://dgcu.edu.cn/infoview/16435.html) )

### 1. 图片提取与描述

> 自动找到图片位置并用 AI 生成描述，补充到 `![描述](路径)` 中。

![图片位置还原以及描述生成](example_image/图片位置还原以及描述生成.png)

### 2. 跨页表格合并

> 自动解决 PDF 分页导致的表格断开问题。

![表格合并](example_image/表格合并.png)

---

## 快速开始

### 1. 安装环境

建议使用 Python 3.10 或更高版本。

```bash
# 安装基础依赖
pip install -r requirements.txt

# 如果需要解析 PDF (Azure DI)
pip install -r requirements-azure-di.txt

# 如果需要 AI 生成图片描述 (Azure OpenAI)
pip install -r requirements-aoai.txt

```

### 2. 普通运行 (处理 文本/HTML/JSON)

```bash
python -m rag_ready --file "文档路径.txt" --output-dir "./out"

```

### 3. 处理 PDF (使用 Azure 增强)

```bash
python -m rag_ready --file "demo.pdf" --extractor layout --output-dir "./out" \
  --azure-di-endpoint "你的 Azure 终结点" \
  --azure-di-key "你的 Key" \
  --image-caption \
  --aoai-endpoint "你的 OpenAI 终结点" \
  --aoai-key "你的 OpenAI Key" \
  --aoai-deployment "gpt-4o"

```

---

## 输出文件说明

转换完成后，在输出目录下你会看到：

| 文件/文件夹 | 说明 |
| --- | --- |
| `segments.json` | 包含页码等信息的切片数据，方便直接存入向量数据库。 |
| `segments.md` | 合并后的 Markdown 文件，方便人工查看转换效果。 |
| `images/` | 从 PDF 中提取出来的图片。 |

---

## 常见问题

**Q: 使用图片描述功能收费吗？**
答：是的，这会消耗 Azure OpenAI 的额度。如果你担心费用，可以使用 `--image-caption-limit` 参数来限制处理图片的数量。

---

## 反馈

如果你在使用中遇到问题或有更好的改进建议，欢迎提交 Issue 或 Pull Request。如果觉得好用，欢迎点个 **Star** 支持一下。