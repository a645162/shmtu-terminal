import { defineConfig } from 'vitepress'

function resolveBase() {
  const repo = process.env.GITHUB_REPOSITORY?.split('/')[1]
  if (!process.env.GITHUB_ACTIONS || !repo) {
    return '/'
  }
  return repo.endsWith('.github.io') ? '/' : `/${repo}/`
}

export default defineConfig({
  base: resolveBase(),
  lang: 'zh-CN',
  title: '海大终端文档总览',
  description: 'shmtu-terminal 聚合仓库的横切式设计文档与开发日志',
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: true,
  themeConfig: {
    nav: [
      { text: '总览', link: '/' },
      { text: '数据模型', link: '/data-model' },
      { text: '功能规划', link: '/feature-spec' },
      { text: '界面设计', link: '/ui-design' },
      { text: '分类器', link: '/classifier' },
      { text: '开发日志', link: '/dev/index' },
    ],
    sidebar: [
      {
        text: '聚合仓库',
        items: [
          { text: '文档首页', link: '/' },
          { text: '总览与索引', link: '/overview' },
        ],
      },
      {
        text: '专题设计',
        items: [
          { text: '数据模型', link: '/data-model' },
          { text: '功能规划', link: '/feature-spec' },
          { text: '界面设计', link: '/ui-design' },
          { text: '账单统计模块', link: '/statistics-design' },
          { text: '账单分类器', link: '/classifier' },
          { text: 'TOML 格式规范', link: '/toml-format' },
          { text: 'BillParser 解析', link: '/parser' },
          { text: '快速集成 cas_lib', link: '/getting-started' },
          { text: 'Android 集成 cas_lib', link: '/android-integration' },
          { text: 'Android 账单翻译链路', link: '/android-bill-flow' },
          { text: 'Android 多级设置', link: '/android-settings' },
          { text: 'Android 端架构', link: '/android-architecture' },
          { text: 'OCR 模型 v1 / v2 共存', link: '/ocr-model-versions' },
        ],
      },
      {
        text: '开发日志',
        items: [
          { text: '日志归档', link: '/dev/index' },
          { text: '日均消费计算', link: '/dev/daily-average' },
          { text: 'Docker bundled 镜像', link: '/dev/docker-bundled' },
          { text: '多服务监控', link: '/dev/multi-server-monitor' },
        ],
      },
    ],
    outline: [2, 3],
    search: {
      provider: 'local',
    },
    footer: {
      message: 'SHMTU Terminal Docs',
      copyright: 'Copyright © SHMTU Terminal',
    },
  },
})
