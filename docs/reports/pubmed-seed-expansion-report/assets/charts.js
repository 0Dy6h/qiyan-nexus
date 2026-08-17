(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  // --- Chart 1: Corpus Growth ---
  var chart1 = echarts.init(document.getElementById('chart-corpus-growth'), null, { renderer: 'svg' });
  chart1.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true },
    legend: { data: ['PubMed Live 语料数'], bottom: 0, textStyle: { color: muted } },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      data: ['Baseline', 'Batch 1 后', 'Batch 2 后', '最终态'],
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '篇数',
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [{
      name: 'PubMed Live 语料数',
      type: 'bar',
      data: [344, 527, 659, 568],
      itemStyle: { color: accent, borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', color: ink, fontSize: 13, fontWeight: 600 },
      barWidth: '45%'
    }]
  });
  window.addEventListener('resize', function() { chart1.resize(); });

  // --- Chart 2: Metrics Evolution ---
  var chart2 = echarts.init(document.getElementById('chart-metrics-evolution'), null, { renderer: 'svg' });
  chart2.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true },
    legend: { data: ['Precision@5', 'MRR@5'], bottom: 0, textStyle: { color: muted } },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      data: ['v1 Baseline', 'v2 调参后', 'v3 语料扩展', 'v4 最新标注'],
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      max: 0.6,
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, formatter: function(v) { return (v * 100).toFixed(0) + '%'; } },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [
      {
        name: 'Precision@5',
        type: 'line',
        data: [0.113, 0.100, 0.280, 0.320],
        itemStyle: { color: accent },
        lineStyle: { color: accent, width: 2.5 },
        symbol: 'circle',
        symbolSize: 8,
        label: { show: true, color: ink, fontSize: 12, formatter: function(p) { return (p.value * 100).toFixed(1) + '%'; } }
      },
      {
        name: 'MRR@5',
        type: 'line',
        data: [0.163, 0.268, 0.488, 0.566],
        itemStyle: { color: accent2 },
        lineStyle: { color: accent2, width: 2.5 },
        symbol: 'circle',
        symbolSize: 8,
        label: { show: true, color: ink, fontSize: 12, formatter: function(p) { return (p.value * 100).toFixed(1) + '%'; } }
      }
    ]
  });
  window.addEventListener('resize', function() { chart2.resize(); });

  // --- Chart 3: Batch 1 Per-Topic Results ---
  var chart3 = echarts.init(document.getElementById('chart-batch1-topics'), null, { renderer: 'svg' });
  chart3.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true },
    legend: { data: ['保留候选 (kept)', '新增候选 (added)'], bottom: 0, textStyle: { color: muted } },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      data: ['PDE4', 'TSLP', '维生素D', '黄芩', '白鲜皮', '马拉色菌'],
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '候选数',
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [
      {
        name: '保留候选 (kept)',
        type: 'bar',
        data: [2, 0, 3, 5, 3, 4],
        itemStyle: { color: muted, borderRadius: [4, 4, 0, 0] },
        stack: 'total'
      },
      {
        name: '新增候选 (added)',
        type: 'bar',
        data: [3, 5, 2, 0, 2, 1],
        itemStyle: { color: accent, borderRadius: [4, 4, 0, 0] },
        stack: 'total'
      }
    ]
  });
  window.addEventListener('resize', function() { chart3.resize(); });

  // --- Chart 4: Term Dictionary Growth ---
  var chart4 = echarts.init(document.getElementById('chart-term-growth'), null, { renderer: 'svg' });
  chart4.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true },
    legend: { data: ['术语条目数'], bottom: 0, textStyle: { color: muted } },
    grid: { left: 50, right: 30, top: 30, bottom: 50 },
    xAxis: {
      type: 'category',
      data: ['初始 (调参)', 'Batch 2 补充', 'Batch 3 补充', '当前'],
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '条目数',
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [{
      name: '术语条目数',
      type: 'bar',
      data: [54, 69, 75, 84],
      itemStyle: {
        color: function(params) {
          var colors = [muted, accent, accent2, accent];
          return colors[params.dataIndex];
        },
        borderRadius: [4, 4, 0, 0]
      },
      label: { show: true, position: 'top', color: ink, fontSize: 13, fontWeight: 600 },
      barWidth: '45%'
    }]
  });
  window.addEventListener('resize', function() { chart4.resize(); });
})();
