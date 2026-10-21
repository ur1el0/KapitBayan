import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/user_model.dart';
import '../models/barangay_model.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';
import '../widgets/custom_button.dart';
import '../widgets/resident_identity_verification_section.dart';
import '../widgets/resident_registration_details_section.dart';
import '../widgets/kapitbayan_logo.dart';
import 'login_screen.dart';

class RegisterScreen extends StatefulWidget {
  final AuthService? authService;

  const RegisterScreen({super.key, this.authService});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _fullNameController = TextEditingController();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();
  final TextEditingController _contactNumberController =
      TextEditingController();
  final TextEditingController _purokController = TextEditingController();
  final TextEditingController _addressDetailsController =
      TextEditingController();
  final TextEditingController _philsysIdController = TextEditingController();
  DateTime? _birthDate;
  int? _selectedBarangayId;
  List<BarangayModel> _barangays = const [];
  bool _isLoadingBarangays = true;
  String? _barangayLoadError;
  bool _voterStatus = false;
  bool _requiresGuardian = false;
  late TextEditingController _guardianController;

  // Identity & Residency Verification Proofs
  XFile? _philsysPhoto;
  String _utilityBillingType = 'Electric Bill';
  XFile? _utilityBillingPhoto;
  String _secondaryIdType = '';
  XFile? _secondaryIdPhoto;
  bool _dataPrivacyConsent = false;

  final ImagePicker _picker = ImagePicker();

  final List<String> _billingTypes = const [
    'Electric Bill',
    'Water Bill',
    'Internet / Telco Bill',
    'Lease Agreement',
    'Other Utility',
  ];

  final List<String> _secondaryIdTypes = const [
    '',
    'Passport',
    "Driver's License",
    'UMID',
    'Postal ID',
    'PRC ID',
    'Senior / PWD ID',
    'Student ID',
  ];

  AuthService? _authService;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initializeAuthService();
    _guardianController = TextEditingController();
  }

  Future<void> _initializeAuthService() async {
    if (widget.authService != null) {
      _authService = widget.authService;
    } else {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      _authService = AuthService(apiClient: apiClient, storageService: storage);
    }

    try {
      final barangays = await _authService!.fetchBarangays();
      if (!mounted) return;
      setState(() => _barangays = barangays);
    } catch (_) {
      if (!mounted) return;
      setState(
        () => _barangayLoadError =
            'Approved barangays could not be loaded. Check your connection and try again.',
      );
    } finally {
      if (mounted) setState(() => _isLoadingBarangays = false);
    }
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _contactNumberController.dispose();
    _purokController.dispose();
    _addressDetailsController.dispose();
    _guardianController.dispose();
    _philsysIdController.dispose();
    super.dispose();
  }

  Future<void> _pickImageSource(void Function(XFile?) onSelected) async {
    final ImageSource? source = await showModalBottomSheet<ImageSource>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(
                  Icons.photo_camera_rounded,
                  color: AppColors.primaryNavy,
                ),
                title: const Text(
                  'Take Photo with Camera',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                onTap: () => Navigator.pop(ctx, ImageSource.camera),
              ),
              ListTile(
                leading: const Icon(
                  Icons.photo_library_rounded,
                  color: AppColors.primaryNavy,
                ),
                title: const Text(
                  'Choose from Gallery',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                onTap: () => Navigator.pop(ctx, ImageSource.gallery),
              ),
            ],
          ),
        ),
      ),
    );

    if (source != null) {
      try {
        final XFile? picked = await _picker.pickImage(source: source);
        if (picked != null) {
          setState(() {
            onSelected(picked);
          });
        }
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to pick image: $e')));
      }
    }
  }

  Future<void> _handleRegister() async {
    FocusScope.of(context).unfocus();

    if (_errorMessage != null) {
      setState(() {
        _errorMessage = null;
      });
    }

    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    if (_requiresGuardian && _guardianController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please provide your Guardian\'s Registered ID'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (!_dataPrivacyConsent) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Please agree to the Data Privacy Act (RA 10173) consent.',
          ),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (_philsysPhoto == null &&
        _utilityBillingPhoto == null &&
        _secondaryIdPhoto == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Upload at least one ID or proof of residency photo to register.',
          ),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      if (_authService == null) {
        final storage = await StorageService.init();
        final apiClient = ApiClient();
        _authService = AuthService(
          apiClient: apiClient,
          storageService: storage,
        );
      }

      final UserModel user = await _authService!.register(
        fullName: _fullNameController.text.trim(),
        username: _usernameController.text.trim(),
        email: _emailController.text.trim(),
        password: _passwordController.text,
        birthDate: _birthDate != null
            ? "${_birthDate!.year}-${_birthDate!.month.toString().padLeft(2, '0')}-${_birthDate!.day.toString().padLeft(2, '0')}"
            : "2000-01-01",
        voterStatus: _voterStatus,
        privacyConsent: _dataPrivacyConsent,
        barangayId: _selectedBarangayId,
        contactNumber: _contactNumberController.text,
        purok: _purokController.text.trim(),
        addressDetails: _addressDetailsController.text.trim(),
        guardianId: _requiresGuardian ? _guardianController.text.trim() : null,
        philsysIdNumber: _philsysIdController.text.trim().isNotEmpty
            ? _philsysIdController.text.trim()
            : null,
        philsysPhoto: _philsysPhoto,
        utilityBillingType: _utilityBillingType,
        utilityBillingPhoto: _utilityBillingPhoto,
        secondaryIdType: _secondaryIdType.isNotEmpty ? _secondaryIdType : null,
        secondaryIdPhoto: _secondaryIdPhoto,
      );

      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _errorMessage = null;
      });

      final displayName = user.fullName.isNotEmpty
          ? user.fullName
          : user.username;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle_rounded, color: Colors.white),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Account created for $displayName! Please sign in.',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          backgroundColor: const Color(0xFF10B981),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      );

      _navigateToLogin();
    } on ValidationException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
      });
    } on NetworkException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage =
            'An unexpected error occurred during registration. Please try again.';
      });
    }
  }

  Future<void> _selectBirthDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _birthDate ?? DateTime(2000),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
    );
    if (picked != null && picked != _birthDate) {
      // Calculate age
      final today = DateTime.now();
      int age = today.year - picked.year;
      if (today.month < picked.month ||
          (today.month == picked.month && today.day < picked.day)) {
        age--;
      }

      setState(() {
        _birthDate = picked;
        _requiresGuardian = age < 18;
      });
    }
  }

  void _navigateToLogin() {
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
    } else {
      Navigator.of(
        context,
      ).pushReplacement(MaterialPageRoute(builder: (_) => const LoginScreen()));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const SizedBox(height: 32),

                Align(
                  alignment: Alignment.centerRight,
                  child: DropdownButton<String>(
                    value: AppLanguageScope.of(context).languageCode,
                    onChanged: (value) {
                      if (value != null) {
                        AppLanguageScope.of(context).setLanguage(value);
                      }
                    },
                    items: [
                      DropdownMenuItem(value: 'en', child: Text(context.tr('English'))),
                      DropdownMenuItem(value: 'fil', child: Text(context.tr('Filipino (Tagalog)'))),
                    ],
                  ),
                ),

                // Logo & Brand Name
                const KapitBayanLogo(iconSize: 64, textSize: 24),

                const SizedBox(height: 32),

                // Header Typography
                Text(
                  context.tr('Create an Account'),
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
                  context.tr('Please provide your details to join our\ncommunity.'),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w400,
                    color: AppColors.textSecondary,
                    height: 1.35,
                  ),
                ),

                // Dynamic Error Alert Banner
                if (_errorMessage != null) ...[
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEF2F2),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: const Color(0xFFFCA5A5),
                        width: 1,
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.error_outline_rounded,
                          color: Color(0xFFDC2626),
                          size: 20,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(
                              color: Color(0xFFB91C1C),
                              fontSize: 13.5,
                              fontWeight: FontWeight.w500,
                              height: 1.3,
                            ),
                          ),
                        ),
                        GestureDetector(
                          onTap: () {
                            setState(() {
                              _errorMessage = null;
                            });
                          },
                          child: const Icon(
                            Icons.close,
                            color: Color(0xFF991B1B),
                            size: 18,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 28),

                ResidentRegistrationDetailsSection(
                  fullNameController: _fullNameController,
                  usernameController: _usernameController,
                  emailController: _emailController,
                  passwordController: _passwordController,
                  confirmPasswordController: _confirmPasswordController,
                  contactNumberController: _contactNumberController,
                  purokController: _purokController,
                  addressDetailsController: _addressDetailsController,
                  guardianController: _guardianController,
                  barangays: _barangays,
                  selectedBarangayId: _selectedBarangayId,
                  isLoadingBarangays: _isLoadingBarangays,
                  barangayLoadError: _barangayLoadError,
                  obscurePassword: _obscurePassword,
                  obscureConfirmPassword: _obscureConfirmPassword,
                  birthDate: _birthDate,
                  requiresGuardian: _requiresGuardian,
                  voterStatus: _voterStatus,
                  isLoading: _isLoading,
                  onBarangayChanged: (value) =>
                      setState(() => _selectedBarangayId = value),
                  onTogglePasswordVisibility: () =>
                      setState(() => _obscurePassword = !_obscurePassword),
                  onToggleConfirmPasswordVisibility: () => setState(
                    () => _obscureConfirmPassword = !_obscureConfirmPassword,
                  ),
                  onSelectBirthDate: () => _selectBirthDate(context),
                  onVoterStatusChanged: (value) =>
                      setState(() => _voterStatus = value),
                  onSubmit: _handleRegister,
                ),

                ResidentIdentityVerificationSection(
                  philsysIdController: _philsysIdController,
                  philsysPhoto: _philsysPhoto,
                  utilityBillingPhoto: _utilityBillingPhoto,
                  secondaryIdPhoto: _secondaryIdPhoto,
                  utilityBillingType: _utilityBillingType,
                  secondaryIdType: _secondaryIdType,
                  billingTypes: _billingTypes,
                  secondaryIdTypes: _secondaryIdTypes,
                  dataPrivacyConsent: _dataPrivacyConsent,
                  isLoading: _isLoading,
                  onPickPhilsysPhoto: () => _pickImageSource(
                    (file) => setState(() => _philsysPhoto = file),
                  ),
                  onPickUtilityBillingPhoto: () => _pickImageSource(
                    (file) => setState(() => _utilityBillingPhoto = file),
                  ),
                  onPickSecondaryIdPhoto: () => _pickImageSource(
                    (file) => setState(() => _secondaryIdPhoto = file),
                  ),
                  onRemovePhilsysPhoto: () =>
                      setState(() => _philsysPhoto = null),
                  onRemoveUtilityBillingPhoto: () =>
                      setState(() => _utilityBillingPhoto = null),
                  onRemoveSecondaryIdPhoto: () =>
                      setState(() => _secondaryIdPhoto = null),
                  onUtilityBillingTypeChanged: (value) =>
                      setState(() => _utilityBillingType = value),
                  onSecondaryIdTypeChanged: (value) =>
                      setState(() => _secondaryIdType = value),
                  onPrivacyConsentChanged: (value) =>
                      setState(() => _dataPrivacyConsent = value ?? false),
                ),

                // Register Account Action Button
                CustomButton(
                  text: context.tr('Register Account'),
                  isLoading: _isLoading,
                  icon: Icons.arrow_forward_rounded,
                  onPressed: _handleRegister,
                ),

                const SizedBox(height: 28),

                // Already have an account? Login here
                Center(
                  child: GestureDetector(
                    onTap: _isLoading ? null : _navigateToLogin,
                    child: Text.rich(
                      TextSpan(
                        text: context.tr('Already have an account? '),
                        style: TextStyle(
                          fontSize: 14,
                          color: AppColors.textSecondary,
                          fontWeight: FontWeight.w500,
                        ),
                        children: [
                          TextSpan(
                            text: context.tr('Login here'),
                            style: TextStyle(
                              color: AppColors.primaryNavy,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ],
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),

                const SizedBox(height: 28),

                // Footer Terms & Privacy Notice
                const Text(
                  'BY REGISTERING, YOU AGREE TO OUR\nTERMS OF SERVICE & PRIVACY POLICY.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textHint,
                    letterSpacing: 0.8,
                    height: 1.4,
                  ),
                ),

                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
