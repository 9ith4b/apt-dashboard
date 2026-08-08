import {
  BoxIcon,
  CrosshairIcon,
  Globe2Icon,
  MailIcon,
  NetworkIcon,
  UserRoundIcon,
  type LucideIcon,
} from "lucide-react"

export type FeedItem = {
  id: string
  title: string
  relevance: number
  actor: string
  technique: string
  reason: string
  source: string
  sourceInitials: string
  age: string
  confidence: "high" | "medium" | "low"
  icon: LucideIcon
  summary: string
}

export const feedItems: FeedItem[] = [
  {
    id: "lazarus-fake-interview",
    title: "Lazarus 利用虚假技术面试向开发者投递恶意 NPM 包",
    relevance: 94,
    actor: "Lazarus Group",
    technique: "虚假招聘",
    reason: "命中关注对象、已知 Campaign 行为与 6 个可观测对象",
    source: "Microsoft Security Blog",
    sourceInitials: "MS",
    age: "18 分钟前",
    confidence: "high",
    icon: CrosshairIcon,
    summary:
      "威胁行为者冒充知名公司招聘人员，通过 Telegram 和招聘网站联系开发者，诱导其运行测试任务并安装恶意 NPM 包。该包会窃取开发环境信息并建立持久访问通道。",
  },
  {
    id: "apt28-oauth",
    title: "APT28 针对政府外交机构的凭据窃取活动",
    relevance: 88,
    actor: "APT28",
    technique: "凭据访问",
    reason: "命中关注对象、使用新型 OAuth 令牌窃取技术",
    source: "The Record",
    sourceInitials: "TR",
    age: "1 小时前",
    confidence: "medium",
    icon: UserRoundIcon,
    summary:
      "研究人员观察到针对政府与外交机构的新型 OAuth 钓鱼链路，攻击者尝试获取长期有效的云端访问权限。",
  },
  {
    id: "unc5221-edge-rce",
    title: "UNC5221 利用未认证 RCE 在边缘设备上建立持久化",
    relevance: 76,
    actor: "UNC5221",
    technique: "持久化",
    reason: "涉及公开漏洞目录中的边缘设备漏洞，已观测到活跃利用",
    source: "CISA ICS-CERT",
    sourceInitials: "CS",
    age: "2 小时前",
    confidence: "medium",
    icon: NetworkIcon,
    summary:
      "攻击者利用边缘设备上的未认证远程代码执行漏洞部署持久化组件，并通过多层基础设施隐藏控制流量。",
  },
  {
    id: "colors-js-supply-chain",
    title: "开源依赖包 colors.js 被植入挖矿模块的供应链事件",
    relevance: 72,
    actor: "未归因",
    technique: "供应链",
    reason: "影响超过 3,200 个 NPM 项目，下载量持续上升",
    source: "GitHub Advisory",
    sourceInitials: "GH",
    age: "3 小时前",
    confidence: "medium",
    icon: BoxIcon,
    summary:
      "恶意版本通过依赖更新传播挖矿组件。当前证据不足以将事件归因到已知攻击组织。",
  },
  {
    id: "fin7-carbarnak",
    title: "FIN7 使用钓鱼邮件投递新版 Carbanak 恶意载荷",
    relevance: 68,
    actor: "FIN7",
    technique: "钓鱼投递",
    reason: "命中文本相似特征，载荷与历史样本高度相似",
    source: "VirusTotal",
    sourceInitials: "VT",
    age: "4 小时前",
    confidence: "low",
    icon: MailIcon,
    summary:
      "样本与历史 Carbanak 家族存在较高代码相似度，但当前归因仍需要更多直接证据。",
  },
  {
    id: "apt10-telecom",
    title: "东南亚电信行业遭疑似 APT10 的数据外泄活动",
    relevance: 58,
    actor: "APT10",
    technique: "数据窃取",
    reason: "多家运营商受影响，疑似利用 VPN 网关漏洞",
    source: "BleepingComputer",
    sourceInitials: "BB",
    age: "5 小时前",
    confidence: "low",
    icon: Globe2Icon,
    summary:
      "多家电信运营商出现异常数据传输。现有基础设施与 APT10 历史活动有弱关联，仍待审核。",
  },
]
