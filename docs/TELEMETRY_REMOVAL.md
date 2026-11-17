# 第三方遥测清理

本次整理所有待推送提交的可达历史。原 Git、网页快照、依赖和提交 ID 在本机完整备份中保留。发布历史的 SHA 见 [原提交与发布提交映射](PUBLIC_COMMIT_MAP.tsv)。

| 路径或组件 | 清理结果与原因 |
| --- | --- |
| `legal/licenses/p37l/upstream/OpenCV-license.html` | 发布历史移除整个网页快照、Google Tag Manager 初始化、无脚本 iframe、Cloudflare Web Analytics beacon、站点标识和 Cloudflare challenge 配置。保留许可来源链接。 |
| `legal/licenses/p37l/upstream/Qt-obligations.html`、`Qt-modules.html` | 发布历史移除整页及其 Tag Manager 脚本、内联配置和第三方 iframe。源码所需的 LGPL 原文与 QtSvg 声明随附。 |
| 其他供应商网页、脚本、嵌入资源 | 原网页快照及其资源留在本地。用自有的 [许可来源页](license-sources.html) 提供可以离线打开的官方链接。页面没有 JavaScript、嵌入资源或后台请求。 |
| 历史 YOLO worker | 在历史发布副本中于首次依赖导入之前禁用 Ultralytics 的在线探测与遥测入口。归档脚本位于 `archive/yolo/`，新版训练由 RF-DETR 路由。 |
| RF-DETR worker 和独立实验 | 保留已有禁止上报、清理子进程凭证和工作进程离线设置；这些设置仅阻止上报。仓库没有捆绑第三方遥测 SDK。 |

以独立 Edge 浏览器配置打开静态来源页并记录实际网络事件。页面加载完成、6 个链接、0 个脚本，共 1 次本地文档请求，0 次外部或遥测请求。官方链接只响应用户主动点击。旧带令牌页面的证据来自静态检查。

旧快照中可识别的令牌来自第三方网站的遥测或挑战代码，签发方持有账户及配置。是否需要轮换或吊销由签发方确认。原页面及所有相关代码均从本次发布历史排除。
