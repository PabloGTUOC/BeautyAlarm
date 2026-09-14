import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/routine.dart';
import 'api_provider.dart';

final routineProvider = StateNotifierProvider<RoutineNotifier, AsyncValue<List<Routine>>>((ref) {
  return RoutineNotifier(ref);
});

class RoutineNotifier extends StateNotifier<AsyncValue<List<Routine>>> {
  final Ref ref;

  RoutineNotifier(this.ref) : super(const AsyncValue.loading()) {
    fetchRoutines();
  }

  Future<void> fetchRoutines() async {
    try {
      state = const AsyncValue.loading();
      final apiService = ref.read(apiServiceProvider);
      final routines = await apiService.getRoutines();
      state = AsyncValue.data(routines);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> addRoutine({
    required String productName,
    String? brand,
    required List<int> daysOfWeek,
    required String timePeriod,
  }) async {
    try {
      final apiService = ref.read(apiServiceProvider);
      
      // 1. Create the Product
      final product = await apiService.createProduct({
        'name': productName,
        'brand': brand,
        'notes': '',
      });

      // 2. Create the Routine linked to the Product
      await apiService.createRoutine({
        'product_id': product.id,
        'days_of_week': daysOfWeek,
        'time_period': timePeriod,
      });

      // 3. Refresh the routines list
      await fetchRoutines();
    } catch (e) {
      rethrow;
    }
  }
}
