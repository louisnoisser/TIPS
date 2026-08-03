const dashboard = window.GBA_INDICATION_DASHBOARD;

const n = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
};

const formatInt = (value) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n(value));
const formatPct = (value) => `${n(value).toFixed(1)}%`;
const formatDelta = (value) => {
  if (value === null || value === undefined) return "n/a";
  const amount = n(value);
  return `${amount >= 0 ? "+" : ""}${formatInt(amount)}`;
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

function setCopy() {
  document.title = dashboard.meta.title;
  const subtitle = `${dashboard.meta.indication_name} | OPS ${dashboard.meta.ops_selector} | latest year ${dashboard.meta.latest_year}`;
  document.getElementById("app-title").textContent = dashboard.meta.title;
  document.getElementById("app-subtitle").textContent = subtitle;

  const badgeRow = document.getElementById("hero-badges");
  const timeLabel = (dashboard.meta.time_bins || []).join(" / ");
  const badges = [
    `Main network >= ${dashboard.meta.main_threshold}`,
    `Strict network >= ${dashboard.meta.strict_threshold}`,
    `Access bands ${timeLabel} min`,
    `Cases ${formatInt(dashboard.metrics.latest_year_cases_total)}`,
  ];
  badgeRow.innerHTML = badges.map((item) => `<span class="badge">${escapeHtml(item)}</span>`).join("");

  const heroSummary = document.getElementById("hero-summary");
  heroSummary.innerHTML = [
    {
      label: "Strict-network share",
      value: formatPct(dashboard.metrics.strict_threshold_case_share_pct),
    },
    {
      label: `Change vs ${dashboard.metrics.previous_year ?? "prior year"}`,
      value: formatDelta(dashboard.metrics.delta_cases_vs_previous),
    },
    {
      label: "Matched subcodes",
      value: String((dashboard.metrics.matched_subcodes || []).length),
    },
  ]
    .map(
      (item) => `
        <article class="summary-chip">
          <span>${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
        </article>
      `
    )
    .join("");
}

function renderMetrics() {
  const grid = document.getElementById("metrics-grid");
  const cards = [
    {
      title: `Procedures in ${dashboard.meta.latest_year}`,
      value: formatInt(dashboard.metrics.latest_year_cases_total),
      meta: `${formatDelta(dashboard.metrics.delta_cases_vs_previous)} vs ${dashboard.metrics.previous_year ?? "previous year"}`,
      className: "accent",
    },
    {
      title: "Any active hospitals",
      value: formatInt(dashboard.metrics.latest_year_hospitals_any),
      meta: "All hospitals with at least one recorded procedure",
      className: "",
    },
    {
      title: `Main network (>= ${dashboard.meta.main_threshold})`,
      value: formatInt(dashboard.metrics.main_threshold_centers),
      meta: `${formatDelta(dashboard.metrics.delta_main_centers_vs_previous)} centers vs ${dashboard.metrics.previous_year ?? "prior year"}`,
      className: "",
    },
    {
      title: `Strict network (>= ${dashboard.meta.strict_threshold})`,
      value: formatInt(dashboard.metrics.strict_threshold_centers),
      meta: `${formatDelta(dashboard.metrics.delta_strict_centers_vs_previous)} centers vs ${dashboard.metrics.previous_year ?? "prior year"}`,
      className: "warm",
    },
  ];

  grid.innerHTML = cards
    .map(
      (card) => `
        <article class="metric-card ${card.className}">
          <p class="card-kicker">${escapeHtml(card.title)}</p>
          <span class="metric-value">${escapeHtml(card.value)}</span>
          <span class="metric-meta">${escapeHtml(card.meta)}</span>
        </article>
      `
    )
    .join("");
}

function renderFindings() {
  const grid = document.getElementById("findings-grid");
  grid.innerHTML = (dashboard.findings || [])
    .map(
      (item) => `
        <article class="finding-card">
          <p class="card-kicker">${escapeHtml(item.kicker)}</p>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.body)}</p>
        </article>
      `
    )
    .join("");
}

function buildLineChartMarkup(data, series, yLabel) {
  if (!data.length || !series.length) {
    return `<p class="metric-meta">No chart data available.</p>`;
  }

  const width = 760;
  const height = 260;
  const padding = { top: 18, right: 22, bottom: 34, left: 40 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const labels = data.map((row) => String(row.year));

  const allValues = series.flatMap((item) => data.map((row) => n(row[item.key])));
  const yMax = Math.max(...allValues, 1);
  const xStep = data.length > 1 ? chartWidth / (data.length - 1) : chartWidth / 2;

  const toPoint = (rowIndex, value) => {
    const x = padding.left + (data.length > 1 ? xStep * rowIndex : chartWidth / 2);
    const y = padding.top + chartHeight - (n(value) / yMax) * chartHeight;
    return [x, y];
  };

  const gridLines = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3;
    const y = padding.top + chartHeight - chartHeight * ratio;
    const label = Math.round(yMax * ratio);
    return `<g>
      <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(24,34,46,0.09)" stroke-width="1" />
      <text x="${padding.left - 8}" y="${y + 4}" text-anchor="end" font-size="12" fill="#5e6773">${label}</text>
    </g>`;
  }).join("");

  const yearLabels = labels
    .map((label, index) => {
      if (data.length > 8 && index % 2 === 1 && index !== labels.length - 1) return "";
      const [x] = toPoint(index, 0);
      return `<text x="${x}" y="${height - 8}" text-anchor="middle" font-size="12" fill="#5e6773">${label}</text>`;
    })
    .join("");

  const lines = series
    .map((item) => {
      const points = data.map((row, index) => toPoint(index, row[item.key]));
      const path = points.map((point) => point.join(",")).join(" ");
      const circles = points
        .map(
          (point) =>
            `<circle cx="${point[0]}" cy="${point[1]}" r="4" fill="${item.color}" stroke="#fffaf4" stroke-width="2" />`
        )
        .join("");
      return `
        <g>
          <polyline fill="none" stroke="${item.color}" stroke-width="4" points="${path}" stroke-linejoin="round" stroke-linecap="round" />
          ${circles}
        </g>
      `;
    })
    .join("");

  const legend = `
    <div class="legend">
      ${series
        .map(
          (item) => `
            <span class="legend-item">
              <span class="legend-swatch" style="background:${item.color}"></span>
              ${escapeHtml(item.label)}
            </span>
          `
        )
        .join("")}
    </div>
  `;

  return `
    <div class="svg-shell">
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(yLabel)}">
        ${gridLines}
        <line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${width - padding.right}" y2="${padding.top + chartHeight}" stroke="rgba(24,34,46,0.14)" stroke-width="1.2" />
        ${lines}
        ${yearLabels}
      </svg>
      ${legend}
    </div>
  `;
}

function renderTrendCharts() {
  document.getElementById("volume-chart").innerHTML = buildLineChartMarkup(
    dashboard.yearly || [],
    [{ key: "cases_total", label: "Cases", color: "#0d6c74" }],
    "Cases over time"
  );

  document.getElementById("center-chart").innerHTML = buildLineChartMarkup(
    dashboard.yearly || [],
    [
      { key: "hospitals_any", label: "Any hospital", color: "#18222e" },
      { key: "hospitals_main", label: `>= ${dashboard.meta.main_threshold}`, color: "#0d6c74" },
      { key: "hospitals_strict", label: `>= ${dashboard.meta.strict_threshold}`, color: "#cb5f3d" },
    ],
    "Center counts over time"
  );

  document.getElementById("population-chart").innerHTML = buildLineChartMarkup(
    (dashboard.population_coverage?.main || []).map((row) => ({
      year: `${row.time_minutes}m`,
      main: row.pct_population_covered,
      strict: (dashboard.population_coverage?.strict || []).find((item) => n(item.time_minutes) === n(row.time_minutes))
        ?.pct_population_covered,
    })),
    [
      { key: "main", label: `>= ${dashboard.meta.main_threshold}`, color: "#0d6c74" },
      { key: "strict", label: `>= ${dashboard.meta.strict_threshold}`, color: "#cb5f3d" },
    ],
    "Population coverage"
  );
}

function renderConcentrationChart() {
  document.getElementById("concentration-chart").innerHTML = buildLineChartMarkup(
    dashboard.concentration || [],
    [
      { key: "top_10_share_pct", label: "Top 10 share", color: "#0d6c74" },
      { key: "top_20_share_pct", label: "Top 20 share", color: "#cb5f3d" },
    ],
    "Concentration over time"
  );
}

function renderChurnChart() {
  const churnRows = dashboard.churn || [];
  const thresholds = [...new Set(churnRows.map((row) => n(row.threshold)))];
  const grouped = [];
  thresholds.forEach((threshold) => {
    churnRows
      .filter((row) => n(row.threshold) === threshold)
      .forEach((row) => {
        const existing = grouped.find((item) => item.year === row.year);
        if (existing) {
          existing[`t${threshold}`] = row.retention_rate_prev_pct;
        } else {
          grouped.push({ year: row.year, [`t${threshold}`]: row.retention_rate_prev_pct });
        }
      });
  });
  grouped.sort((a, b) => n(a.year) - n(b.year));

  document.getElementById("churn-chart").innerHTML = buildLineChartMarkup(
    grouped,
    thresholds.map((threshold, index) => ({
      key: `t${threshold}`,
      label: `Retention >= ${threshold}`,
      color: ["#18222e", "#0d6c74", "#cb5f3d", "#8f1d28"][index % 4],
    })),
    "Retention rates by threshold"
  );
}

function renderSimpleTable(targetId, rows, columns) {
  const mount = document.getElementById(targetId);
  if (!rows.length) {
    mount.innerHTML = `<p class="metric-meta">No rows available.</p>`;
    return;
  }
  mount.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (row) => `
                <tr>
                  ${columns
                    .map((column) => `<td>${column.render ? column.render(row[column.key], row) : escapeHtml(row[column.key])}</td>`)
                    .join("")}
                </tr>
              `
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderCenterTables() {
  renderSimpleTable("center-table", dashboard.top_centers || [], [
    { key: "hospital_name", label: "Center", render: (value) => `<strong>${escapeHtml(value)}</strong>` },
    { key: "city", label: "City" },
    { key: dashboard.case_col, label: "Cases", render: (value) => formatInt(value) },
  ]);

  renderSimpleTable("ik-table", dashboard.top_ik || [], [
    { key: "hospital_name", label: "Center", render: (value) => `<strong>${escapeHtml(value)}</strong>` },
    { key: "city", label: "City" },
    { key: "total_cases", label: "Total cases", render: (value) => formatInt(value) },
    { key: "years_active", label: "Years", render: (value) => formatInt(value) },
  ]);
}

function renderRateTables() {
  renderSimpleTable("state-rate-table", dashboard.state_rates || [], [
    { key: "state_name", label: "State", render: (value) => `<strong>${escapeHtml(value)}</strong>` },
    { key: "cases_per_million", label: "Cases / million", render: (value) => n(value).toFixed(2) },
    { key: "total_cases", label: "Cases", render: (value) => formatInt(value) },
  ]);

  renderSimpleTable("county-rate-table", dashboard.top_provider_counties || [], [
    { key: "county_name", label: "County", render: (value, row) => `<strong>${escapeHtml(value)}</strong><br><span class="metric-meta">${escapeHtml(row.state_name)}</span>` },
    { key: "cases_per_million", label: "Cases / million", render: (value) => n(value).toFixed(2) },
    { key: "total_cases", label: "Cases", render: (value) => formatInt(value) },
  ]);
}

function currentCoverageColumn() {
  return `coverage_ge_${document.getElementById("threshold-select").value}_${document.getElementById("time-select").value}m_pct`;
}

function currentGapColumn() {
  return `gap_vs_germany_ge_${document.getElementById("threshold-select").value}_${document.getElementById("time-select").value}m_pp`;
}

function renderStateBars() {
  const coverageColumn = currentCoverageColumn();
  const gapColumn = currentGapColumn();
  const stateRows = [...(dashboard.state_access || [])].sort((a, b) => n(b[coverageColumn]) - n(a[coverageColumn]));
  const list = stateRows
    .map(
      (row) => `
        <article class="state-bar-row">
          <div>
            <div class="state-bar-meta">
              <strong>${escapeHtml(row.state_name)}</strong>
              <span>${formatPct(row[coverageColumn])}</span>
            </div>
            <div class="state-bar-track">
              <span class="state-bar-fill" style="width:${Math.max(0, Math.min(100, n(row[coverageColumn])))}%"></span>
            </div>
            <div class="state-bar-meta">
              <span>Gap vs Germany</span>
              <span>${n(row[gapColumn]).toFixed(2)} pp</span>
            </div>
          </div>
          <div class="metric-meta">
            ${formatInt(row[`centers_ge_${document.getElementById("threshold-select").value}`] || 0)} centers
          </div>
        </article>
      `
    )
    .join("");
  document.getElementById("state-bars").innerHTML = `<div class="state-bar-list">${list}</div>`;
}

function renderCountyTable() {
  const coverageColumn = currentCoverageColumn();
  const gapColumn = currentGapColumn();
  const query = document.getElementById("county-search").value.trim().toLowerCase();
  const urbanity = document.getElementById("urbanity-select").value;

  let rows = [...(dashboard.county_access || [])];
  if (urbanity !== "all") {
    rows = rows.filter((row) => String(row.urban_rural || "").toLowerCase() === urbanity);
  }
  if (query) {
    rows = rows.filter((row) => `${row.county_name} ${row.state_name}`.toLowerCase().includes(query));
  }

  rows = rows.sort((a, b) => n(a[coverageColumn]) - n(b[coverageColumn])).slice(0, 20);
  const markup = rows
    .map(
      (row) => `
        <article class="county-row">
          <header>
            <div>
              <strong>${escapeHtml(row.county_name)}</strong>
              <div class="metric-meta">${escapeHtml(row.state_name)}</div>
            </div>
            <span class="pill ${escapeHtml(String(row.urban_rural || "other").toLowerCase())}">${escapeHtml(row.urban_rural || "other")}</span>
          </header>
          <div class="state-bar-meta">
            <span>Coverage</span>
            <span>${formatPct(row[coverageColumn])}</span>
          </div>
          <div class="state-bar-meta">
            <span>Gap vs Germany</span>
            <span>${n(row[gapColumn]).toFixed(2)} pp</span>
          </div>
          <div class="state-bar-meta">
            <span>Population</span>
            <span>${formatInt(row.population_total)}</span>
          </div>
        </article>
      `
    )
    .join("");

  document.getElementById("county-table").innerHTML = `<div class="county-list">${markup}</div>`;
}

function renderFigureGallery() {
  const mount = document.getElementById("figure-gallery");
  const modal = document.getElementById("figure-modal");
  const modalImage = document.getElementById("modal-image");
  const modalTitle = document.getElementById("modal-title");
  const modalCaption = document.getElementById("modal-caption");

  mount.innerHTML = (dashboard.figures || [])
    .map(
      (figure, index) => `
        <article class="figure-card" data-index="${index}" tabindex="0">
          <img src="${escapeHtml(figure.file)}" alt="${escapeHtml(figure.title)}">
          <div>
            <p class="card-kicker">Figure ${index + 1}</p>
            <h3>${escapeHtml(figure.title)}</h3>
            <p>${escapeHtml(figure.caption)}</p>
          </div>
        </article>
      `
    )
    .join("");

  mount.querySelectorAll(".figure-card").forEach((card) => {
    const open = () => {
      const figure = dashboard.figures[Number(card.dataset.index)];
      modalImage.src = figure.file;
      modalImage.alt = figure.title;
      modalTitle.textContent = figure.title;
      modalCaption.textContent = figure.caption;
      modal.showModal();
    };
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });
  });

  document.getElementById("modal-close").addEventListener("click", () => modal.close());
  modal.addEventListener("click", (event) => {
    const rect = modal.getBoundingClientRect();
    const inside =
      rect.top <= event.clientY &&
      event.clientY <= rect.top + rect.height &&
      rect.left <= event.clientX &&
      event.clientX <= rect.left + rect.width;
    if (!inside) modal.close();
  });
}

function renderMethods() {
  document.getElementById("method-list").innerHTML = (dashboard.methods || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
  document.getElementById("summary-markdown").textContent = dashboard.summary_markdown || "No summary text available.";
}

function seedControls() {
  const thresholdSelect = document.getElementById("threshold-select");
  const timeSelect = document.getElementById("time-select");

  [dashboard.meta.main_threshold, dashboard.meta.strict_threshold].forEach((threshold) => {
    const option = document.createElement("option");
    option.value = String(threshold);
    option.textContent = `>= ${threshold} cases`;
    thresholdSelect.append(option);
  });
  thresholdSelect.value = String(dashboard.meta.strict_threshold);

  (dashboard.meta.time_bins || []).forEach((timeBin) => {
    const option = document.createElement("option");
    option.value = String(timeBin);
    option.textContent = `${timeBin} min`;
    timeSelect.append(option);
  });
  timeSelect.value = String((dashboard.meta.time_bins || []).slice(-1)[0] || 60);

  [thresholdSelect, timeSelect, document.getElementById("urbanity-select"), document.getElementById("county-search")].forEach(
    (element) => {
      element.addEventListener("input", () => {
        renderStateBars();
        renderCountyTable();
      });
    }
  );
}

document.addEventListener("DOMContentLoaded", () => {
  setCopy();
  renderMetrics();
  renderFindings();
  renderTrendCharts();
  renderConcentrationChart();
  renderChurnChart();
  renderCenterTables();
  renderRateTables();
  seedControls();
  renderStateBars();
  renderCountyTable();
  renderFigureGallery();
  renderMethods();
});
