import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/routine_provider.dart';

class AddRoutineScreen extends ConsumerStatefulWidget {
  const AddRoutineScreen({super.key});

  @override
  ConsumerState<AddRoutineScreen> createState() => _AddRoutineScreenState();
}

class _AddRoutineScreenState extends ConsumerState<AddRoutineScreen> {
  final _formKey = GlobalKey<FormState>();
  String _productName = '';
  String _brand = '';
  String _timePeriod = 'morning';
  bool _isLoading = false;

  void _submit() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      setState(() => _isLoading = true);

      try {
        await ref.read(routineProvider.notifier).addRoutine(
          productName: _productName,
          brand: _brand.isNotEmpty ? _brand : null,
          // For now, defaulting to everyday [1..7]
          daysOfWeek: [1, 2, 3, 4, 5, 6, 7],
          timePeriod: _timePeriod,
        );
        if (mounted) {
          Navigator.pop(context);
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to save routine: $e')),
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('Add Routine'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                decoration: const InputDecoration(labelText: 'Product Name'),
                validator: (value) => value == null || value.isEmpty ? 'Required' : null,
                onSaved: (value) => _productName = value ?? '',
              ),
              const SizedBox(height: 16),
              TextFormField(
                decoration: const InputDecoration(labelText: 'Brand (Optional)'),
                onSaved: (value) => _brand = value ?? '',
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _timePeriod,
                decoration: const InputDecoration(labelText: 'Time Period'),
                items: const [
                  DropdownMenuItem(value: 'morning', child: Text('Morning')),
                  DropdownMenuItem(value: 'night', child: Text('Night')),
                ],
                onChanged: (value) {
                  setState(() {
                    _timePeriod = value ?? 'morning';
                  });
                },
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: _isLoading ? null : _submit,
                child: _isLoading 
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Save Routine'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
