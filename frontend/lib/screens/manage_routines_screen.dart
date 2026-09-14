import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/routine_provider.dart';
import 'add_routine_screen.dart';

class ManageRoutinesScreen extends ConsumerWidget {
  const ManageRoutinesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routinesAsync = ref.watch(routineProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Manage Routines'),
      ),
      body: routinesAsync.when(
        data: (routines) {
          if (routines.isEmpty) {
            return const Center(
              child: Text('No routines found. Add one!'),
            );
          }

          return ListView.builder(
            itemCount: routines.length,
            itemBuilder: (context, index) {
              final routine = routines[index];
              return ListTile(
                title: Text(routine.product?.name ?? 'Unknown Product'),
                subtitle: Text('Time: ${routine.timePeriod} | Days: ${routine.daysOfWeek.length}'),
                trailing: IconButton(
                  icon: const Icon(Icons.delete, color: Colors.red),
                  onPressed: () {
                    // TODO: Implement delete
                  },
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const AddRoutineScreen()),
          );
        },
        child: const Icon(Icons.add),
      ),
    );
  }
}
