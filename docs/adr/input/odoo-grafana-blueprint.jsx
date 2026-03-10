import { useState } from "react";
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadialBarChart, RadialBar
} from "recharts";

// ─── DESIGN SYSTEM ─────────────────────────────────────────────────────────────
const C = {
  bg: "#0d1117",
  surface: "#161b22",
  card: "#1c2230",
  border: "#2d3a4e",
  accent: "#00d4aa",
  accentDim: "#00d4aa22",
  accentGold: "#f59e0b",
  accentRed: "#ef4444",
  accentBlue: "#3b82f6",
  accentPurple: "#a855f7",
  text: "#e2e8f0",
  muted: "#64748b",
  dim: "#334155",
};

// ─── MOCK DATA ──────────────────────────────────────────────────────────────────
const salesData = [
  { month: "Sep", revenue: 142000, target: 130000, orders: 89 },
  { month: "Okt", revenue: 158000, target: 145000, orders: 102 },
  { month: "Nov", revenue: 171000, target: 160000, orders: 118 },
  { month: "Dez", revenue: 196000, target: 175000, orders: 134 },
  { month: "Jan", revenue: 183000, target: 185000, orders: 121 },
  { month: "Feb", revenue: 211000, target: 195000, orders: 148 },
  { month: "Mär", revenue: 228000, target: 210000, orders: 162 },
];

const crmFunnelData = [
  { stage: "Leads", count: 342, value: 0 },
  { stage: "Qualifiziert", count: 198, value: 0 },
  { stage: "Angebot", count: 87, value: 0 },
  { stage: "Verhandlung", count: 41, value: 0 },
  { stage: "Gewonnen", count: 23, value: 0 },
];

const inventoryData = [
  { name: "Verfügbar", value: 68, color: C.accent },
  { name: "Reserviert", value: 21, color: C.accentGold },
  { name: "Bestellt", value: 8, color: C.accentBlue },
  { name: "Kritisch", value: 3, color: C.accentRed },
];

const systemData = [
  { time: "08:00", cpu: 22, ram: 58, workers: 4 },
  { time: "09:00", cpu: 45, ram: 63, workers: 8 },
  { time: "10:00", cpu: 67, ram: 71, workers: 12 },
  { time: "11:00", cpu: 58, ram: 69, workers: 10 },
  { time: "12:00", cpu: 81, ram: 76, workers: 14 },
  { time: "13:00", cpu: 73, ram: 74, workers: 13 },
  { time: "14:00", cpu: 62, ram: 72, workers: 11 },
  { time: "15:00", cpu: 55, ram: 70, workers: 9 },
];

const topProducts = [
  { name: "Produkt A", revenue: 48200, margin: 34 },
  { name: "Produkt B", revenue: 39100, margin: 28 },
  { name: "Produkt C", revenue: 31800, margin: 42 },
  { name: "Produkt D", revenue: 28400, margin: 19 },
  { name: "Produkt E", revenue: 22700, margin: 37 },
];

const invoiceAging = [
  { range: "0-30 Tage", amount: 94000, color: C.accent },
  { range: "31-60 Tage", amount: 41000, color: C.accentGold },
  { range: "61-90 Tage", amount: 18000, color: "#f97316" },
  { range: ">90 Tage", amount: 8500, color: C.accentRed },
];

// ─── REUSABLE COMPONENTS ────────────────────────────────────────────────────────
const KpiCard = ({ label, value, sub, trend, color = C.accent }) => (
  <div style={{
    background: C.card,
    border: `1px solid ${C.border}`,
    borderRadius: 10,
    padding: "18px 22px",
    position: "relative",
    overflow: "hidden",
  }}>
    <div style={{
      position: "absolute", top: 0, left: 0, right: 0, height: 2,
      background: color,
    }} />
    <div style={{ color: C.muted, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
      {label}
    </div>
    <div style={{ color: C.text, fontSize: 26, fontWeight: 700, fontFamily: "monospace" }}>{value}</div>
    <div style={{ marginTop: 6, display: "flex", gap: 8, alignItems: "center" }}>
      {trend && (
        <span style={{
          background: trend > 0 ? `${C.accent}22` : `${C.accentRed}22`,
          color: trend > 0 ? C.accent : C.accentRed,
          fontSize: 11, padding: "2px 7px", borderRadius: 4, fontWeight: 600
        }}>
          {trend > 0 ? "▲" : "▼"} {Math.abs(trend)}%
        </span>
      )}
      {sub && <span style={{ color: C.muted, fontSize: 11 }}>{sub}</span>}
    </div>
  </div>
);

const PanelHeader = ({ title, query, icon }) => (
  <div style={{ marginBottom: 14 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
      <span style={{ fontSize: 14 }}>{icon}</span>
      <span style={{ color: C.text, fontSize: 13, fontWeight: 600 }}>{title}</span>
    </div>
    {query && (
      <div style={{
        background: "#0d1117", border: `1px solid ${C.dim}`, borderRadius: 5,
        padding: "5px 10px", fontSize: 10, color: "#7c8a9e", fontFamily: "monospace",
        overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis"
      }}>
        {query}
      </div>
    )}
  </div>
);

const Tag = ({ children, color = C.accent }) => (
  <span style={{
    background: `${color}18`, color, border: `1px solid ${color}44`,
    fontSize: 10, padding: "2px 8px", borderRadius: 4, fontWeight: 600
  }}>{children}</span>
);

const SectionTitle = ({ children }) => (
  <div style={{
    color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em",
    fontWeight: 700, marginBottom: 16, paddingBottom: 8, borderBottom: `1px solid ${C.border}`
  }}>{children}</div>
);

// ─── ARCHITECTURE DIAGRAM ───────────────────────────────────────────────────────
const ArchDiagram = () => {
  const boxes = [
    { label: "Odoo 17", sub: "ERP / Business Logic", color: C.accentPurple, x: 20 },
    { label: "PostgreSQL", sub: "Odoo DB (read-only user)", color: C.accentBlue, x: 20 },
    { label: "Prometheus", sub: "Metrics Scraping :9090", color: C.accentGold, x: 50 },
    { label: "Loki", sub: "Log Aggregation", color: "#ec4899", x: 50 },
    { label: "Grafana", sub: "Visualization :3000", color: C.accent, x: 80 },
  ];

  return (
    <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 10, padding: 24 }}>
      <SectionTitle>Stack-Architektur (Docker Compose)</SectionTitle>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        {/* Left column: Odoo */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1, minWidth: 140 }}>
          {[boxes[0], boxes[1]].map(b => (
            <div key={b.label} style={{
              background: C.card, border: `1px solid ${b.color}66`,
              borderRadius: 8, padding: "12px 16px", textAlign: "center"
            }}>
              <div style={{ color: b.color, fontWeight: 700, fontSize: 13 }}>{b.label}</div>
              <div style={{ color: C.muted, fontSize: 10, marginTop: 3 }}>{b.sub}</div>
            </div>
          ))}
        </div>

        {/* Arrow */}
        <div style={{ color: C.border, fontSize: 24, flex: "0 0 auto" }}>→</div>

        {/* Middle column: Node Exporter + Promtail */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1, minWidth: 140 }}>
          <div style={{
            background: C.card, border: `1px solid ${C.accentGold}66`,
            borderRadius: 8, padding: "12px 16px", textAlign: "center"
          }}>
            <div style={{ color: C.accentGold, fontWeight: 700, fontSize: 13 }}>Node Exporter</div>
            <div style={{ color: C.muted, fontSize: 10, marginTop: 3 }}>System Metrics :9100</div>
          </div>
          <div style={{
            background: C.card, border: `1px solid #ec489966`,
            borderRadius: 8, padding: "12px 16px", textAlign: "center"
          }}>
            <div style={{ color: "#ec4899", fontWeight: 700, fontSize: 13 }}>Promtail</div>
            <div style={{ color: C.muted, fontSize: 10, marginTop: 3 }}>Log Shipper → Loki</div>
          </div>
        </div>

        {/* Arrow */}
        <div style={{ color: C.border, fontSize: 24, flex: "0 0 auto" }}>→</div>

        {/* Middle column: Prometheus + Loki */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1, minWidth: 140 }}>
          {[boxes[2], boxes[3]].map(b => (
            <div key={b.label} style={{
              background: C.card, border: `1px solid ${b.color}66`,
              borderRadius: 8, padding: "12px 16px", textAlign: "center"
            }}>
              <div style={{ color: b.color, fontWeight: 700, fontSize: 13 }}>{b.label}</div>
              <div style={{ color: C.muted, fontSize: 10, marginTop: 3 }}>{b.sub}</div>
            </div>
          ))}
        </div>

        {/* Arrow */}
        <div style={{ color: C.border, fontSize: 24, flex: "0 0 auto" }}>→</div>

        {/* Right: Grafana */}
        <div style={{ flex: 1, minWidth: 140 }}>
          <div style={{
            background: C.card, border: `2px solid ${C.accent}`,
            borderRadius: 8, padding: "20px 16px", textAlign: "center",
            boxShadow: `0 0 20px ${C.accent}33`
          }}>
            <div style={{ color: C.accent, fontWeight: 800, fontSize: 15 }}>📊 GRAFANA</div>
            <div style={{ color: C.muted, fontSize: 10, marginTop: 3 }}>Dashboards :3000</div>
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
              {["PostgreSQL DS", "Prometheus DS", "Loki DS"].map(ds => (
                <div key={ds} style={{
                  background: `${C.accent}18`, color: C.accent,
                  fontSize: 9, borderRadius: 3, padding: "2px 6px"
                }}>{ds}</div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Data Flows Legend */}
      <div style={{ marginTop: 16, display: "flex", gap: 16, flexWrap: "wrap" }}>
        {[
          { label: "Business KPIs via SQL", color: C.accentBlue },
          { label: "System Metrics via PromQL", color: C.accentGold },
          { label: "Logs via LogQL", color: "#ec4899" },
        ].map(f => (
          <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 20, height: 2, background: f.color }} />
            <span style={{ color: C.muted, fontSize: 10 }}>{f.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── DASHBOARD 1: BUSINESS ──────────────────────────────────────────────────────
const BusinessDashboard = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <SectionTitle>📈 Dashboard 1 — Business Intelligence (PostgreSQL → Grafana)</SectionTitle>

    {/* KPI Row */}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
      <KpiCard label="Umsatz MTD" value="€228k" trend={8.1} sub="vs. Vormonat" color={C.accent} />
      <KpiCard label="Offene Aufträge" value="162" trend={13.3} sub="aktiv" color={C.accentBlue} />
      <KpiCard label="Conversion Rate" value="6.7%" trend={-1.2} sub="Leads → Won" color={C.accentGold} />
      <KpiCard label="Offene Rechnungen" value="€161k" sub="4 Altersklassen" color={C.accentRed} />
    </div>

    {/* Charts Row 1 */}
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
      {/* Revenue vs Target */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18 }}>
        <PanelHeader
          icon="💰"
          title="Umsatz vs. Ziel (6 Monate)"
          query="SELECT date_trunc('month', date_order) AS time, SUM(amount_total) FROM sale_order WHERE state='sale' GROUP BY 1"
        />
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={salesData}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={C.accent} stopOpacity={0.3} />
                <stop offset="95%" stopColor={C.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={C.dim} />
            <XAxis dataKey="month" stroke={C.muted} tick={{ fontSize: 10 }} />
            <YAxis stroke={C.muted} tick={{ fontSize: 10 }} tickFormatter={v => `€${v/1000}k`} />
            <Tooltip
              contentStyle={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6 }}
              labelStyle={{ color: C.text }}
              formatter={(v, n) => [`€${(v/1000).toFixed(0)}k`, n === "revenue" ? "Umsatz" : "Ziel"]}
            />
            <Area type="monotone" dataKey="revenue" stroke={C.accent} fill="url(#revGrad)" strokeWidth={2} />
            <Line type="monotone" dataKey="target" stroke={C.accentGold} strokeDasharray="5 5" strokeWidth={1.5} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* CRM Funnel */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18 }}>
        <PanelHeader
          icon="🎯"
          title="CRM Pipeline Funnel"
          query="SELECT stage_id, COUNT(*) FROM crm_lead WHERE active=true GROUP BY stage_id"
        />
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
          {crmFunnelData.map((d, i) => {
            const max = crmFunnelData[0].count;
            const pct = (d.count / max) * 100;
            return (
              <div key={d.stage}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ color: C.muted, fontSize: 10 }}>{d.stage}</span>
                  <span style={{ color: C.text, fontSize: 10, fontFamily: "monospace" }}>{d.count}</span>
                </div>
                <div style={{ background: C.dim, borderRadius: 3, height: 6 }}>
                  <div style={{
                    background: `hsl(${160 - i * 25}, 70%, 55%)`,
                    width: `${pct}%`, height: 6, borderRadius: 3,
                    transition: "width 0.5s ease"
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>

    {/* Charts Row 2 */}
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
      {/* Top Products */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18 }}>
        <PanelHeader icon="🏆" title="Top 5 Produkte" query="SELECT pt.name, SUM(sol.price_subtotal) FROM sale_order_line sol JOIN product_template pt ON... GROUP BY 1 ORDER BY 2 DESC LIMIT 5" />
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {topProducts.map((p, i) => (
            <div key={p.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ color: C.muted, fontSize: 10, width: 14 }}>{i + 1}.</span>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: C.text, fontSize: 11 }}>{p.name}</span>
                  <span style={{ color: C.accent, fontSize: 11, fontFamily: "monospace" }}>€{(p.revenue / 1000).toFixed(1)}k</span>
                </div>
                <div style={{ color: C.muted, fontSize: 9 }}>Marge: {p.margin}%</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Inventory Status */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18 }}>
        <PanelHeader icon="📦" title="Lagerbestand Status" query="SELECT location_id, SUM(quantity) FROM stock_quant GROUP BY product_id" />
        <ResponsiveContainer width="100%" height={140}>
          <PieChart>
            <Pie data={inventoryData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" paddingAngle={2}>
              {inventoryData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip
              contentStyle={{ background: C.surface, border: `1px solid ${C.border}` }}
              formatter={(v) => [`${v}%`]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center" }}>
          {inventoryData.map(d => (
            <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: d.color }} />
              <span style={{ color: C.muted, fontSize: 9 }}>{d.name} {d.value}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Invoice Aging */}
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18 }}>
        <PanelHeader icon="💳" title="Offene Posten Aging" query="SELECT CASE WHEN date_due >= NOW()-30 THEN '0-30d'... FROM account_move WHERE state='posted' AND payment_state!='paid'" />
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={invoiceAging} barSize={20}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.dim} vertical={false} />
            <XAxis dataKey="range" stroke={C.muted} tick={{ fontSize: 8 }} />
            <YAxis stroke={C.muted} tick={{ fontSize: 8 }} tickFormatter={v => `€${v/1000}k`} />
            <Tooltip
              contentStyle={{ background: C.surface, border: `1px solid ${C.border}` }}
              formatter={(v) => [`€${(v/1000).toFixed(0)}k`]}
            />
            <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
              {invoiceAging.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
);

// ─── DASHBOARD 2: SYSTEM ────────────────────────────────────────────────────────
const SystemDashboard = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <SectionTitle>🖥️ Dashboard 2 — System Performance (Prometheus → Grafana)</SectionTitle>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
      <KpiCard label="CPU Usage" value="62%" trend={-5} sub="avg 15min" color={C.accentGold} />
      <KpiCard label="RAM Usage" value="72%" sub="11.5 / 16 GB" color={C.accentBlue} />
      <KpiCard label="Odoo Workers" value="11" sub="von max 16" color={C.accent} />
      <KpiCard label="Response Time" value="284ms" trend={-12} sub="p95 HTTP" color={C.accentPurple} />
    </div>
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18 }}>
      <PanelHeader
        icon="⚡"
        title="CPU / RAM / Worker Load (Tagesverlauf)"
        query='rate(node_cpu_seconds_total{mode="user"}[5m]) * 100 | node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100'
      />
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={systemData}>
          <CartesianGrid strokeDasharray="3 3" stroke={C.dim} />
          <XAxis dataKey="time" stroke={C.muted} tick={{ fontSize: 10 }} />
          <YAxis stroke={C.muted} tick={{ fontSize: 10 }} />
          <Tooltip contentStyle={{ background: C.surface, border: `1px solid ${C.border}` }} />
          <Line type="monotone" dataKey="cpu" stroke={C.accentGold} strokeWidth={2} dot={false} name="CPU %" />
          <Line type="monotone" dataKey="ram" stroke={C.accentBlue} strokeWidth={2} dot={false} name="RAM %" />
          <Line type="monotone" dataKey="workers" stroke={C.accent} strokeWidth={2} dot={false} name="Workers" />
        </LineChart>
      </ResponsiveContainer>
    </div>
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }}>
      <PanelHeader icon="🔔" title="Alerting-Regeln (Prometheus AlertManager)" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {[
          { name: "High CPU", rule: "avg(rate(cpu[5m])) > 0.85", sev: "warning", color: C.accentGold },
          { name: "RAM Critical", rule: "mem_available / mem_total < 0.1", sev: "critical", color: C.accentRed },
          { name: "Worker Saturation", rule: "odoo_workers_busy / odoo_workers_total > 0.9", sev: "critical", color: C.accentRed },
          { name: "Slow Responses", rule: "http_request_duration_p95 > 2s", sev: "warning", color: C.accentGold },
          { name: "DB Connections", rule: "pg_stat_activity_count > 80", sev: "warning", color: C.accentGold },
          { name: "Disk Space", rule: "disk_free_ratio < 0.15", sev: "warning", color: C.accentGold },
        ].map(a => (
          <div key={a.name} style={{
            background: C.bg, border: `1px solid ${a.color}44`, borderRadius: 7, padding: "10px 12px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ color: C.text, fontSize: 11, fontWeight: 600 }}>{a.name}</span>
              <Tag color={a.color}>{a.sev}</Tag>
            </div>
            <div style={{ color: C.muted, fontSize: 9, fontFamily: "monospace" }}>{a.rule}</div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// ─── DASHBOARD 3: SQL LIBRARY ───────────────────────────────────────────────────
const SqlLibrary = () => {
  const queries = [
    {
      title: "Monatlicher Umsatz",
      module: "Sales",
      sql: `SELECT
  date_trunc('month', so.date_order) AS "time",
  SUM(so.amount_total) AS revenue,
  COUNT(*) AS order_count
FROM sale_order so
WHERE so.state IN ('sale','done')
  AND so.date_order >= NOW() - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1`,
    },
    {
      title: "CRM Pipeline nach Stage",
      module: "CRM",
      sql: `SELECT
  cs.name AS stage,
  COUNT(cl.id) AS leads,
  SUM(cl.expected_revenue) AS pipeline_value
FROM crm_lead cl
JOIN crm_stage cs ON cs.id = cl.stage_id
WHERE cl.active = true AND cl.type = 'opportunity'
GROUP BY cs.name, cs.sequence
ORDER BY cs.sequence`,
    },
    {
      title: "Offene Rechnungen Aging",
      module: "Accounting",
      sql: `SELECT
  CASE
    WHEN NOW() - am.invoice_date_due <= INTERVAL '30 days' THEN '0-30 Tage'
    WHEN NOW() - am.invoice_date_due <= INTERVAL '60 days' THEN '31-60 Tage'
    WHEN NOW() - am.invoice_date_due <= INTERVAL '90 days' THEN '61-90 Tage'
    ELSE '>90 Tage'
  END AS aging_bucket,
  SUM(am.amount_residual) AS open_amount,
  COUNT(*) AS invoice_count
FROM account_move am
WHERE am.move_type = 'out_invoice'
  AND am.state = 'posted'
  AND am.payment_state NOT IN ('paid','reversed')
GROUP BY 1`,
    },
    {
      title: "Lagerbestand kritisch",
      module: "Inventory",
      sql: `SELECT
  pt.name AS product,
  SUM(sq.quantity) AS qty_on_hand,
  pp.reorder_point
FROM stock_quant sq
JOIN product_product pp ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
WHERE sq.location_id IN (
  SELECT id FROM stock_location WHERE usage = 'internal'
)
GROUP BY pt.name, pp.reorder_point
HAVING SUM(sq.quantity) <= pp.reorder_point * 1.2
ORDER BY SUM(sq.quantity) / NULLIF(pp.reorder_point, 0)`,
    },
  ];

  const [active, setActive] = useState(0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SectionTitle>🗄️ SQL Query Library — PostgreSQL Datasource</SectionTitle>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {queries.map((q, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            style={{
              background: active === i ? `${C.accent}22` : C.bg,
              border: `1px solid ${active === i ? C.accent : C.border}`,
              color: active === i ? C.accent : C.muted,
              borderRadius: 6, padding: "6px 14px", fontSize: 11,
              cursor: "pointer", fontWeight: active === i ? 600 : 400
            }}
          >
            {q.title}
          </button>
        ))}
      </div>
      <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 14, alignItems: "center" }}>
          <Tag color={C.accentBlue}>{queries[active].module}</Tag>
          <span style={{ color: C.text, fontSize: 13, fontWeight: 600 }}>{queries[active].title}</span>
        </div>
        <pre style={{
          background: C.bg, border: `1px solid ${C.dim}`,
          borderRadius: 7, padding: 16, margin: 0,
          fontSize: 11, color: "#7dd3fc", fontFamily: "monospace",
          lineHeight: 1.7, overflow: "auto", maxHeight: 260
        }}>
          {queries[active].sql}
        </pre>
        <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Tag color={C.muted}>Grafana: PostgreSQL Datasource</Tag>
          <Tag color={C.muted}>Visualization: Time Series / Bar Chart / Stat</Tag>
          <Tag color={C.accentGold}>⚠ Read-Only User empfohlen</Tag>
        </div>
      </div>
    </div>
  );
};

// ─── IMPLEMENTATION GUIDE ───────────────────────────────────────────────────────
const ImplementationGuide = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
    <SectionTitle>⚙️ Implementation Guide (Docker Compose Stack)</SectionTitle>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      {[
        {
          step: "01",
          title: "Read-Only DB User anlegen",
          color: C.accentBlue,
          code: `-- In Odoo PostgreSQL:
CREATE USER grafana_ro WITH PASSWORD 'secret';
GRANT CONNECT ON DATABASE odoo TO grafana_ro;
GRANT USAGE ON SCHEMA public TO grafana_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO grafana_ro;`
        },
        {
          step: "02",
          title: "Prometheus prometheus.yml",
          color: C.accentGold,
          code: `global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']`
        },
        {
          step: "03",
          title: "Grafana Datasources (provisioning)",
          color: C.accent,
          code: `# grafana/provisioning/datasources/all.yaml
apiVersion: 1
datasources:
  - name: OdooDB
    type: postgres
    url: db:5432
    database: odoo
    user: grafana_ro
    jsonData:
      sslmode: disable
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
  - name: Loki
    type: loki
    url: http://loki:3100`
        },
        {
          step: "04",
          title: "Docker Compose services",
          color: C.accentPurple,
          code: `services:
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
  prometheus:
    image: prom/prometheus
    volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml"]
  loki:
    image: grafana/loki
  node-exporter:
    image: prom/node-exporter`
        },
      ].map(item => (
        <div key={item.step} style={{
          background: C.card, border: `1px solid ${item.color}44`, borderRadius: 10, padding: 18
        }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
            <div style={{
              background: item.color, color: C.bg, borderRadius: 5,
              width: 28, height: 28, display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 11, fontWeight: 800
            }}>{item.step}</div>
            <span style={{ color: C.text, fontSize: 12, fontWeight: 600 }}>{item.title}</span>
          </div>
          <pre style={{
            background: C.bg, borderRadius: 6, padding: 12, margin: 0,
            fontSize: 9.5, color: "#94a3b8", fontFamily: "monospace",
            lineHeight: 1.6, overflow: "auto", maxHeight: 160
          }}>{item.code}</pre>
        </div>
      ))}
    </div>
  </div>
);

// ─── MAIN APP ───────────────────────────────────────────────────────────────────
const tabs = [
  { id: "arch", label: "🏗 Architektur" },
  { id: "business", label: "📈 Business KPIs" },
  { id: "system", label: "🖥 System Monitor" },
  { id: "sql", label: "🗄 SQL Library" },
  { id: "setup", label: "⚙️ Setup Guide" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("arch");

  return (
    <div style={{
      background: C.bg, minHeight: "100vh",
      fontFamily: "'IBM Plex Mono', 'Fira Code', monospace",
      color: C.text, padding: 24
    }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 4 }}>
          <h1 style={{ margin: 0, fontSize: 22, color: C.accent, fontWeight: 800, letterSpacing: "-0.02em" }}>
            Odoo + Grafana
          </h1>
          <span style={{ color: C.muted, fontSize: 11 }}>Best Practice Blueprint</span>
          <Tag color={C.accent}>2025</Tag>
        </div>
        <p style={{ margin: 0, color: C.muted, fontSize: 11 }}>
          Full Observability Stack: Business Intelligence · System Monitoring · Log Analysis
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap" }}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            style={{
              background: activeTab === t.id ? `${C.accent}22` : "transparent",
              border: `1px solid ${activeTab === t.id ? C.accent : C.border}`,
              color: activeTab === t.id ? C.accent : C.muted,
              borderRadius: 7, padding: "8px 16px", fontSize: 11,
              cursor: "pointer", fontWeight: activeTab === t.id ? 700 : 400,
              transition: "all 0.15s"
            }}
          >{t.label}</button>
        ))}
      </div>

      {/* Content */}
      <div>
        {activeTab === "arch" && <ArchDiagram />}
        {activeTab === "business" && <BusinessDashboard />}
        {activeTab === "system" && <SystemDashboard />}
        {activeTab === "sql" && <SqlLibrary />}
        {activeTab === "setup" && <ImplementationGuide />}
      </div>
    </div>
  );
}
