import 'package:dio/dio.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  late final Dio _dio;

  ApiService._internal() {
    _dio = Dio(BaseOptions(
      // Chrome / macOS 桌面版用 localhost
      // Android 模擬器改成 http://10.0.2.2:8000
      // iOS 模擬器用 http://localhost:8000
      baseUrl: 'http://localhost:8000',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));
  }

  // 搜尋車型
  Future<Map<String, dynamic>> searchCars(String keyword) async {
    final res = await _dio.get('/api/cars/search', queryParameters: {'keyword': keyword});
    return res.data;
  }

  // 取得所有車型
  Future<Map<String, dynamic>> getAllCars() async {
    final res = await _dio.get('/api/cars/search');
    return res.data;
  }

  // 取得單一車型
  Future<Map<String, dynamic>> getCar(int id) async {
    final res = await _dio.get('/api/cars/$id');
    return res.data;
  }

  // 快速比較
  Future<Map<String, dynamic>> compareCars(List<int> ids) async {
    final idsStr = ids.join(',');
    final res = await _dio.get('/api/compare/quick', queryParameters: {'ids': idsStr});
    return res.data;
  }

  // 購車分析
  Future<Map<String, dynamic>> analyzeCar(int id) async {
    final res = await _dio.get('/api/analysis/$id');
    return res.data;
  }

  Future<Map<String, dynamic>> aiRecommend(String query) async {
    final res = await _dio.get('/api/ai/recommend', queryParameters: {'q': query});
    return res.data;
  }

  Future<Map<String, dynamic>> aiCompare(List<int> ids, {String? question}) async {
    final idsStr = ids.join(',');
    final params = <String, dynamic>{'ids': idsStr};
    if (question != null) params['q'] = question;
    final res = await _dio.get('/api/ai/compare', queryParameters: params);
    return res.data;
  }

}
