// Shared, DOM-free contract used by the editor and the Dashboard adapter.
import { DEFAULT_THEME, THEME_SCHEMA, REGION_PROPERTIES } from '../generated/theme-data.js';

export const FONTS = {
  system: '"Segoe UI", "Microsoft YaHei UI", system-ui, sans-serif',
  serif: '"Noto Serif SC", "Songti SC", SimSun, Georgia, serif',
  mono: '"Cascadia Code", Consolas, "Microsoft YaHei UI", monospace',
};

export function validateDeclarations(value) {
  if (typeof value !== 'string' || value.length > 2000) throw new Error('分区 CSS 超过长度限制');
  for (const item of value.split(';').filter(part => part.trim())) {
    const colon = item.indexOf(':');
    const property = item.slice(0, colon).trim();
    const content = item.slice(colon + 1);
    if (colon < 0 || !REGION_PROPERTIES.includes(property)) throw new Error('分区 CSS 包含未支持的属性');
    if (!/^[\w\s#.,()%+\-]+$/.test(content)) throw new Error('分区 CSS 请使用静态颜色、尺寸与阴影值');
    for (const match of content.matchAll(/([\w-]+)\s*\(/g)) {
      if (!['rgb', 'rgba', 'hsl', 'hsla'].includes(match[1].toLowerCase())) {
        throw new Error('分区 CSS 支持 rgb/rgba/hsl/hsla 颜色函数');
      }
    }
  }
  return value.trim();
}

export function validateTheme(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('请提供风格对象');
  for (const key of Object.keys(input)) {
    if (!Object.hasOwn(DEFAULT_THEME, key)) throw new Error(`未知风格字段：${key}`);
  }
  const value = { ...structuredClone(DEFAULT_THEME), ...input };
  for (const [key, rule] of Object.entries(THEME_SCHEMA.properties)) {
    if (key === 'regions') continue;
    const item = value[key];
    if (rule.const !== undefined && item !== rule.const) throw new Error('风格版本需要升级');
    if (rule.enum && !rule.enum.includes(item)) throw new Error(`请选择有效的 ${key}`);
    if (rule.type === 'string' && (typeof item !== 'string' || !item.trim()
      || (rule.maxLength && item.length > rule.maxLength)
      || (rule.pattern && !new RegExp(rule.pattern).test(item)))) throw new Error(`请检查 ${key}`);
    if (['integer', 'number'].includes(rule.type) && (typeof item !== 'number'
      || !Number.isFinite(item) || (rule.type === 'integer' && !Number.isInteger(item))
      || item < rule.minimum || item > rule.maximum)) throw new Error(`请检查 ${key} 的范围`);
  }
  if (!value.regions || typeof value.regions !== 'object' || Array.isArray(value.regions)) {
    throw new Error('请提供分区样式对象');
  }
  for (const key of Object.keys(value.regions)) {
    if (!['sidebar', 'header', 'card'].includes(key)) throw new Error('未知样式分区');
  }
  value.regions = Object.fromEntries(['sidebar', 'header', 'card'].map(key =>
    [key, validateDeclarations(value.regions[key] ?? '')]));
  value.name = value.name.trim();
  return value;
}

export function luminance(hex) {
  const rgb = hex.match(/[0-9a-f]{2}/gi).map(part => parseInt(part, 16) / 255)
    .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
}

export function contrast(first, second) {
  const a = luminance(first), b = luminance(second);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function hsl(hex) {
  const [r, g, b] = hex.match(/[0-9a-f]{2}/gi).map(part => parseInt(part, 16) / 255);
  const high = Math.max(r, g, b), low = Math.min(r, g, b), delta = high - low;
  const light = (high + low) / 2;
  const saturation = delta === 0 ? 0 : delta / (1 - Math.abs(2 * light - 1));
  let hue = 0;
  if (delta) hue = high === r ? ((g - b) / delta) % 6 : high === g ? (b - r) / delta + 2 : (r - g) / delta + 4;
  return `${((hue * 60 + 360) % 360).toFixed(2)} ${(saturation * 100).toFixed(2)}% ${(light * 100).toFixed(2)}%`;
}

export function themeCSS(input, root = 'html[data-plugin-appearance]') {
  const t = validateTheme(input);
  const foreground = contrast(t.primary, '#FFFFFF') >= contrast(t.primary, '#000000') ? '#FFFFFF' : '#000000';
  const shadow = { none: 'none', soft: '0 4px 20px #0000000d', crisp: `3px 3px 0 ${t.border}` }[t.shadow];
  const tokens = {
    primary: t.primary, 'primary-foreground': foreground, accent: t.primary, 'accent-foreground': foreground,
    background: t.background, foreground: t.text, card: t.surface, 'card-foreground': t.text,
    popover: t.surface, 'popover-foreground': t.text, muted: t.background, 'muted-foreground': t.muted,
    secondary: t.background, 'secondary-foreground': t.text, border: t.border, input: t.border, ring: t.primary,
  };
  const variables = Object.entries(tokens).map(([key, value]) => `--color-${key}:${hsl(value)}!important;`).join('');
  const sizes = { xs: 0.75, sm: 0.875, base: 1, lg: 1.125, xl: 1.25, '2xl': 1.5 };
  const typography = Object.entries(sizes).map(([key, scale]) => `--typography-font-size-${key}:${t.font_size * scale}px!important;`).join('');
  const region = (selector, declarations) => declarations ? `${root} ${selector}{${declarations.split(';').filter(s => s.trim()).map(s => `${s}!important;`).join('')}}` : '';
  return `${root}{${variables}${typography}
    --typography-font-family-base:${FONTS[t.font]}!important;--typography-line-height-normal:${t.line_height}!important;
    --layout-sidebar-width:${t.sidebar_width}px!important;--layout-header-height:${t.header_height}px!important;
    --visual-radius-sm:${Math.max(0, t.radius - 4)}px!important;
    --visual-radius-md:${Math.max(0, t.radius - 2)}px!important;--visual-radius-lg:${t.radius}px!important;
    --visual-radius-xl:${t.radius + 4}px!important;--visual-shadow-sm:${shadow}!important;--visual-shadow-md:${shadow}!important;
    font-family:${FONTS[t.font]};font-size:${t.font_size}px;line-height:${t.line_height};
    background:${t.background};color:${t.text};color-scheme:${t.mode === 'system' ? 'light dark' : t.mode};}
    ${root} [data-dashboard-sidebar]{background:color-mix(in srgb, ${t.background} 85%, transparent)!important;color:${t.text}!important;backdrop-filter:blur(20px);}
    ${root} [data-dashboard-header]{background:color-mix(in srgb, ${t.surface} 88%, transparent)!important;color:${t.text}!important;backdrop-filter:blur(20px);}
    ${root} [data-dashboard-main]{background:${t.background}!important;color:${t.text}!important;}
    ${root} .bg-card{background:${t.surface}!important;color:${t.text}!important;border-color:${t.border}!important;
      border-radius:${t.radius}px!important;box-shadow:${shadow}!important;}
    @media(min-width:1024px){
      ${root} [data-dashboard-sidebar-layout]{order:${t.sidebar_side === 'right' ? 2 : 0};}
      ${root} [data-dashboard-header]:not([data-dashboard-header-collapsed="true"]){height:${t.header_height}px!important;min-height:${t.header_height}px!important;}
      ${root} [data-dashboard-header]{margin-left:0!important;width:100%!important;}
      ${root} [data-dashboard-workspace-content]{max-width:${t.content_width}px;margin-inline:auto;padding:${t.gap}px;box-sizing:border-box;}
      ${t.sidebar_side === 'right' ? `${root} [data-dashboard-sidebar]{left:auto;right:0;border-left:1px solid ${t.border};border-right:0;}
      ${root} [data-dashboard-sidebar][data-dashboard-sidebar-mode="hover"]{position:absolute;}
      ${root} [data-dashboard-sidebar][data-dashboard-sidebar-mode="hover"][data-dashboard-sidebar-visually-open="false"]{left:0;right:auto;}` : ''}
    }
    @media(prefers-reduced-transparency:reduce){${root} [data-dashboard-sidebar],${root} [data-dashboard-header]{background:${t.surface}!important;backdrop-filter:none;}}
    ${region('[data-dashboard-sidebar]', t.regions.sidebar)}
    ${region('[data-dashboard-header]', t.regions.header)}
    ${region('.bg-card', t.regions.card)}`;
}
