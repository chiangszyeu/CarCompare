import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'ai_chat_screen.dart';
import '../theme/app_theme.dart';
import 'compare_screen.dart';
import 'analysis_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = ApiService();
  final _searchCtrl = TextEditingController();
  List<dynamic> _allCars = [];
  List<dynamic> _filteredCars = [];
  final Set<int> _selectedIds = {};
  bool _loading = false;

  // 篩選狀態
  String? _selectedBrand;
  String? _selectedBodyType;
  String _sortBy = 'price_asc';
  String? _selectedFuelType;
  RangeValues _priceRange = const RangeValues(0, 700);

  // 篩選選項
  List<String> _brands = [];
  List<String> _bodyTypes = [];
  List<String> _fuelTypes = [];

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() => _loading = true);
    try {
      final data = await _api.getAllCars();
      final items = data['items'] ?? [];
      setState(() {
        _allCars = items;
        _extractFilters();
        _applyFilters();
      });
    } catch (e) {
      _showError('無法連線至伺服器：$e');
    }
    setState(() => _loading = false);
  }

  void _extractFilters() {
    final brandSet = <String>{};
    final bodySet = <String>{};
    final fuelSet = <String>{};
    for (final car in _allCars) {
      final b = car['brand']?.toString();
      final bt = car['body_type']?.toString();
      final ft = car['fuel_type']?.toString();
      if (b != null && b.isNotEmpty) brandSet.add(b);
      if (bt != null && bt.isNotEmpty) bodySet.add(bt);
      if (ft != null && ft.isNotEmpty) fuelSet.add(ft);
    }
    _brands = brandSet.toList()..sort();
    _bodyTypes = bodySet.toList()..sort();
    _fuelTypes = fuelSet.toList()..sort();
  }

  void _applyFilters() {
    List<dynamic> result = List.from(_allCars);

    // 關鍵字搜尋
    final keyword = _searchCtrl.text.trim().toLowerCase();
    if (keyword.isNotEmpty) {
      result = result.where((car) {
        final name = (car['name'] ?? '').toString().toLowerCase();
        final brand = (car['brand'] ?? '').toString().toLowerCase();
        final brandZh = (car['brand_zh'] ?? '').toString().toLowerCase();
        final series = (car['series'] ?? '').toString().toLowerCase();
        return name.contains(keyword) || brand.contains(keyword) ||
            brandZh.contains(keyword) || series.contains(keyword);
      }).toList();
    }

    // 品牌篩選
    if (_selectedBrand != null) {
      result = result.where((c) => c['brand'] == _selectedBrand).toList();
    }

    // 車型篩選
    if (_selectedBodyType != null) {
      result = result.where((c) => c['body_type'] == _selectedBodyType).toList();
    }

    // 燃料篩選
    if (_selectedFuelType != null) {
      result = result.where((c) => c['fuel_type'] == _selectedFuelType).toList();
    }

    // 價格篩選
    result = result.where((c) {
      final msrp = c['msrp'];
      if (msrp == null) return true;
      final priceWan = (msrp is num ? msrp : num.tryParse(msrp.toString()) ?? 0) / 10000;
      return priceWan >= _priceRange.start && priceWan <= _priceRange.end;
    }).toList();

    // 排序
    result.sort((a, b) {
      final msrpA = (a['msrp'] as num?) ?? 0;
      final msrpB = (b['msrp'] as num?) ?? 0;
      final hpA = (a['horsepower'] as num?) ?? 0;
      final hpB = (b['horsepower'] as num?) ?? 0;
      switch (_sortBy) {
        case 'price_asc':  return msrpA.compareTo(msrpB);
        case 'price_desc': return msrpB.compareTo(msrpA);
        case 'hp_desc':    return hpB.compareTo(hpA);
        case 'hp_asc':     return hpA.compareTo(hpB);
        default:           return msrpA.compareTo(msrpB);
      }
    });

    setState(() => _filteredCars = result);
  }

  void _showError(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppTheme.worseColor),
    );
  }

  void _toggleSelect(int id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else if (_selectedIds.length < 4) {
        _selectedIds.add(id);
      } else {
        _showError('最多比較 4 台車');
      }
    });
  }

  void _goCompare() {
    if (_selectedIds.length < 2) {
      _showError('請至少選擇 2 台車進行比較');
      return;
    }
    Navigator.push(context,
      MaterialPageRoute(builder: (_) => CompareScreen(carIds: _selectedIds.toList())));
  }

  void _goAnalysis(int id) {
    Navigator.push(context,
      MaterialPageRoute(builder: (_) => AnalysisScreen(carId: id)));
  }

  String _formatPrice(dynamic msrp) {
    if (msrp == null) return '---';
    final val = msrp is num ? msrp : num.tryParse(msrp.toString()) ?? 0;
    return '${(val / 10000).toStringAsFixed(1)} 萬';
  }

  void _clearFilters() {
    setState(() {
      _selectedBrand = null;
      _selectedBodyType = null;
      _selectedFuelType = null;
      _sortBy = 'price_asc';
      _priceRange = const RangeValues(0, 700);
      _searchCtrl.clear();
    });
    _applyFilters();
  }

  bool get _hasActiveFilters =>
      _selectedBrand != null || _selectedBodyType != null ||
      _selectedFuelType != null || _priceRange.start > 0 || _priceRange.end < 700;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('🚗 CarCompare'),
        actions: [
          IconButton(
            icon: const Icon(Icons.auto_awesome),
            tooltip: 'AI 智慧推薦',
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const AiChatScreen())),
          ),
          if (_selectedIds.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilledButton.icon(
                onPressed: _goCompare,
                icon: const Icon(Icons.compare_arrows, size: 18),
                label: Text('比較 (${_selectedIds.length})'),
                style: FilledButton.styleFrom(
                  backgroundColor: AppTheme.accentGold,
                  foregroundColor: Colors.black87,
                ),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          // 搜尋欄
          Container(
            color: AppTheme.primaryColor,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: TextField(
              controller: _searchCtrl,
              onChanged: (_) => _applyFilters(),
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: '搜尋車型，例如：NX、GLC、Tesla、Mazda...',
                hintStyle: const TextStyle(color: Colors.white60),
                prefixIcon: const Icon(Icons.search, color: Colors.white70),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear, color: Colors.white70),
                  onPressed: () { _searchCtrl.clear(); _applyFilters(); },
                ),
                filled: true, fillColor: Colors.white24,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),

          // 品牌快速篩選
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              children: [
                _buildFilterChip('全部品牌', _selectedBrand == null, () {
                  setState(() => _selectedBrand = null);
                  _applyFilters();
                }),
                ..._brands.map((b) => _buildFilterChip(b, _selectedBrand == b, () {
                  setState(() => _selectedBrand = _selectedBrand == b ? null : b);
                  _applyFilters();
                })),
              ],
            ),
          ),

          // 車型 + 燃料 + 排序 + 價格
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Row(
              children: [
                // 車型下拉
                Expanded(
                  child: _buildDropdown(
                    value: _selectedBodyType,
                    hint: '車型',
                    icon: Icons.directions_car,
                    items: _bodyTypes,
                    onChanged: (v) { setState(() => _selectedBodyType = v); _applyFilters(); },
                  ),
                ),
                const SizedBox(width: 8),
                // 燃料下拉
                Expanded(
                  child: _buildDropdown(
                    value: _selectedFuelType,
                    hint: '燃料',
                    icon: Icons.local_gas_station,
                    items: _fuelTypes,
                    onChanged: (v) { setState(() => _selectedFuelType = v); _applyFilters(); },
                  ),
                ),
                const SizedBox(width: 8),
                // 排序下拉
                Expanded(
                  child: Container(
                    height: 36,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    decoration: BoxDecoration(
                      color: Colors.white, borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey[300]!),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: _sortBy,
                        isExpanded: true,
                        icon: const Icon(Icons.sort, size: 16),
                        style: const TextStyle(fontSize: 12, color: Colors.black87),
                        items: const [
                          DropdownMenuItem(value: 'price_asc',  child: Text('價格低→高')),
                          DropdownMenuItem(value: 'price_desc', child: Text('價格高→低')),
                          DropdownMenuItem(value: 'hp_desc',    child: Text('馬力高→低')),
                          DropdownMenuItem(value: 'hp_asc',     child: Text('馬力低→高')),
                        ],
                        onChanged: (v) { if (v != null) { setState(() => _sortBy = v); _applyFilters(); } },
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // 價格範圍滑桿
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Text('${_priceRange.start.toInt()}萬',
                    style: const TextStyle(fontSize: 11, color: Colors.grey)),
                Expanded(
                  child: RangeSlider(
                    values: _priceRange,
                    min: 0, max: 700, divisions: 70,
                    labels: RangeLabels(
                      '${_priceRange.start.toInt()}萬',
                      '${_priceRange.end.toInt()}萬',
                    ),
                    onChanged: (v) { setState(() => _priceRange = v); _applyFilters(); },
                  ),
                ),
                Text('${_priceRange.end.toInt()}萬',
                    style: const TextStyle(fontSize: 11, color: Colors.grey)),
              ],
            ),
          ),

          // 結果統計 + 清除篩選
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
            child: Row(
              children: [
                Text('共 ${_filteredCars.length} 台',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: Colors.grey)),
                if (_hasActiveFilters) ...[
                  const Spacer(),
                  GestureDetector(
                    onTap: _clearFilters,
                    child: const Text('清除篩選',
                        style: TextStyle(fontSize: 12, color: AppTheme.primaryColor, fontWeight: FontWeight.w500)),
                  ),
                ],
              ],
            ),
          ),

          // 已選車型提示
          if (_selectedIds.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              color: AppTheme.accentGold.withOpacity(0.15),
              child: Row(
                children: [
                  Text('已選 ${_selectedIds.length} 台',
                      style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13)),
                  const Spacer(),
                  GestureDetector(
                    onTap: () { setState(() => _selectedIds.clear()); },
                    child: const Text('取消全選',
                        style: TextStyle(fontSize: 12, color: Colors.red)),
                  ),
                ],
              ),
            ),

          // 車型列表
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _filteredCars.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.search_off, size: 48, color: Colors.grey[400]),
                            const SizedBox(height: 8),
                            const Text('找不到符合條件的車型'),
                            if (_hasActiveFilters)
                              TextButton(onPressed: _clearFilters, child: const Text('清除篩選')),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 4, 12, 80),
                        itemCount: _filteredCars.length,
                        itemBuilder: (ctx, i) => _buildCarCard(_filteredCars[i]),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, bool selected, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          decoration: BoxDecoration(
            color: selected ? AppTheme.primaryColor : Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: selected ? AppTheme.primaryColor : Colors.grey[300]!,
            ),
          ),
          child: Text(label,
              style: TextStyle(
                fontSize: 12,
                color: selected ? Colors.white : Colors.black87,
                fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
              )),
        ),
      ),
    );
  }

  Widget _buildDropdown({
    required String? value,
    required String hint,
    required IconData icon,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return Container(
      height: 36,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(8),
        border: Border.all(color: value != null ? AppTheme.primaryColor : Colors.grey[300]!),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          hint: Row(
            children: [
              Icon(icon, size: 14, color: Colors.grey),
              const SizedBox(width: 4),
              Text(hint, style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
          icon: const Icon(Icons.expand_more, size: 16),
          style: const TextStyle(fontSize: 12, color: Colors.black87),
          items: [
            DropdownMenuItem<String>(value: null, child: Text('全部$hint')),
            ...items.map((i) => DropdownMenuItem(value: i, child: Text(i))),
          ],
          onChanged: onChanged,
        ),
      ),
    );
  }

  Widget _buildCarCard(Map<String, dynamic> car) {
    final id = car['id'] as int;
    final selected = _selectedIds.contains(id);
    final brand = car['brand_zh'] ?? car['brand'] ?? '';
    final name = car['name'] ?? '';
    final year = car['year'] ?? '';
    final bodyType = car['body_type'] ?? '';
    final hp = car['horsepower'] ?? '';
    final fuel = car['fuel_economy_combined'];
    final fuelType = car['fuel_type'] ?? '';
    final drivetrain = car['drivetrain'] ?? '';
    final msrp = _formatPrice(car['msrp']);

    // 燃料類型顏色標籤
    Color fuelColor;
    if (fuelType.contains('電動')) {
      fuelColor = Colors.green;
    } else if (fuelType.contains('油電') || fuelType.contains('混合')) {
      fuelColor = Colors.teal;
    } else {
      fuelColor = Colors.blueGrey;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: selected
            ? const BorderSide(color: AppTheme.primaryColor, width: 2.5)
            : BorderSide.none,
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _toggleSelect(id),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              // 選取圈
              Container(
                width: 36, height: 36,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: selected ? AppTheme.primaryColor : Colors.grey[200],
                ),
                child: selected
                    ? const Icon(Icons.check, color: Colors.white, size: 20)
                    : Center(child: Text('$id',
                        style: TextStyle(color: Colors.grey[600], fontWeight: FontWeight.bold, fontSize: 12))),
              ),
              const SizedBox(width: 12),
              // 車輛資訊
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('$brand $name',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                        maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _buildTag(bodyType, Colors.blueGrey),
                        const SizedBox(width: 4),
                        _buildTag(fuelType, fuelColor),
                        const SizedBox(width: 4),
                        _buildTag(drivetrain, Colors.deepPurple),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$year年 · ${hp}hp · ${fuel != null ? "${fuel}km/L" : ""}',
                      style: TextStyle(color: Colors.grey[600], fontSize: 12),
                    ),
                  ],
                ),
              ),
              // 價格 + 分析
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(msrp,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.primaryColor)),
                  const SizedBox(height: 6),
                  GestureDetector(
                    onTap: () => _goAnalysis(id),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.accentGold.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Text('分析 →',
                          style: TextStyle(color: AppTheme.accentGold, fontWeight: FontWeight.w600, fontSize: 12)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTag(String text, Color color) {
    if (text.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(text, style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w500)),
    );
  }
}
