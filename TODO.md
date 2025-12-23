# TODO

## GitHub 链接支持

### 目标
支持解析 GitHub 仓库链接，提取项目信息。

### 需要处理的链接类型
- `github.com/user/repo` - 仓库主页
- `github.com/user/repo/blob/...` - 文件链接
- `github.com/user/repo/tree/...` - 目录链接
- `github.com/user/repo/issues/...` - Issue 链接
- `github.com/user/repo/pull/...` - PR 链接

### 需要提取的信息
- [ ] 仓库名称
- [ ] 仓库描述
- [ ] Star 数量
- [ ] 主要编程语言
- [ ] 最近更新日期
- [ ] README 内容（用于摘要生成）
- [ ] Topics/Tags

### 实现方案
1. 检测 GitHub URL 格式
2. 使用 GitHub API 获取仓库信息
   - 需要处理 rate limit（考虑 token 认证）
3. 解析 README.md 内容
4. 特殊处理 Issues/PRs 页面

### API 参考
```
GET https://api.github.com/repos/{owner}/{repo}
GET https://api.github.com/repos/{owner}/{repo}/readme
```

---

## 知乎链接支持

### 目标
支持解析知乎文章和回答链接。

### 需要处理的链接类型
- `zhuanlan.zhihu.com/p/{id}` - 专栏文章
- `zhihu.com/question/{qid}/answer/{aid}` - 回答
- `zhihu.com/question/{qid}` - 问题页面

### 需要提取的信息
- [ ] 标题
- [ ] 作者
- [ ] 发布/更新日期
- [ ] 正文内容
- [ ] 点赞数（可选）

### 实现挑战
1. 知乎有反爬机制，需要模拟浏览器请求
2. 部分内容需要登录才能查看
3. 页面结构可能动态变化

### 实现方案
1. 添加知乎专用 User-Agent
2. 尝试提取 JSON-LD 结构化数据
3. 使用 CSS 选择器提取正文
4. 备选：使用 Selenium/Playwright 渲染

### 可能需要的 Headers
```python
headers = {
    "User-Agent": "Mozilla/5.0 ...",
    "Cookie": "可选的登录 cookie",
    "Referer": "https://www.zhihu.com/"
}
```

---

## 优先级

1. **High**: GitHub 仓库主页解析
2. **Medium**: 知乎专栏文章解析
3. **Low**: GitHub Issues/PRs 解析
4. **Low**: 知乎回答解析

---

## 其他待办

- [ ] 支持更多学术网站
  - [ ] Google Scholar
  - [ ] Semantic Scholar
  - [ ] OpenReview
- [ ] 支持 Twitter/X 链接
- [ ] 支持 YouTube 视频链接（提取视频信息）
- [ ] 图片 OCR 支持
- [ ] PDF 直链下载解析（非 ArXiv）
