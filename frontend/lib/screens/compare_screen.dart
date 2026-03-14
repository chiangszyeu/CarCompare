import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class CompareScreen extends StatefulWidget {
  final List<int> carIds;
  const CompareScreen({super.key, required this.carIds});
  @override
  State<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends State<CompareScreen> {
  final _api = ApiService();
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await _api.compareCars(widget.carIds);
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '載入失敗：$e';
        _loading = false;
      });
    }
  }

  Color _hlColor(String? hl) {
    switch (hl) {
      case 'better':  return AppTheme.betterColor;
      case 'worse':   return AppTheme.worseColor;
      case 'same':    return AppTheme.sameColor;
      default:        return AppTheme.neutralColor;
    }
  }

  IconData? _hlIcon(String? hl) {
    switch (hl) {
      case 'better':  return Icons.arrow_upward;
      case 'worse':   return Icons.arrow_downward;
      default:        return null;
    }
  }

  String _fmtPrice(dynamic v) {
    if (v == null) return '';
    final n = v is num ? v : num.tryParse(v.toString()) ?? 0;
    return '${(n / 10000).toStringAsFixed(1)} 萬';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('車型比較')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final cars = (_data?['cars'] ?? []) as List;
    final rows = (_data?['rows'] ?? []) as List;

    if (cars.isEmpty) {
      return const Center(child: Text('無車輛資料'));
    }

    return SingleChildScrollView(
      scrollDirection: Axis.vertical,
      child: Column(
        children: [
          // ===== 車型標題區 =====
          Container(
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
            color: AppTheme.primaryColor.withOpacity(0.05),
            child: Row(
              children: [
                const SizedBox(width: 110, child: Text('規格',
                    style: TextStyle(fontWeight: FontWeight.bold))),
                ...cars.map((car) {
                  final c = car as Map<String, dynamic>;
                  return Expanded(
                    child: Column(
                      children: [
                        Text(c['brand'] ?? '',
                            style: const TextStyle(fontSize: 11, color: Colors.grey)),
                        const SizedBox(height: 2),
                        Text(c['name'] ?? '',
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                        Text(_fmtPrice(c['msrp']),
                            style: const TextStyle(
                                color: AppTheme.primaryColor,
                                fontWeight: FontWeight.w600, fontSize: 13)),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
          const Divider(height: 1),

          // ===== 比較表格 =====
          ...rows.map((row) {
            final r = row as Map<String, dynamic>;
            final label = r['label'] ?? '';
            final unit = r['unit'];
            final cells = (r['cells'] ?? []) as List;
            final isImportant = r['is_important'] == true;

            return Container(
              decoration: BoxDecoration(
                color: isImportant ? AppTheme.accentGold.withOpacity(0.06) : null,
                border: Border(bottom: BorderSide(color: Colors.grey[200]!)),
              ),
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
              child: Row(
                children: [
                  // 欄位名稱
                  SizedBox(
                    width: 110,
                    child: Row(
                      children: [
                        if (isImportant)
                          Container(
                            width: 3, height: 16,
                            margin: const EdgeInsets.only(right: 6),
                            decoration: BoxDecoration(
                              color: AppTheme.accentGold,
                              borderRadius: BorderRadius.circular(2),
                            ),
                          ),
                        Flexible(
                          child: Text(label.toString(),
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: isImportant ? FontWeight.w600 : FontWeight.w500,
                                color: Colors.black54,
                              )),
                        ),
                      ],
                    ),
                  ),

                  // 各車數值
                  ...List.generate(cars.length, (i) {
                    if (i >= cells.length) {
                      return const Expanded(child: Center(child: Text('---')));
                    }
                    final cell = cells[i] as Map<String, dynamic>;
                    final displayVal = cell['display_value']?.toString() ?? '---';
                    final hl = cell['highlight']?.toString();
                    final diffText = cell['diff_text']?.toString();
                    final color = _hlColor(hl);
                    final icon = _hlIcon(hl);

                    // 顯示值 + 單位
                    final showVal = unit != null && unit.toString().isNotEmpty
                        ? '$displayVal $unit'
                        : displayVal;

                    return Expanded(
                      child: Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (icon != null)
                                Icon(icon, size: 14, color: color),
                              if (icon != null)
                                const SizedBox(width: 2),
                              Flexible(
                                child: Text(
                                  showVal,
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: color,
                                    fontWeight: hl == 'better'
                                        ? FontWeight.bold
                                        : FontWeight.normal,
                                    fontSize: 13,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          if (diffText != null && diffText.isNotEmpty && diffText != 'null')
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                diffText,
                                style: TextStyle(fontSize: 10, color: color),
                              ),
                            ),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            );
          }),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}
