import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class AnalysisScreen extends StatefulWidget {
  final int carId;
  const AnalysisScreen({super.key, required this.carId});
  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  final _api = ApiService();
  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await _api.analyzeCar(widget.carId);
      setState(() { _data = data; _loading = false; });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final carName = _data?['car']?['name'] ?? '車型分析';
    return Scaffold(
      appBar: AppBar(title: Text(carName)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _data == null
              ? const Center(child: Text('載入失敗'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildScoreChart(),
                      const SizedBox(height: 20),
                      _buildTopRecommendations(),
                      const SizedBox(height: 20),
                      _buildAllScoreDetails(),
                      const SizedBox(height: 20),
                      _buildOwnershipCost(),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
    );
  }

  // ========== 長條圖 ==========
  Widget _buildScoreChart() {
    final scores = (_data?['buyer_scores'] as List?) ?? [];
    if (scores.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('購車類型適配分析',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),
            SizedBox(
              height: 280,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  maxY: 100,
                  barTouchData: BarTouchData(
                    touchTooltipData: BarTouchTooltipData(
                      getTooltipItem: (group, gi, rod, ri) {
                        if (group.x < 0 || group.x >= scores.length) return null;
                        final item = scores[group.x] as Map<String, dynamic>;
                        return BarTooltipItem(
                          '${item['name'] ?? item['key']}\n${rod.toY.toInt()} 分',
                          const TextStyle(color: Colors.white, fontSize: 12),
                        );
                      },
                    ),
                  ),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 30,
                        getTitlesWidget: (val, meta) => Text(
                          '${val.toInt()}',
                          style: const TextStyle(fontSize: 10, color: Colors.grey),
                        ),
                      ),
                    ),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 50,
                        getTitlesWidget: (val, meta) {
                          final i = val.toInt();
                          if (i < 0 || i >= scores.length) return const SizedBox.shrink();
                          final item = scores[i] as Map<String, dynamic>;
                          final icon = item['icon'] ?? '';
                          final name = item['name'] ?? item['key'] ?? '';
                          return Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(icon, style: const TextStyle(fontSize: 16)),
                                Text(name,
                                    style: const TextStyle(fontSize: 9),
                                    textAlign: TextAlign.center),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: 25,
                    getDrawingHorizontalLine: (val) => FlLine(
                      color: Colors.grey[300]!,
                      strokeWidth: 0.5,
                    ),
                  ),
                  barGroups: List.generate(scores.length, (i) {
                    final item = scores[i] as Map<String, dynamic>;
                    final score = (item['score'] as num?)?.toDouble() ?? 0;
                    // 用 API 回傳的顏色，或 fallback
                    Color barColor;
                    final colorStr = item['color']?.toString();
                    if (colorStr != null && colorStr.startsWith('#') && colorStr.length == 7) {
                      barColor = Color(int.parse('FF${colorStr.substring(1)}', radix: 16));
                    } else {
                      barColor = score >= 90 ? AppTheme.betterColor
                          : score >= 70 ? AppTheme.primaryColor
                          : score >= 50 ? AppTheme.accentGold
                          : AppTheme.worseColor;
                    }
                    return BarChartGroupData(
                      x: i,
                      barRods: [
                        BarChartRodData(
                          toY: score,
                          width: 28,
                          color: barColor,
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                          backDrawRodData: BackgroundBarChartRodData(
                            show: true,
                            toY: 100,
                            color: Colors.grey[200],
                          ),
                        ),
                      ],
                      showingTooltipIndicators: score >= 90 ? [0] : [],
                    );
                  }),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ========== 前三名推薦 ==========
  Widget _buildTopRecommendations() {
    final scores = (_data?['buyer_scores'] as List?) ?? [];
    if (scores.isEmpty) return const SizedBox.shrink();

    // 取前三名（已排序）或自己排序
    final sorted = List<Map<String, dynamic>>.from(
      scores.map((e) => e as Map<String, dynamic>),
    )..sort((a, b) => ((b['score'] as num?) ?? 0).compareTo((a['score'] as num?) ?? 0));
    final top3 = sorted.take(3).toList();

    const medals = ['🥇', '🥈', '🥉'];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('最適合的購車類型',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            ...List.generate(top3.length, (i) {
              final item = top3[i];
              final score = item['score'] ?? 0;
              final grade = item['grade'] ?? '';
              final name = item['name'] ?? item['key'] ?? '';
              final icon = item['icon'] ?? '';
              final pros = (item['pros'] as List?)?.cast<String>() ?? [];
              final cons = (item['cons'] as List?)?.cast<String>() ?? [];

              return Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: i == 0
                      ? AppTheme.betterColor.withOpacity(0.06)
                      : Colors.grey[50],
                  borderRadius: BorderRadius.circular(12),
                  border: i == 0
                      ? Border.all(color: AppTheme.betterColor.withOpacity(0.3))
                      : null,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(medals[i], style: const TextStyle(fontSize: 22)),
                        const SizedBox(width: 8),
                        Text('$icon $name',
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w600)),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: score >= 90
                                ? AppTheme.betterColor
                                : score >= 70
                                    ? AppTheme.primaryColor
                                    : AppTheme.accentGold,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text('$grade  $score分',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13)),
                        ),
                      ],
                    ),
                    if (pros.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      ...pros.map((p) => Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: Row(
                              children: [
                                const Icon(Icons.check_circle,
                                    size: 14, color: AppTheme.betterColor),
                                const SizedBox(width: 6),
                                Flexible(child: Text(p,
                                    style: const TextStyle(fontSize: 13))),
                              ],
                            ),
                          )),
                    ],
                    if (cons.isNotEmpty && cons.first != '無明顯短板') ...[
                      const SizedBox(height: 4),
                      ...cons.map((c) => Padding(
                            padding: const EdgeInsets.only(bottom: 2),
                            child: Row(
                              children: [
                                const Icon(Icons.info_outline,
                                    size: 14, color: Colors.orange),
                                const SizedBox(width: 6),
                                Flexible(child: Text(c,
                                    style: const TextStyle(fontSize: 13))),
                              ],
                            ),
                          )),
                    ],
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  // ========== 全部分數明細（可展開） ==========
  Widget _buildAllScoreDetails() {
    final scores = (_data?['buyer_scores'] as List?) ?? [];
    if (scores.isEmpty) return const SizedBox.shrink();

    return Card(
      child: ExpansionTile(
        title: const Text('所有類型評分明細',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        children: scores.map((item) {
          final m = item as Map<String, dynamic>;
          final name = m['name'] ?? m['key'] ?? '';
          final icon = m['icon'] ?? '';
          final score = (m['score'] as num?)?.toInt() ?? 0;
          final grade = m['grade'] ?? '';
          return ListTile(
            leading: Text(icon, style: const TextStyle(fontSize: 20)),
            title: Text(name),
            trailing: SizedBox(
              width: 120,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  SizedBox(
                    width: 60,
                    child: LinearProgressIndicator(
                      value: score / 100,
                      backgroundColor: Colors.grey[200],
                      color: score >= 90
                          ? AppTheme.betterColor
                          : score >= 70
                              ? AppTheme.primaryColor
                              : score >= 50
                                  ? AppTheme.accentGold
                                  : AppTheme.worseColor,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text('$grade $score',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  // ========== 養車成本 ==========
  Widget _buildOwnershipCost() {
    final cost = _data?['ownership_cost'];
    if (cost == null) return const SizedBox.shrink();

    final annual = cost['annual'] as Map<String, dynamic>? ?? {};
    final monthly = cost['monthly_average'];
    final fiveYear = cost['five_year_total'];

    const labelMap = {
      'fuel': '⛽ 油資',
      'insurance': '🛡️ 保險',
      'tax': '📋 稅金',
      'maintenance': '🔧 保養',
      'total': '📊 年度合計',
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('預估養車成本',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            // 月 / 五年 摘要
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppTheme.primaryColor.withOpacity(0.1),
                          AppTheme.primaryColor.withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      children: [
                        const Text('💰 每月', style: TextStyle(color: Colors.grey)),
                        const SizedBox(height: 4),
                        Text('${_fmt(monthly)} 元',
                            style: const TextStyle(
                                fontSize: 22, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppTheme.accentGold.withOpacity(0.15),
                          AppTheme.accentGold.withOpacity(0.05),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      children: [
                        const Text('📅 五年', style: TextStyle(color: Colors.grey)),
                        const SizedBox(height: 4),
                        Text('${_fmt(fiveYear)} 元',
                            style: const TextStyle(
                                fontSize: 22, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 8),
            // 年度明細
            ...annual.entries
                .where((e) => e.key != 'total')
                .map((e) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(labelMap[e.key] ?? e.key,
                              style: const TextStyle(fontSize: 15)),
                          Text('${_fmt(e.value)} 元 / 年',
                              style: const TextStyle(
                                  fontSize: 15, fontWeight: FontWeight.w500)),
                        ],
                      ),
                    )),
            const Divider(),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(labelMap['total'] ?? '年度合計',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                  Text('${_fmt(annual['total'])} 元 / 年',
                      style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primaryColor)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _fmt(dynamic v) {
    if (v == null) return '---';
    final n = v is num ? v.toInt() : int.tryParse(v.toString()) ?? 0;
    final s = n.toString();
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(',');
      buf.write(s[i]);
    }
    return buf.toString();
  }
}
