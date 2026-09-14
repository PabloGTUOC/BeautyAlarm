import 'routine.dart';

class DailyLog {
  final int id;
  final int routineId;
  final DateTime timestamp;
  final String status;
  final Routine? routine;

  DailyLog({
    required this.id,
    required this.routineId,
    required this.timestamp,
    required this.status,
    this.routine,
  });

  factory DailyLog.fromJson(Map<String, dynamic> json) {
    return DailyLog(
      id: json['id'],
      routineId: json['routine_id'],
      timestamp: DateTime.parse(json['timestamp']),
      status: json['status'],
      routine: json['routine'] != null ? Routine.fromJson(json['routine']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'routine_id': routineId,
      'timestamp': timestamp.toIso8601String(),
      'status': status,
    };
  }
}
