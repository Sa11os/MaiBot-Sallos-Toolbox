// Dashboard 1.9.9 home layout. Keep card data, DOM order and native editing intact.
export function homeLayoutCSS(root, gap) {
  const page = `${root} [data-home-page]`;
  const grid = `${page} [data-home-summary-cards]:not(:has([data-home-card-edit-overlay]))`;
  const card = `${grid}>[data-home-card-id]`;
  return `
    ${root} [data-dashboard-workspace-content]:has([data-home-page]){
      max-width:none!important;width:100%;height:auto!important;min-height:100%;padding:${gap}px;}
    ${root} [data-dashboard-main] div:has(>[data-dashboard-scrollbar-viewport] [data-home-page]){
      height:auto!important;overflow:visible!important;}
    ${root} [data-dashboard-main] [data-dashboard-scrollbar-viewport]:has([data-home-page]){
      height:auto!important;overflow:visible!important;}
    ${page}{container:toolbox-home / inline-size;padding:0!important;}
    ${grid}{grid-template-columns:repeat(12,minmax(0,1fr))!important;grid-template-rows:none!important;
      grid-auto-rows:auto;gap:clamp(12px,1.2vw,${gap}px)!important;align-items:stretch;}
    ${card}{grid-column:span 12!important;height:auto!important;min-height:160px;}
    ${card}[data-home-card-variant="separator"]{min-height:40px;}
    ${card}>[aria-hidden="false"]{overflow:visible!important;}
    ${grid} [data-dashboard-card-header]{padding:14px 16px 10px!important;}
    ${grid} [data-dashboard-card-content]{padding:0 16px 14px!important;}
    ${grid} [data-home-titleless-content]{padding:14px 16px!important;}
    ${card}[data-home-card-id="builtin:quick-actions"] [data-home-titleless-content]{height:100%;}
    ${card}[data-home-card-id="builtin:news"]{height:200px!important;}
    ${grid} [data-home-storage-details]{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px 12px!important;}
    ${grid} [data-home-storage-row]{gap:4px 6px!important;}
    ${grid} [data-home-statistics-overview]{min-height:110px;padding-top:0!important;gap:8px!important;}
    ${grid} [data-home-summary-secondary]{grid-template-columns:repeat(2,minmax(0,1fr))!important;}
    ${grid} [data-dashboard-card-content]:has([data-chart])>div{
      height:clamp(220px,25dvh,300px)!important;min-height:220px!important;flex:none;}
    ${grid} [data-home-hitokoto]{white-space:normal;}
    ${grid} [data-home-hitokoto] p{white-space:normal;overflow:visible;}
    @container toolbox-home (min-width:40rem){
      ${card}{grid-column:span 6!important;}
      ${card}[data-home-card-variant="separator"]{grid-column:1/-1!important;}
      ${card}[data-home-card-id="builtin:hitokoto"]{grid-column:span 6!important;}
      ${card}[data-home-card-id="builtin:stats-overview"]{grid-column:1/-1!important;}
      ${grid} [data-home-summary-secondary]{grid-template-columns:repeat(4,minmax(0,1fr))!important;}
    }
    @container toolbox-home (min-width:56rem){
      ${card}{grid-column:span 4!important;}
      ${card}[data-home-card-id="builtin:hitokoto"]{grid-column:1/-1!important;}
      ${card}[data-home-card-id="builtin:stats-overview"]{grid-column:span 4!important;}
      ${card}:is([data-home-card-id="builtin:request-trend"],[data-home-card-id="builtin:token-trend"]){grid-column:span 6!important;}
    }
    @container toolbox-home (min-width:88rem){
      ${card}{grid-column:span 3!important;}
      ${card}[data-home-card-id="builtin:hitokoto"]{grid-column:span 3!important;}
      ${card}[data-home-card-id="builtin:stats-overview"]{grid-column:span 6!important;}
      ${grid} [data-home-summary-secondary]{grid-template-columns:repeat(4,minmax(0,1fr))!important;}
    }
  `;
}
