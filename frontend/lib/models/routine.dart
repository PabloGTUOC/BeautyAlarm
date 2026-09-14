import 'product.dart';

class Routine {
  final int id;
  final int productId;
  final List<int> daysOfWeek;
  final String timePeriod;
  final String? notificationTime;
  final Product? product;

  Routine({
    required this.id,
    required this.productId,
    required this.daysOfWeek,
    required this.timePeriod,
    this.notificationTime,
    this.product,
  });

  factory Routine.fromJson(Map<String, dynamic> json) {
    return Routine(
      id: json['id'],
      productId: json['product_id'],
      daysOfWeek: List<int>.from(json['days_of_week']),
      timePeriod: json['time_period'],
      notificationTime: json['notification_time'],
      product: json['product'] != null ? Product.fromJson(json['product']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'product_id': productId,
      'days_of_week': daysOfWeek,
      'time_period': timePeriod,
      'notification_time': notificationTime,
    };
  }
}
