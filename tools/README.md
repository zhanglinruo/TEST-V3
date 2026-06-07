# Power BI Report Analyzer

读取 PBIP 报表结构，基于视觉对象字段绑定生成 DAX，通过 Power BI Modeling MCP 查询当前打开的 Power BI Desktop 语义模型，并输出可追溯的分析数据包。

## Usage

```powershell
node .\tools\powerbi_report_analyzer.js --limit 20
```

默认读取：

```text
D:\powerBI\test_db_generated\test_db_generated.Report\report.json
```

输出：

```text
outputs\powerbi-analysis\report-index.json
outputs\powerbi-analysis\analysis-package.json
outputs\powerbi-analysis\analysis-summary.md
```

## Notes

- 支持 `card`、`lineChart`、`barChart`、`clusteredColumnChart`、`tableEx`、`pivotTable` 的第一版查询。
- `textbox` 和 `slicer` 不直接查询，但切片器筛选会转成 `TREATAS` 应用到同页图表。
- 查询结果来自 Power BI Desktop 当前打开的 live 语义模型，而不是截图或 OCR。
