# Knowledge Notes

这是一个多主题知识笔记静态展示站，基于 [knowledge-site-template](https://github.com/ljxpython/knowledge-site-template) 构建。当前第一份 collection 是 `open_deep_research` 中的 LangGraph / LangChain 学习文档，后续可以继续加入其他技术主题。

当前 LangGraph / LangChain 源文档来自：

```text
/Users/lijiaxin/PyCharmMiscProject/research/open_deep_research/docs/langgraph-langchain-learning
```

## 刷新内容

```bash
npm run import:course
npm run assets:check
npm test
npm run build
```

导入器只读取 Markdown、复制内容并重写链接。它不会执行文档中的 Python、`uv`、模型调用、搜索、MCP 或其他外部服务命令。

## 阅读提示

文档中的命令属于读者手动运行的示例。部分命令需要 API Key、外部服务权限，或可能产生模型与搜索费用。构建、测试、预览和部署只生成静态页面，不会执行这些命令。

## 本地预览

```bash
npm install
npm run import:course
npm run dev
```

## 项目位置

```text
/Users/lijiaxin/PyCharmMiscProject/research/knowledge-notes
```

目标仓库名：`knowledge-notes`。
