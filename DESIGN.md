# Smart Router Design System

## Overview

Smart Router 的设计系统是一种**深色科技风格（Dark Tech）**，专为开发者工具、运维监控仪表板和 CLI 工具的可视化界面而设计。视觉语言强调**精确、冷静、高效**，通过高对比度的色彩层级、等宽字体排版和精细的边框系统，传达出系统的可靠性和技术感。

---

## Design Tokens

### Color Palette

#### Background Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--tech-bg` | `#0a0a0f` | 页面主背景，最深层 |
| `--tech-bg-secondary` | `#111118` | 卡片、面板背景 |
| `--tech-bg-tertiary` | `#1a1a24` | 悬浮层、输入框背景 |

#### Border Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--tech-border` | `#1a1a2e` | 默认边框 |
| `--tech-border-hover` | `#2a2a3e` | Hover 状态边框 |

#### Accent Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--tech-accent` | `#00d4aa` | 主强调色（青绿），用于主要操作、活跃状态、成功指示 |
| `--tech-accent-dim` | `rgba(0, 212, 170, 0.1)` | 强调色淡色背景 |
| `--tech-accent-glow` | `rgba(0, 212, 170, 0.15)` | 强调色发光效果 |

#### Text Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--tech-text` | `#e8e8ed` | 主要文字 |
| `--tech-text-secondary` | `#8e8e93` | 次要文字、标签 |
| `--tech-text-muted` | `#636366` | 禁用、占位符、最弱层级文字 |

#### Semantic Status Colors
| Token | Hex | Status |
|-------|-----|--------|
| `--tech-red` | `#e74c3c` | 错误、危险、离线 |
| `--tech-orange` | `#f39c12` | 警告、注意 |
| `--tech-blue` | `#3498db` | 信息、链接 |
| `--tech-green` | `#27ae60` | 成功、在线 |
| `--tech-purple` | `#9b59b6` | 特殊标记 |
| `--tech-pink` | `#e84393` | 高亮标记 |
| `--tech-cyan` | `#00cec9` | 辅助信息 |
| `--tech-indigo` | `#6c5ce7` | 品牌辅助 |
| `--tech-teal` | `#1abc9c` | 辅助成功 |

> 每种状态色均配有 `-dim` 变体（`rgba(color, 0.1)`），用于标签背景、按钮背景、Toast 背景等。

---

### Typography

#### Font Families
| Role | Stack |
|------|-------|
| **Primary (Sans)** | `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif` |
| **Monospace** | `'JetBrains Mono', 'SF Mono', 'Fira Code', ui-monospace, Menlo, monospace` |

#### Type Scale & Style
系统大量使用**小字号 + 大写 + 加宽字距**的组合来营造科技感：

| Context | Size | Weight | Transform | Letter-Spacing | Font |
|---------|------|--------|-----------|----------------|------|
| Page Title | `18px` | `600` | `uppercase` | `0.08em` | Mono |
| Section Label | `10px` | `400` | `uppercase` | `0.05em` | Mono |
| Tab Label | `10px` | `400` | `uppercase` | `0.05em` | Mono |
| Button Text | `12px` | `400` | `uppercase` | `0.05em` | Mono |
| Body Text | `14px` | `400` | `none` | `normal` | Sans |
| Data/Number | `14px` | `400` | `none` | `normal` | Mono + `tabular-nums` |
| Tag/Status | `11px` | `400` | `uppercase` | `0.05em` | Mono |
| Subtitle | `10px` | `400` | `none` | `0.05em` | Mono |

---

### Spacing & Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--content-max-width` | `1280px` (max-w-7xl) | 内容区最大宽度 |
| `--content-padding-x` | `24px` (px-6) | 水平内边距 |
| `--section-gap` | `24px` (space-y-6) | 区块间距 |
| `--card-gap` | `24px` (gap-6) | 卡片间距 |
| `--card-radius` | `4px` | 卡片圆角 |
| `--card-border` | `1px solid #1a1a2e` | 卡片边框 |
| `--input-radius` | `4px` | 输入框圆角 |

---

### Shadows & Effects

| Token | Value | Usage |
|-------|-------|-------|
| `--accent-glow` | `0 0 12px rgba(0, 212, 170, 0.1)` | 主要按钮 hover 光晕 |
| `--status-glow-online` | `0 0 6px rgba(0, 212, 170, 0.4)` | 在线状态发光 |
| `--status-glow-offline` | `0 0 6px rgba(231, 76, 60, 0.4)` | 离线状态发光 |
| `--focus-ring` | `0 0 0 2px rgba(0, 212, 170, 0.05)` | 输入框 focus 环 |

---

### Animation

| Token | Value | Usage |
|-------|-------|-------|
| `--transition-fast` | `0.15s ease` | 行悬停、快速反馈 |
| `--transition-base` | `0.2s ease` | 按钮、卡片、边框状态变化 |
| `--pulse-duration` | `2s` | 状态指示器脉冲 |

---

## Component Primitives

### Tech Card
```css
.tech-card {
  background: #111118;
  border: 1px solid #1a1a2e;
  border-radius: 4px;
  transition: border-color 0.2s ease;
}
.tech-card:hover {
  border-color: #2a2a3e;
}
```
- 无阴影，纯靠边框和背景层级区分
- Hover 仅提升边框亮度，克制不张扬

### Tech Button
```css
.tech-btn {
  background: transparent;
  border: 1px solid #1a1a2e;
  color: #8e8e93;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.75rem;
  transition: all 0.2s ease;
}
```
- 变体：`tech-btn-primary`（强调色边框+文字）、`tech-btn-danger`（红色）、`tech-btn-warning`（橙色）、`tech-btn-muted`（弱化）
- Hover 时边框和文字变为对应强调色，可能伴随微弱背景色和光晕

### Tech Input
```css
.tech-input {
  background: #0a0a0f;
  border: 1px solid #1a1a2e;
  color: #e8e8ed;
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.2s ease;
}
.tech-input:focus {
  border-color: rgba(0, 212, 170, 0.4);
  box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.05);
  outline: none;
}
```
- Placeholder 使用 `--tech-text-muted`

### Tech Tab
```css
.tech-tab {
  background: transparent;
  border: 1px solid transparent;
  color: #636366;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.7rem;
  transition: all 0.2s ease;
}
.tech-tab-active {
  background: rgba(0, 212, 170, 0.08);
  border-color: rgba(0, 212, 170, 0.25);
  color: #00d4aa;
}
```

### Tech Tag
```css
.tech-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 0.65rem;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```
- 变体：`tech-tag-accent`、`tech-tag-danger`、`tech-tag-warning`、`tech-tag-muted`
- 均使用对应颜色的 dim 背景和半透明边框

### Status Indicator
```css
.status-indicator {
  width: 6px;
  height: 6px;
  border-radius: 1px; /* 接近方形的圆角 */
}
.status-online {
  background: #00d4aa;
  box-shadow: 0 0 6px rgba(0, 212, 170, 0.4);
}
```
- 极小尺寸（6px），方形圆角，配合发光阴影
- 脉冲动画：`pulse-glow`（opacity 1 → 0.6 → 1）

### Corner Bracket Decoration
```css
.corner-bracket::before,
.corner-bracket::after {
  content: '';
  position: absolute;
  width: 8px;
  height: 8px;
  border-color: #00d4aa;
  border-style: solid;
  opacity: 0.3;
}
```
- 在卡片或特殊区域的左上角和右下角添加 8px 的 L 形装饰角
- 营造精密仪器/终端的科技感

---

## Layout Patterns

### Page Shell
```
┌─ top-accent-line (1px gradient line) ─┐
│┌────────── Header (sticky) ──────────┐│
││  Logo + Title + Status + Actions    ││
│└─────────────────────────────────────┘│
│┌────────── Main Content ─────────────┐│
││  max-w-7xl mx-auto px-6 py-6        ││
││                                     ││
││  ┌─ ModelOverrideBar ────────────┐  ││
││  ├─ Error Alert (if any) ───────┤  ││
││  ├─ Tab Navigation ─────────────┤  ││
││  │  [DASHBOARD] [MODELS] ...    │  ││
││  └──────────────────────────────┘  ││
││  ┌─ Page Content ────────────────┐  ││
││  │  Cards / Tables / Charts      │  ││
││  └───────────────────────────────┘  ││
│└─────────────────────────────────────┘│
│         Footer (center, mono)         │
└───────────────────────────────────────┘
```

### Grid Background
```css
.bg-tech-grid {
  background-image:
    linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
  background-size: 40px 40px;
}
```
- 极其淡化的网格线（1.5% 不透明度白色）
- 40px 间距，营造底层坐标感，不干扰内容阅读

### Content Hierarchy
1. **Stats Overview** — 顶部横向统计卡片行
2. **Main Grid** — `lg:grid-cols-3`，左侧 1/3 放状态+错误，右侧 2/3 放主内容
3. **Data Tables** — 无边框表格，行底部分割线 `1px solid #1a1a2e`，行 hover 极淡背景

---

## Visual Principles

1. **克制用色**：除强调色 `#00d4aa` 外，所有颜色均为中性灰阶或低饱和状态色。避免渐变背景。
2. **边框即层级**：不用阴影区分层级，而用背景色深度 + 边框亮度。卡片 > 面板 > 页面背景。
3. **等宽即专业**：所有标签、按钮、Tab、状态、数据均使用等宽字体 + 大写，营造 CLI/终端的专业感。
4. **方形美学**：圆角极小（2px–4px），状态指示器接近方形（`border-radius: 1px`），与科技主题呼应。
5. **发光点缀**：仅在状态指示器和主要按钮 hover 时使用微弱发光，不滥用。
6. **网格底色**：底层 40px 淡网格提供空间参考，但不形成视觉噪音。

---

## Usage Examples

### Button Group
```html
<button class="tech-btn px-3 py-1.5 rounded-sm">REFRESH</button>
<button class="tech-btn tech-btn-primary px-3 py-1.5 rounded-sm">START</button>
<button class="tech-btn tech-btn-danger px-3 py-1.5 rounded-sm">STOP</button>
```

### Tag Set
```html
<span class="tech-tag tech-tag-accent">ONLINE</span>
<span class="tech-tag tech-tag-warning">DEGRADED</span>
<span class="tech-tag tech-tag-danger">OFFLINE</span>
<span class="tech-tag tech-tag-muted">UNKNOWN</span>
```

### Card with Corner Brackets
```html
<div class="tech-card corner-bracket p-4 relative">
  <h3 class="text-xs font-mono uppercase tracking-wider text-[#8e8e93]">STATUS</h3>
  <p class="text-sm text-[#e8e8ed] mt-2">All systems operational</p>
</div>
```

---

## File References

- `frontend/src/index.css` — 设计令牌与工具类定义
- `frontend/src/App.tsx` — 页面壳层与导航结构
- `frontend/src/components/Header.tsx` — 头部组件参考
- `frontend/src/components/DashboardPage.tsx` — 布局模式参考
