import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../models/barangay_model.dart';

class BarangaySelectField extends StatelessWidget {
  final List<BarangayModel> barangays;
  final int? selectedId;
  final bool enabled;
  final ValueChanged<int?> onChanged;

  const BarangaySelectField({
    super.key,
    required this.barangays,
    required this.selectedId,
    required this.enabled,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final selected = barangays.where((item) => item.id == selectedId);
    return FormField<int>(
      initialValue: selectedId,
      enabled: enabled,
      validator: (value) =>
          value == null ? 'Please select your barangay' : null,
      builder: (field) => InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: !enabled
            ? null
            : () async {
                final id = await showModalBottomSheet<int>(
                  context: context,
                  isScrollControlled: true,
                  useSafeArea: true,
                  builder: (context) => _BarangaySearchSheet(
                    barangays: barangays,
                    selectedId: selectedId,
                  ),
                );
                if (id != null && field.mounted) {
                  field.didChange(id);
                  onChanged(id);
                }
              },
        child: InputDecorator(
          decoration: InputDecoration(
            enabled: enabled,
            errorText: field.errorText,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            errorBorder: InputBorder.none,
            focusedErrorBorder: InputBorder.none,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 12,
            ),
            prefixIcon: const Icon(
              Icons.location_on_outlined,
              color: AppColors.textMuted,
              size: 20,
            ),
            suffixIcon: const Icon(
              Icons.keyboard_arrow_down_rounded,
              color: AppColors.textMuted,
            ),
          ),
          child: Text(
            selected.isEmpty
                ? (barangays.isEmpty
                    ? 'No registered barangays are currently available.'
                    : 'Select your Barangay')
                : selected.first.displayName,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w500,
              color: selected.isEmpty || !enabled
                  ? AppColors.textHint
                  : AppColors.textPrimary,
            ),
          ),
        ),
      ),
    );
  }
}

class _BarangaySearchSheet extends StatefulWidget {
  final List<BarangayModel> barangays;
  final int? selectedId;

  const _BarangaySearchSheet({required this.barangays, this.selectedId});

  @override
  State<_BarangaySearchSheet> createState() => _BarangaySearchSheetState();
}

class _BarangaySearchSheetState extends State<_BarangaySearchSheet> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final matches = widget.barangays
        .where((item) => item.displayName.toLowerCase().contains(_query))
        .toList();

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.65,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 8, 0),
              child: Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Select your Barangay',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close',
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                autofocus: true,
                decoration: const InputDecoration(
                  labelText: 'Search barangay, municipality, or province',
                  prefixIcon: Icon(Icons.search),
                  border: OutlineInputBorder(),
                ),
                onChanged: (value) => setState(() {
                  _query = value.trim().toLowerCase();
                }),
              ),
            ),
            Expanded(
              child: matches.isEmpty
                  ? const Center(child: Text('No barangays found.'))
                  : ListView.builder(
                      keyboardDismissBehavior:
                          ScrollViewKeyboardDismissBehavior.onDrag,
                      itemCount: matches.length,
                      itemBuilder: (context, index) {
                        final barangay = matches[index];
                        return ListTile(
                          title: Text(barangay.displayName),
                          selected: barangay.id == widget.selectedId,
                          trailing: barangay.id == widget.selectedId
                              ? const Icon(Icons.check)
                              : null,
                          onTap: () => Navigator.pop(context, barangay.id),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
