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

### 状态
⚠️ **受限支持** - 知乎有严格的反爬保护（zse-ck JavaScript验证），无法自动抓取。

### 已尝试的方案
1. ❌ 移动端 User-Agent - 仍返回 403
2. ❌ curl_cffi (模拟浏览器 TLS) - 仍返回 403
3. ❌ Playwright + Stealth - 触发验证码页面
4. ❌ 直接调用 Zhihu API - 需要认证

### 当前解决方案
- 检测到知乎链接时，返回友好提示
- 建议用户手动复制内容，使用文本模式输入

### 可能的改进方向
- 支持用户提供登录 Cookie
- 使用第三方 API 服务（如 Jina Reader）
- 等待知乎放松限制

---

## 优先级

1. **High**: GitHub 仓库主页解析
2. **Low**: GitHub Issues/PRs 解析
3. **On Hold**: 知乎 - 需要等待更好的解决方案

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
