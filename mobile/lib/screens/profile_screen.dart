import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/network/api_exception.dart';
import '../core/theme/app_colors.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../services/push_notification_service.dart';
import '../widgets/custom_button.dart';
import '../widgets/custom_text_field.dart';
import '../widgets/kapitbayan_logo.dart';
import '../widgets/resident_evidence_edit_section.dart';
import '../widgets/resident_evidence_view_section.dart';
import '../widgets/resident_evidence_viewer_dialog.dart';
import 'login_screen.dart';

class ProfileScreen extends StatefulWidget {
  final UserModel user;
  final AuthService authService;
  final PushNotificationService? pushNotificationService;

  const ProfileScreen({
    super.key,
    required this.user,
    required this.authService,
    this.pushNotificationService,
  });

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _isEditing = false;
  bool _isSaving = false;
  late UserModel _currentUser;

  late TextEditingController _fullNameController;
  late TextEditingController _contactNumberController;
  DateTime? _birthDate;
  bool _voterStatus = false;
  bool _isLoadingNotificationPreferences = true;
  bool _isSavingNotificationPreference = false;
  bool _notificationPreferencesFailed = false;
  bool _emailAlerts = true;
  bool _pushAlerts = false;

  late TextEditingController _philsysIdController;
  XFile? _newPhilsysPhoto;
  bool _removePhilsysPhoto = false;

  String _secondaryIdType = 'Passport';
  bool _secondaryIdTypeChanged = false;
  XFile? _newSecondaryIdPhoto;
  bool _removeSecondaryIdPhoto = false;

  String _utilityBillingType = 'Electric / Meralco';
  bool _utilityBillingTypeChanged = false;
  XFile? _newUtilityBillingPhoto;
  bool _removeUtilityBillingPhoto = false;

  final ImagePicker _imagePicker = ImagePicker();

  static const List<String> _secondaryIdTypes = [
    'Passport',
    "Driver's License",
    'UMID',
    'Postal ID',
    "Voter's ID",
    'PRC ID',
    'Senior Citizen ID',
    'PWD ID',
    'Other Valid ID',
  ];

  static const List<String> _billingTypes = [
    'Electric / Meralco',
    'Water Utility',
    'Internet / Telecom',
    'Barangay Certification',
    'Lease Contract',
  ];

  @override
  void initState() {
    super.initState();
    _currentUser = widget.user;
    _fullNameController = TextEditingController();
    _contactNumberController = TextEditingController();
    _philsysIdController = TextEditingController();
    _resetFieldsFromUser();
    _loadNotificationPreferences();
  }

  Future<void> _loadNotificationPreferences() async {
    try {
      final response = await widget.authService.apiClient.get(
        '/auth/me/',
        requiresAuth: true,
      );
      if (response.statusCode != 200) {
        throw Exception('Notification preferences are unavailable.');
      }
      final data = jsonDecode(utf8.decode(response.bodyBytes))
          as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _emailAlerts = data['email_alerts'] as bool? ?? true;
        _pushAlerts = data['push_alerts'] as bool? ?? false;
        _notificationPreferencesFailed = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _notificationPreferencesFailed = true);
    } finally {
      if (mounted) setState(() => _isLoadingNotificationPreferences = false);
    }
  }

  Future<void> _updateNotificationPreference({
    required bool push,
    required bool enabled,
  }) async {
    if (push && enabled) {
      final service = widget.pushNotificationService ??
          PushNotificationService(apiClient: widget.authService.apiClient);
      final registered = await service.requestPermissionAndRegisterDevice();
      if (!registered) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Could not enable push alerts. Allow notifications and check your connection, then try again.',
            ),
          ),
        );
        return;
      }
    }

    if (!mounted) return;
    setState(() => _isSavingNotificationPreference = true);
    try {
      final field = push ? 'push_alerts' : 'email_alerts';
      final response = await widget.authService.apiClient.patch(
        '/auth/me/',
        body: {field: enabled},
        requiresAuth: true,
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('Notification preference update failed.');
      }
      if (!mounted) return;
      setState(() {
        if (push) {
          _pushAlerts = enabled;
        } else {
          _emailAlerts = enabled;
        }
      });
      if (push) {
        widget.pushNotificationService?.setPushEnabled(enabled);
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not save notification preference.')),
      );
    } finally {
      if (mounted) setState(() => _isSavingNotificationPreference = false);
    }
  }

  void _resetFieldsFromUser() {
    _fullNameController.text = _currentUser.fullName;
    _contactNumberController.text = _currentUser.contactNumber ?? '';
    _voterStatus = _currentUser.voterStatus ?? false;
    _birthDate =
        _currentUser.birthDate == null || _currentUser.birthDate!.isEmpty
        ? null
        : DateTime.tryParse(_currentUser.birthDate!);

    _philsysIdController.text = _currentUser.philsysIdNumber ?? '';
    _newPhilsysPhoto = null;
    _removePhilsysPhoto = false;

    _secondaryIdType = _currentUser.secondaryIdType ?? 'Passport';
    _secondaryIdTypeChanged = false;
    if (!_secondaryIdTypes.contains(_secondaryIdType)) {
      _secondaryIdType = 'Passport';
    }
    _newSecondaryIdPhoto = null;
    _removeSecondaryIdPhoto = false;

    _utilityBillingType = _currentUser.utilityBillingType ?? 'Electric / Meralco';
    _utilityBillingTypeChanged = false;
    if (!_billingTypes.contains(_utilityBillingType)) {
      _utilityBillingType = 'Electric / Meralco';
    }
    _newUtilityBillingPhoto = null;
    _removeUtilityBillingPhoto = false;
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _contactNumberController.dispose();
    _philsysIdController.dispose();
    super.dispose();
  }

  int _calculateEffectiveProofCount() {
    int count = 0;
    if (_newPhilsysPhoto != null) {
      count++;
    } else if (_currentUser.hasPhilsysPhoto && !_removePhilsysPhoto) {
      count++;
    }

    if (_newSecondaryIdPhoto != null) {
      count++;
    } else if (_currentUser.hasSecondaryIdPhoto && !_removeSecondaryIdPhoto) {
      count++;
    }

    if (_newUtilityBillingPhoto != null) {
      count++;
    } else if (_currentUser.hasUtilityBillingPhoto && !_removeUtilityBillingPhoto) {
      count++;
    }
    return count;
  }

  Future<void> _pickImage(void Function(XFile file) onSelected) async {
    try {
      final XFile? picked = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1600,
        maxHeight: 1600,
        imageQuality: 85,
      );
      if (picked != null) {
        setState(() {
          onSelected(picked);
        });
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to select image: $e'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  void _showDocumentViewer({
    required String title,
    required String relativeUrl,
  }) {
    ResidentEvidenceViewerDialog.show(
      context,
      title: title,
      loadImage: () => widget.authService.fetchPrivateMedia(relativeUrl),
    );
  }

  Future<void> _selectBirthDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _birthDate ?? DateTime(2000),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
    );
    if (picked != null && picked != _birthDate) {
      setState(() {
        _birthDate = picked;
      });
    }
  }

  String _formatDate(DateTime? date) {
    if (date == null) return 'Not provided';
    return "${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}";
  }

  Future<void> _saveProfile() async {
    setState(() => _isSaving = true);

    try {
      final updatedUser = await widget.authService.updateProfile(
        fullName: _fullNameController.text.trim(),
        contactNumber: _contactNumberController.text.trim(),
        birthDate: _birthDate != null ? _formatDate(_birthDate) : null,
        voterStatus: _voterStatus,
        philsysIdNumber: _philsysIdController.text.trim(),
        philsysPhoto: _newPhilsysPhoto,
        removePhilsysPhoto: _removePhilsysPhoto,
        secondaryIdType: _secondaryIdTypeChanged ? _secondaryIdType : null,
        secondaryIdPhoto: _newSecondaryIdPhoto,
        removeSecondaryIdPhoto: _removeSecondaryIdPhoto,
        utilityBillingType: _utilityBillingTypeChanged ? _utilityBillingType : null,
        utilityBillingPhoto: _newUtilityBillingPhoto,
        removeUtilityBillingPhoto: _removeUtilityBillingPhoto,
      );

      if (!mounted) return;

      setState(() {
        _currentUser = updatedUser;
        _isEditing = false;
        _isSaving = false;
        _resetFieldsFromUser();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Profile updated successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isSaving = false);

      final errorMessage =
          e is ApiException ? e.message : 'Failed to update profile: $e';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(errorMessage),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _logout(BuildContext context) async {
    await widget.authService.logout();
    if (context.mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final effectiveProofCount = _calculateEffectiveProofCount();
    final bool canRemoveProof = effectiveProofCount > 1;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    tooltip: 'Back',
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back_rounded),
                    color: AppColors.primaryNavy,
                  ),
                  TextButton.icon(
                    onPressed: _isSaving
                        ? null
                        : () {
                            setState(() {
                              if (_isEditing) _resetFieldsFromUser();
                              _isEditing = !_isEditing;
                            });
                          },
                    icon: Icon(
                      _isEditing ? Icons.close_rounded : Icons.edit_outlined,
                    ),
                    label: Text(_isEditing ? 'Cancel' : 'Edit Profile'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Center(child: KapitBayanLogo(iconSize: 64, textSize: 24)),
              const SizedBox(height: 32),
              const Text(
                'My Profile',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _isEditing
                    ? 'Update your resident information and verification documents below.'
                    : 'Review your resident information, verification documents, and account details.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 14.5,
                  fontWeight: FontWeight.w400,
                  color: AppColors.textSecondary,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 28),
              if (_isEditing) ...[
                CustomTextField(
                  label: 'FULL NAME',
                  controller: _fullNameController,
                  hintText: 'Your full name',
                  prefixIcon: Icons.person_outline_rounded,
                  enabled: !_isSaving,
                ),
                const SizedBox(height: 18),
                CustomTextField(
                  label: 'CONTACT NUMBER',
                  controller: _contactNumberController,
                  hintText: '09123456789',
                  prefixIcon: Icons.phone_outlined,
                  keyboardType: TextInputType.phone,
                  enabled: !_isSaving,
                ),
                const SizedBox(height: 18),
                const Text(
                  'BIRTH DATE',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF64748B),
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 8),
                InkWell(
                  onTap: _isSaving ? null : () => _selectBirthDate(context),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 16,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.inputBackground,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.calendar_today_rounded,
                          color: AppColors.textMuted,
                          size: 20,
                        ),
                        const SizedBox(width: 12),
                        Text(
                          _formatDate(_birthDate),
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: _birthDate != null
                                ? AppColors.textPrimary
                                : AppColors.textHint,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                SwitchListTile(
                  title: const Text(
                    'Registered Voter in this Barangay',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  value: _voterStatus,
                  activeThumbColor: AppColors.primaryNavy,
                  contentPadding: EdgeInsets.zero,
                  onChanged: _isSaving
                      ? null
                      : (value) => setState(() => _voterStatus = value),
                ),
                if (_currentUser.isResident) ...[
                  const SizedBox(height: 24),
                  ResidentEvidenceEditSection(
                    user: _currentUser,
                    philsysIdController: _philsysIdController,
                    newPhilsysPhoto: _newPhilsysPhoto,
                    removePhilsysPhoto: _removePhilsysPhoto,
                    onPickPhilsysPhoto: () => _pickImage((f) => _newPhilsysPhoto = f),
                    onRemovePhilsysPhoto: () => setState(() => _removePhilsysPhoto = true),
                    onUndoPhilsysRemoval: () => setState(() => _removePhilsysPhoto = false),
                    onClearPhilsysFile: () => setState(() => _newPhilsysPhoto = null),
                    secondaryIdType: _secondaryIdType,
                    secondaryIdTypes: _secondaryIdTypes,
                    onSecondaryIdTypeChanged: (val) {
                      if (val != null) {
                        setState(() {
                          _secondaryIdType = val;
                          _secondaryIdTypeChanged = true;
                        });
                      }
                    },
                    newSecondaryIdPhoto: _newSecondaryIdPhoto,
                    removeSecondaryIdPhoto: _removeSecondaryIdPhoto,
                    onPickSecondaryPhoto: () => _pickImage((f) => _newSecondaryIdPhoto = f),
                    onRemoveSecondaryPhoto: () => setState(() => _removeSecondaryIdPhoto = true),
                    onUndoSecondaryRemoval: () => setState(() => _removeSecondaryIdPhoto = false),
                    onClearSecondaryFile: () => setState(() => _newSecondaryIdPhoto = null),
                    utilityBillingType: _utilityBillingType,
                    utilityBillingTypes: _billingTypes,
                    onUtilityBillingTypeChanged: (val) {
                      if (val != null) {
                        setState(() {
                          _utilityBillingType = val;
                          _utilityBillingTypeChanged = true;
                        });
                      }
                    },
                    newUtilityBillingPhoto: _newUtilityBillingPhoto,
                    removeUtilityBillingPhoto: _removeUtilityBillingPhoto,
                    onPickUtilityPhoto: () => _pickImage((f) => _newUtilityBillingPhoto = f),
                    onRemoveUtilityPhoto: () => setState(() => _removeUtilityBillingPhoto = true),
                    onUndoUtilityRemoval: () => setState(() => _removeUtilityBillingPhoto = false),
                    onClearUtilityFile: () => setState(() => _newUtilityBillingPhoto = null),
                    canRemoveProof: canRemoveProof,
                    isSaving: _isSaving,
                  ),
                ],
                const SizedBox(height: 24),
                CustomButton(
                  text: 'Save Changes',
                  icon: Icons.check_rounded,
                  isLoading: _isSaving,
                  onPressed: _isSaving ? null : _saveProfile,
                ),
              ] else ...[
                _buildInfoTile('FULL NAME', _currentUser.fullName),
                _buildInfoTile('USERNAME', _currentUser.username),
                _buildInfoTile('EMAIL ADDRESS', _currentUser.email),
                _buildInfoTile(
                  'CONTACT NUMBER',
                  _currentUser.contactNumber ?? 'Not provided',
                ),
                _buildInfoTile(
                  'BIRTH DATE',
                  _currentUser.birthDate ?? 'Not provided',
                ),
                _buildInfoTile(
                  'VOTER STATUS',
                  _currentUser.voterStatus == true
                      ? 'Registered Voter'
                      : 'Not Registered',
                ),
                if (_currentUser.isResident) ...[
                  const SizedBox(height: 8),
                  ResidentEvidenceViewSection(
                    user: _currentUser,
                    onViewDocument: (title, relativeUrl) => _showDocumentViewer(
                      title: title,
                      relativeUrl: relativeUrl,
                    ),
                  ),
                  _buildNotificationPreferences(),
                ],
              ],
              const SizedBox(height: 36),
              SizedBox(
                height: 50,
                child: OutlinedButton.icon(
                  onPressed: _isSaving ? null : () => _logout(context),
                  icon: const Icon(
                    Icons.logout_rounded,
                    color: AppColors.error,
                  ),
                  label: const Text(
                    'Log Out',
                    style: TextStyle(
                      color: AppColors.error,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.error),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 28),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNotificationPreferences() {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Material(
        color: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        clipBehavior: Clip.antiAlias,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Padding(
                padding: EdgeInsets.only(top: 6, bottom: 4),
                child: Text(
                  'Notification Preferences',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              const Text(
                'Choose how you receive queue, document, and community updates.',
                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
              if (_isLoadingNotificationPreferences)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 18),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_notificationPreferencesFailed)
                TextButton.icon(
                  onPressed: _loadNotificationPreferences,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Could not load preferences. Try again.'),
                )
              else ...[
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _pushAlerts,
                  activeThumbColor: AppColors.primaryNavy,
                  title: const Text(
                    'Push notifications',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: const Text(
                    'Receive queue calls and service updates on this device.',
                  ),
                  onChanged: _isSavingNotificationPreference
                      ? null
                      : (enabled) => _updateNotificationPreference(
                          push: true,
                          enabled: enabled,
                        ),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _emailAlerts,
                  activeThumbColor: AppColors.primaryNavy,
                  title: const Text(
                    'Email updates',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    _currentUser.email.isEmpty
                        ? 'Add an email address to receive service updates.'
                        : 'Send service updates to ${_currentUser.email}.',
                  ),
                  onChanged: _isSavingNotificationPreference ||
                          _currentUser.email.isEmpty
                      ? null
                      : (enabled) => _updateNotificationPreference(
                          push: false,
                          enabled: enabled,
                        ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoTile(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              color: Color(0xFF64748B),
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            decoration: BoxDecoration(
              color: AppColors.inputBackground,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              value.isNotEmpty ? value : 'Not provided',
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
