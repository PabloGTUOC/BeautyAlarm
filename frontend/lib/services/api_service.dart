import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/product.dart';
import '../models/routine.dart';
import '../models/daily_log.dart';

class ApiService {
  // Use a local IP for Android emulator (10.0.2.2) or iOS simulator (127.0.0.1)
  // When deploying, this should be the Cloudflare Tunnel URL.
  final String baseUrl = 'http://127.0.0.1:8000';
  
  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
  };

  // --- GET Methods ---
  
  Future<List<Product>> getProducts() async {
    final response = await http.get(Uri.parse('$baseUrl/products/'));
    if (response.statusCode == 200) {
      Iterable l = json.decode(response.body);
      return List<Product>.from(l.map((model) => Product.fromJson(model)));
    } else {
      throw Exception('Failed to load products');
    }
  }

  Future<List<Routine>> getRoutines() async {
    final response = await http.get(Uri.parse('$baseUrl/routines/'));
    if (response.statusCode == 200) {
      Iterable l = json.decode(response.body);
      return List<Routine>.from(l.map((model) => Routine.fromJson(model)));
    } else {
      throw Exception('Failed to load routines');
    }
  }

  Future<List<DailyLog>> getLogs() async {
    final response = await http.get(Uri.parse('$baseUrl/logs/'));
    if (response.statusCode == 200) {
      Iterable l = json.decode(response.body);
      return List<DailyLog>.from(l.map((model) => DailyLog.fromJson(model)));
    } else {
      throw Exception('Failed to load logs');
    }
  }

  // --- POST Methods ---

  Future<Product> createProduct(Map<String, dynamic> productData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/products/'),
      headers: _headers,
      body: json.encode(productData),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return Product.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create product');
    }
  }

  Future<Routine> createRoutine(Map<String, dynamic> routineData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/routines/'),
      headers: _headers,
      body: json.encode(routineData),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return Routine.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create routine');
    }
  }

  Future<DailyLog> createDailyLog(Map<String, dynamic> logData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/logs/'),
      headers: _headers,
      body: json.encode(logData),
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return DailyLog.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create daily log');
    }
  }
}
