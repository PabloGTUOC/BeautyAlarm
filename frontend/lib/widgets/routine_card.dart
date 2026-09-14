import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/routine.dart';
import '../providers/daily_log_provider.dart';

class RoutineCard extends ConsumerStatefulWidget {
  final Routine routine;

  const RoutineCard({super.key, required this.routine});

  @override
  ConsumerState<RoutineCard> createState() => _RoutineCardState();
}

class _RoutineCardState extends ConsumerState<RoutineCard> {
  bool _isLoading = false;

  // In a full implementation, we'd check if there's already a log for TODAY
  // To keep it simple, we'll start with a local state based on if they just checked it.
  bool _isCompleted = false;

  void _toggleCompletion(bool? value) async {
    if (value == true) {
      setState(() => _isLoading = true);
      try {
        await ref.read(dailyLogProvider.notifier).logCompletion(
          widget.routine.id,
          'completed',
        );
        if (mounted) {
          setState(() {
            _isCompleted = true;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('${widget.routine.product?.name} logged!')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to log completion: $e')),
          );
        }
      } finally {
        if (mounted) {
          setState(() => _isLoading = false);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        leading: Icon(
          widget.routine.timePeriod == 'morning' ? Icons.wb_sunny : Icons.nights_stay,
          color: widget.routine.timePeriod == 'morning' ? Colors.orange : Colors.indigo,
        ),
        title: Text(
          widget.routine.product?.name ?? 'Unknown Product', 
          style: TextStyle(
            fontWeight: FontWeight.bold,
            decoration: _isCompleted ? TextDecoration.lineThrough : null,
          ),
        ),
        subtitle: Text(widget.routine.product?.brand ?? 'No Brand'),
        trailing: _isLoading
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Checkbox(
                value: _isCompleted,
                onChanged: _isCompleted ? null : _toggleCompletion,
              ),
      ),
    );
  }
}
