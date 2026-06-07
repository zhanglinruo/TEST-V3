const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const DEFAULT_PROJECT_ROOT = "D:\\powerBI\\test_db_generated";
const DEFAULT_REPORT_JSON = path.join(
  DEFAULT_PROJECT_ROOT,
  "test_db_generated.Report",
  "report.json",
);
const DEFAULT_OUTPUT_DIR = path.join(process.cwd(), "outputs", "powerbi-analysis");

const SUPPORTED_VISUAL_TYPES = new Set([
  "card",
  "lineChart",
  "barChart",
  "clusteredColumnChart",
  "tableEx",
  "pivotTable",
]);

function parseArgs(argv) {
  const options = {
    reportJson: DEFAULT_REPORT_JSON,
    outputDir: DEFAULT_OUTPUT_DIR,
    rowLimit: 20,
    dryRun: false,
    helpOnly: false,
  };

  for (let index = 2; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--report-json") {
      options.reportJson = argv[index + 1];
      index += 1;
    } else if (argument === "--out") {
      options.outputDir = argv[index + 1];
      index += 1;
    } else if (argument === "--limit") {
      options.rowLimit = Number(argv[index + 1]);
      index += 1;
    } else if (argument === "--dry-run") {
      options.dryRun = true;
    } else if (argument === "--mcp-help") {
      options.helpOnly = true;
    }
  }

  return options;
}

function readJson(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  return JSON.parse(content);
}

function safeParseJson(value, fallback = null) {
  if (typeof value !== "string") return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function sanitizeFilePart(value) {
  return String(value || "report")
    .replace(/[\\/:*?"<>|]+/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 80);
}

function daxIdentifier(value) {
  return String(value).replace(/]/g, "]]");
}

function daxString(value) {
  return String(value).replace(/"/g, '""');
}

function tableColumnRef(tableName, columnName) {
  return `'${String(tableName).replace(/'/g, "''")}'[${daxIdentifier(columnName)}]`;
}

function measureRef(measureName) {
  return `[${daxIdentifier(measureName)}]`;
}

function expressionSourceName(expression) {
  return expression?.SourceRef?.Source || "";
}

function sourceEntityMap(prototypeQuery) {
  const result = new Map();
  for (const source of prototypeQuery?.From || []) {
    if (source?.Name && source?.Entity) {
      result.set(source.Name, source.Entity);
    }
  }
  return result;
}

function parseSelectItem(selectItem, sourceMap) {
  if (selectItem.Column) {
    const sourceName = expressionSourceName(selectItem.Column.Expression);
    return {
      kind: "column",
      table: sourceMap.get(sourceName) || "",
      name: selectItem.Column.Property,
      queryRef: selectItem.Name,
      nativeName: selectItem.NativeReferenceName,
    };
  }

  if (selectItem.Measure) {
    const sourceName = expressionSourceName(selectItem.Measure.Expression);
    return {
      kind: "measure",
      table: sourceMap.get(sourceName) || "",
      name: selectItem.Measure.Property,
      queryRef: selectItem.Name,
      nativeName: selectItem.NativeReferenceName,
    };
  }

  return null;
}

function parseLiteralValue(literal) {
  if (!literal || typeof literal.Value !== "string") return null;
  const rawValue = literal.Value;
  if (/^-?\d+L$/.test(rawValue)) return Number(rawValue.slice(0, -1));
  if (/^-?\d+(\.\d+)?$/.test(rawValue)) return Number(rawValue);
  if (rawValue.startsWith("'") && rawValue.endsWith("'")) {
    return rawValue.slice(1, -1).replace(/''/g, "'");
  }
  return rawValue;
}

function extractSlicerFilter(singleVisual) {
  if (singleVisual?.visualType !== "slicer") return null;

  const filter =
    singleVisual.objects?.general?.[0]?.properties?.filter?.filter ||
    singleVisual.objects?.general?.[0]?.properties?.filter?.expr?.Filter;
  const where = filter?.Where?.[0];
  const inFilter = where?.Condition?.In;
  const expression = inFilter?.Expressions?.[0]?.Column;
  const sourceName = expressionSourceName(expression?.Expression);
  const columnName = expression?.Property;
  const sourceMap = sourceEntityMap(filter);
  const tableName = sourceMap.get(sourceName);
  const values = (inFilter?.Values || [])
    .map((valueRow) => parseLiteralValue(valueRow?.[0]?.Literal))
    .filter((value) => value !== null && value !== undefined);

  if (!tableName || !columnName || values.length === 0) return null;

  return {
    table: tableName,
    column: columnName,
    values,
    dax: `TREATAS({${values.map(formatDaxValue).join(", ")}}, ${tableColumnRef(tableName, columnName)})`,
  };
}

function formatDaxValue(value) {
  if (typeof value === "number") return String(value);
  return `"${daxString(value)}"`;
}

function parseVisualContainer(container, pageName, pageIndex, visualIndex) {
  const config = safeParseJson(container.config);
  const singleVisual = config?.singleVisual;
  if (!singleVisual) return null;

  const visualType = singleVisual.visualType;
  const sourceMap = sourceEntityMap(singleVisual.prototypeQuery);
  const selectItems = (singleVisual.prototypeQuery?.Select || [])
    .map((selectItem) => parseSelectItem(selectItem, sourceMap))
    .filter(Boolean);

  const columns = selectItems.filter((selectItem) => selectItem.kind === "column");
  const measures = selectItems.filter((selectItem) => selectItem.kind === "measure");
  const slicerFilter = extractSlicerFilter(singleVisual);

  return {
    id: config.name || `visual_${pageIndex + 1}_${visualIndex + 1}`,
    pageName,
    visualType,
    position: {
      x: container.x,
      y: container.y,
      width: container.width,
      height: container.height,
      z: container.z,
    },
    columns,
    measures,
    slicerFilter,
    supported: SUPPORTED_VISUAL_TYPES.has(visualType) && measures.length > 0,
    skippedReason: SUPPORTED_VISUAL_TYPES.has(visualType)
      ? measures.length > 0
        ? ""
        : "no measure binding"
      : `unsupported visual type: ${visualType}`,
  };
}

function buildReportIndex(reportJsonPath) {
  const report = readJson(reportJsonPath);
  const pages = (report.sections || []).map((section, pageIndex) => {
    const visualContainers = section.visualContainers || [];
    const visuals = visualContainers
      .map((container, visualIndex) =>
        parseVisualContainer(
          container,
          section.displayName || section.name || `Page ${pageIndex + 1}`,
          pageIndex,
          visualIndex,
        ),
      )
      .filter(Boolean);

    const slicerFilters = visuals
      .map((visual) => visual.slicerFilter)
      .filter(Boolean);

    return {
      name: section.name,
      displayName: section.displayName || section.name,
      width: section.width,
      height: section.height,
      slicerFilters,
      visuals,
    };
  });

  return {
    reportJsonPath,
    generatedAt: new Date().toISOString(),
    pageCount: pages.length,
    visualCount: pages.reduce((total, page) => total + page.visuals.length, 0),
    supportedVisualCount: pages.reduce(
      (total, page) => total + page.visuals.filter((visual) => visual.supported).length,
      0,
    ),
    pages,
  };
}

function filtersForVisual(page, visual) {
  const filters = [];
  for (const pageFilter of page.slicerFilters || []) {
    const isSelfSlicer =
      visual.visualType === "slicer" &&
      pageFilter.table === visual.slicerFilter?.table &&
      pageFilter.column === visual.slicerFilter?.column;
    if (!isSelfSlicer) filters.push(pageFilter);
  }
  return filters;
}

function buildSummarizeDax(visual, filters, rowLimit) {
  const measure = visual.measures[0];
  if (!measure) return null;

  const filterDax = filters.map((filter) => filter.dax);
  const columnRefs = visual.columns.map((column) => tableColumnRef(column.table, column.name));
  const measureAlias = measure.nativeName || measure.name;
  const measureDax = `"${daxString(measureAlias)}", ${measureRef(measure.name)}`;

  if (columnRefs.length === 0) {
    const calculation = filterDax.length
      ? `CALCULATE(${measureRef(measure.name)}, ${filterDax.join(", ")})`
      : measureRef(measure.name);
    return `EVALUATE ROW("${daxString(measureAlias)}", ${calculation})`;
  }

  const summarizeArgs = [...columnRefs, ...filterDax, measureDax].join(",\n    ");
  const baseQuery = `SUMMARIZECOLUMNS(\n    ${summarizeArgs}\n  )`;

  if (visual.visualType === "lineChart" && visual.columns.length === 1) {
    return `EVALUATE\nTOPN(${rowLimit},\n  ${baseQuery},\n  ${columnRefs[0]}, ASC\n)`;
  }

  return `EVALUATE\nTOPN(${rowLimit},\n  ${baseQuery},\n  ${measureRef(measure.name)}, DESC\n)`;
}

class McpClient {
  constructor() {
    this.child = spawn(process.platform === "win32" ? "npx.cmd" : "npx", [
      "-y",
      "@microsoft/powerbi-modeling-mcp@latest",
      "--start",
    ], {
      stdio: ["pipe", "pipe", "pipe"],
      shell: process.platform === "win32",
      windowsHide: true,
    });
    this.nextId = 1;
    this.pending = new Map();
    this.buffer = "";

    this.child.stdout.on("data", (chunk) => this.onStdout(chunk));
    this.child.stderr.on("data", (chunk) => {
      const text = chunk.toString("utf8").trim();
      if (text && process.env.PBI_ANALYZER_VERBOSE) process.stderr.write(`${text}\n`);
    });
  }

  onStdout(chunk) {
    this.buffer += chunk.toString("utf8");
    let newlineIndex;
    while ((newlineIndex = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, newlineIndex).trim();
      this.buffer = this.buffer.slice(newlineIndex + 1);
      if (!line) continue;
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        continue;
      }
      if (message.id && this.pending.has(message.id)) {
        const request = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) request.reject(new Error(JSON.stringify(message.error)));
        else request.resolve(message.result);
      }
    }
  }

  send(method, params) {
    const id = this.nextId;
    this.nextId += 1;
    this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, method });
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`Timed out waiting for ${method}`));
        }
      }, 120000);
    });
  }

  notify(method, params) {
    this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", method, params })}\n`);
  }

  async initialize() {
    await this.send("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "ai-bi-mvp", version: "0.1.0" },
    });
    this.notify("notifications/initialized", {});
    await this.send("tools/list", {});
  }

  async callToolResult(name, args) {
    const result = await this.send("tools/call", { name, arguments: args });
    if (process.env.PBI_ANALYZER_DUMP_MCP) {
      process.stderr.write(`\n[MCP ${name}] ${JSON.stringify(result).slice(0, 8000)}\n`);
    }
    if (result?.isError) {
      const text = (result?.content || [])
        .map((item) => (typeof item.text === "string" ? item.text : ""))
        .join("\n");
      throw new Error(text || `${name} failed`);
    }
    return result;
  }

  async callTool(name, args) {
    const result = await this.callToolResult(name, args);
    const text = (result?.content || [])
      .map((item) => (typeof item.text === "string" ? item.text : ""))
      .join("\n");
    return text;
  }

  close() {
    this.child.kill();
  }
}

function parseJsonMaybe(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function findPowerBiPort(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const matches = [
    ...text.matchAll(/localhost[:=](\d{4,6})|Data Source=localhost:(\d{4,6})|port["']?\s*:\s*(\d{4,6})/gi),
  ];
  for (const match of matches) {
    const port = match[1] || match[2] || match[3];
    if (port) return port;
  }
  return "";
}

async function connectToOpenPowerBi(client) {
  const instancesText = await client.callTool("connection_operations", {
    request: { operation: "ListLocalInstances" },
  });
  const instancesJson = parseJsonMaybe(instancesText);
  const port = findPowerBiPort(instancesJson || instancesText);
  if (!port) throw new Error(`No open Power BI Desktop instance found: ${instancesText}`);

  const connectionString = `Provider=MSOLAP;Data Source=localhost:${port}`;
  const connectText = await client.callTool("connection_operations", {
    request: { operation: "Connect", connectionString },
  });
  const connectJson = parseJsonMaybe(connectText);
  const connectionName = connectJson?.data || connectJson?.Data || "";
  return { port, connectionString, connectionName, instancesText, connectText };
}

async function executeDax(client, dax, connectionName, rowLimit) {
  const attempts = [
    {
      request: {
        Operation: "Execute",
        ConnectionName: connectionName,
        Query: dax,
        MaxRows: rowLimit,
        GetExecutionMetrics: false,
      },
    },
    {
      request: {
        operation: "Execute",
        connectionName,
        Query: dax,
        MaxRows: rowLimit,
        GetExecutionMetrics: false,
      },
    },
    {
      request: {
        Operation: "Execute",
        Query: dax,
        MaxRows: rowLimit,
        GetExecutionMetrics: false,
      },
    },
  ];

  let lastError;
  for (const args of attempts) {
    try {
      return await client.callToolResult("dax_query_operations", args);
    } catch (error) {
      lastError = error;
    }
  }

  const helpText = await client.callTool("dax_query_operations", {
    request: { operation: "Help" },
  });
  throw new Error(`DAX query failed. Last error: ${lastError?.message}\nHelp:\n${helpText}`);
}

function parseCsv(text) {
  const lines = String(text || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .filter((line) => line.length > 0);
  if (lines.length === 0) return [];

  const parseLine = (line) => {
    const cells = [];
    let current = "";
    let inQuotes = false;
    for (let index = 0; index < line.length; index += 1) {
      const character = line[index];
      const nextCharacter = line[index + 1];
      if (character === '"' && inQuotes && nextCharacter === '"') {
        current += '"';
        index += 1;
      } else if (character === '"') {
        inQuotes = !inQuotes;
      } else if (character === "," && !inQuotes) {
        cells.push(current);
        current = "";
      } else {
        current += character;
      }
    }
    cells.push(current);
    return cells;
  };

  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseLine(line);
    const row = {};
    headers.forEach((header, index) => {
      const value = cells[index] ?? "";
      const numericValue = Number(value);
      row[header] = value !== "" && Number.isFinite(numericValue) ? numericValue : value;
    });
    return row;
  });
}

function parseDaxResult(result) {
  const csvResource = (result?.content || []).find(
    (item) => item.type === "resource" && item.resource?.mimeType === "text/csv",
  );
  if (csvResource?.resource?.text) {
    return {
      raw: {
        uri: csvResource.resource.uri,
        mimeType: csvResource.resource.mimeType,
      },
      rows: parseCsv(csvResource.resource.text),
    };
  }

  const text = (result?.content || [])
    .map((item) => (typeof item.text === "string" ? item.text : ""))
    .join("\n");
  const parsed = parseJsonMaybe(text);
  if (!parsed) return { raw: text, rows: [] };
  const data = parsed.data || parsed.Data || parsed;
  const rows =
    data.rows ||
    data.Rows ||
    data.results?.[0]?.tables?.[0]?.rows ||
    data.Results?.[0]?.Tables?.[0]?.Rows ||
    [];
  return { raw: parsed, rows: Array.isArray(rows) ? rows : [] };
}

function numericValues(rows, preferredKey) {
  return rows
    .map((row) => row[preferredKey] ?? row[`[${preferredKey}]`] ?? Object.values(row).find((value) => typeof value === "number"))
    .filter((value) => typeof value === "number" && Number.isFinite(value));
}

function formatNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value ?? "无");
  if (Math.abs(value) >= 1000000) return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  if (Math.abs(value) >= 1000) return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 4 });
}

function valueForMeasure(row, measureName) {
  if (!row) return undefined;
  return row[measureName] ?? row[`[${measureName}]`];
}

function categoryLabel(row, visual) {
  if (!row || visual.columns.length === 0) return "";
  const column = visual.columns[0];
  const directKey = `${column.table}[${column.name}]`;
  return row[directKey] ?? row[column.name] ?? Object.values(row)[0] ?? "";
}

function summarizeVisualResult(visual, queryResult) {
  const measureName = visual.measures[0]?.nativeName || visual.measures[0]?.name || "value";
  const rows = queryResult.rows || [];
  const values = numericValues(rows, measureName);
  const sortedRows = [...rows].sort((leftRow, rightRow) => {
    const leftValue = valueForMeasure(leftRow, measureName);
    const rightValue = valueForMeasure(rightRow, measureName);
    return (rightValue ?? Number.NEGATIVE_INFINITY) - (leftValue ?? Number.NEGATIVE_INFINITY);
  });
  const topRow = sortedRows[0] || rows[0] || null;
  const bottomRow = sortedRows[sortedRows.length - 1] || null;

  if (visual.columns.length === 0) {
    const value = valueForMeasure(topRow, measureName) ?? values[0];
    return {
      kind: "kpi",
      sentence: `${measureName} 为 ${formatNumber(value)}`,
      rowCount: rows.length,
      topRow,
    };
  }

  const maxValue = values.length ? Math.max(...values) : null;
  const minValue = values.length ? Math.min(...values) : null;
  const topLabel = categoryLabel(topRow, visual);
  const bottomLabel = categoryLabel(bottomRow, visual);
  return {
    kind: "distribution",
    sentence: `${measureName} 最高为 ${topLabel}（${formatNumber(maxValue)}），最低为 ${bottomLabel}（${formatNumber(minValue)}），样本 ${rows.length} 行`,
    rowCount: rows.length,
    topRow,
    bottomRow,
    maxValue,
    minValue,
  };
}

function renderMarkdown(analysis) {
  const lines = [];
  lines.push("# Power BI 报表 AI 分析数据包");
  lines.push("");
  lines.push(`- 生成时间：${analysis.generatedAt}`);
  lines.push(`- Power BI 端口：${analysis.powerBi?.port || "未连接"}`);
  lines.push(`- 页面数：${analysis.index.pageCount}`);
  lines.push(`- 可查询视觉对象：${analysis.results.length}`);
  lines.push("");

  for (const page of analysis.pages) {
    lines.push(`## ${page.displayName}`);
    lines.push("");
    if (page.slicerFilters.length) {
      lines.push(`- 页面筛选：${page.slicerFilters.map((filter) => `${filter.table}.${filter.column}=${filter.values.join(",")}`).join("；")}`);
    }
    for (const result of analysis.results.filter((item) => item.pageName === page.displayName)) {
      lines.push(`- ${result.visualId}（${result.visualType}）：${result.summary.sentence}`);
    }
    lines.push("");
  }

  lines.push("## 查询追溯");
  lines.push("");
  for (const result of analysis.results) {
    lines.push(`### ${result.pageName} / ${result.visualId}`);
    lines.push("");
    lines.push("```DAX");
    lines.push(result.dax);
    lines.push("```");
    lines.push("");
  }

  return `${lines.join("\n")}\n`;
}

async function main() {
  const options = parseArgs(process.argv);
  const index = buildReportIndex(options.reportJson);
  fs.mkdirSync(options.outputDir, { recursive: true });

  const indexPath = path.join(options.outputDir, "report-index.json");
  fs.writeFileSync(indexPath, `${JSON.stringify(index, null, 2)}\n`, "utf8");

  if (options.dryRun) {
    console.log(JSON.stringify({ indexPath, supportedVisualCount: index.supportedVisualCount }, null, 2));
    return;
  }

  const client = new McpClient();
  const analysis = {
    generatedAt: new Date().toISOString(),
    index,
    powerBi: null,
    pages: index.pages.map((page) => ({
      name: page.name,
      displayName: page.displayName,
      slicerFilters: page.slicerFilters,
    })),
    results: [],
    skipped: [],
  };

  try {
    await client.initialize();
    analysis.powerBi = await connectToOpenPowerBi(client);

    if (options.helpOnly) {
      const helpText = await client.callTool("dax_query_operations", {
        request: { operation: "Help" },
      });
      console.log(helpText);
      return;
    }

    for (const page of index.pages) {
      for (const visual of page.visuals) {
        if (!visual.supported) {
          analysis.skipped.push({
            pageName: page.displayName,
            visualId: visual.id,
            visualType: visual.visualType,
            reason: visual.skippedReason,
          });
          continue;
        }

        const filters = filtersForVisual(page, visual);
        const dax = buildSummarizeDax(visual, filters, options.rowLimit);
        try {
          const queryText = await executeDax(
            client,
            dax,
            analysis.powerBi.connectionName,
            options.rowLimit,
          );
          const queryResult = parseDaxResult(queryText);
          analysis.results.push({
            pageName: page.displayName,
            visualId: visual.id,
            visualType: visual.visualType,
            columns: visual.columns,
            measures: visual.measures,
            filters,
            dax,
            data: queryResult.rows,
            raw: queryResult.raw,
            summary: summarizeVisualResult(visual, queryResult),
          });
        } catch (error) {
          analysis.skipped.push({
            pageName: page.displayName,
            visualId: visual.id,
            visualType: visual.visualType,
            reason: error.message,
            dax,
          });
        }
      }
    }
  } finally {
    client.close();
  }

  const packagePath = path.join(options.outputDir, "analysis-package.json");
  const markdownPath = path.join(options.outputDir, "analysis-summary.md");
  fs.writeFileSync(packagePath, `${JSON.stringify(analysis, null, 2)}\n`, "utf8");
  fs.writeFileSync(markdownPath, renderMarkdown(analysis), "utf8");

  console.log(JSON.stringify({
    indexPath,
    packagePath,
    markdownPath,
    queriedVisuals: analysis.results.length,
    skippedVisuals: analysis.skipped.length,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
