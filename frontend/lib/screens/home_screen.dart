import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/routine_provider.dart';
import '../widgets/routine_card.dart';
import 'manage_routines_screen.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final routinesAsync = ref.watch(routineProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Today\'s Routine'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ManageRoutinesScreen()),
              );
            },
          )
        ],
      ),
      body: routinesAsync.when(
        data: (routines) {
          if (routines.isEmpty) {
            return const Center(
              child: Text('No routines for today! Add some routines to get started.'),
            );
          }

          final morningRoutines = routines.where((r) => r.timePeriod == 'morning').toList();
          final nightRoutines = routines.where((r) => r.timePeriod == 'night').toList();

          return ListView(
            padding: const EdgeInsets.all(16.0),
            children: [
              if (morningRoutines.isNotEmpty) ...[
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8.0),
                  child: Text('Morning', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                ),
                ...morningRoutines.map((routine) => RoutineCard(routine: routine)),
              ],
              if (nightRoutines.isNotEmpty) ...[
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8.0),
                  child: Text('Night', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                ),
                ...nightRoutines.map((routine) => RoutineCard(routine: routine)),
              ],
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
    );
  }
}
