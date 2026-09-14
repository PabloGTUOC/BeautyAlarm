import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/daily_log.dart';
import 'api_provider.dart';

final dailyLogProvider = StateNotifierProvider<DailyLogNotifier, AsyncValue<List<DailyLog>>>((ref) {
  return DailyLogNotifier(ref);
});

class DailyLogNotifier extends StateNotifier<AsyncValue<List<DailyLog>>> {
  final Ref ref;

  DailyLogNotifier(this.ref) : super(const AsyncValue.loading()) {
    fetchLogs();
  }

  Future<void> fetchLogs() async {
    try {
      state = const AsyncValue.loading();
      final apiService = ref.read(apiServiceProvider);
      final logs = await apiService.getLogs();
      state = AsyncValue.data(logs);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> logCompletion(int routineId, String status) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      
      await apiService.createDailyLog({
        'routine_id': routineId,
        'timestamp': DateTime.now().toUtc().toIso8601String(),
        'status': status,
      });

      // Refresh logs
      await fetchLogs();
    } catch (e) {
      rethrow;
    }
  }
}
