import 'package:flutter/material.dart';
import '../core/network/api_client.dart';
import '../core/network/api_exception.dart';
import '../core/localization/app_language.dart';
import '../core/theme/app_colors.dart';
import '../models/auth_response.dart';
import '../services/auth_service.dart';
import '../services/storage_service.dart';
import '../widgets/kapitbayan_logo.dart';
import '../widgets/login_information_sheets.dart';
import '../widgets/login_credentials_section.dart';
import 'dashboard_screen.dart';
import 'register_screen.dart';
import 'admin_dashboard_screen.dart';
import 'field_official_screen.dart';
import 'forgot_password_screen.dart';

class LoginScreen extends StatefulWidget {
  final AuthService? authService;

  const LoginScreen({super.key, this.authService});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  AuthService? _authService;
  bool _obscurePassword = true;
  bool _isLoading = false;
  bool _isOfficialMode = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initializeAuthService();
  }

  Future<void> _initializeAuthService() async {
    if (widget.authService != null) {
      _authService = widget.authService;
    } else {
      final storage = await StorageService.init();
      final apiClient = ApiClient();
      _authService = AuthService(apiClient: apiClient, storageService: storage);
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    FocusScope.of(context).unfocus();

    if (_errorMessage != null) {
      setState(() {
        _errorMessage = null;
      });
    }

    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // Ensure auth service is initialized
      if (_authService == null) {
        final storage = await StorageService.init();
        final apiClient = ApiClient();
        _authService = AuthService(
          apiClient: apiClient,
          storageService: storage,
        );
      }

      final AuthResponse authResponse = await _authService!.login(
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );

      // Strict Portal Boundary Enforcement
      if (!_isOfficialMode && authResponse.user.isOfficial) {
        await _authService!.logout();
        if (!mounted) return;
        setState(() {
          _isLoading = false;
          _errorMessage =
              'Barangay Personnel must use Official Mode. Long-press the logo to switch.';
        });
        return;
      }

      if (_isOfficialMode && !authResponse.user.isOfficial) {
        await _authService!.logout();
        if (!mounted) return;
        setState(() {
          _isLoading = false;
          _errorMessage =
              'Citizen accounts cannot access the Barangay Personnel Portal.';
        });
        return;
      }

      // Refuse retired or unknown roles even if a stale client is given a token.
      if (!authResponse.user.isSupportedRole) {
        await _authService!.logout();
        if (!mounted) return;
        setState(() {
          _isLoading = false;
          _errorMessage = 'This account role is no longer supported. Contact your Barangay Administrator.';
        });
        return;
      }

      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _errorMessage = null;
      });

      final displayName = authResponse.user.fullName.isNotEmpty
          ? authResponse.user.fullName
          : authResponse.user.username;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle_rounded, color: Colors.white),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Welcome back, $displayName!',
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

      // Navigate to the appropriate screen based on user role tier
      Widget destinationScreen;
      if (authResponse.user.role.toUpperCase() == 'FIELD_OFFICIAL') {
        // Tier 3: Field Official / Tanod Portal
        destinationScreen = const FieldOfficialScreen();
      } else if (authResponse.user.isOfficial) {
        // Tier 2: Barangay Executive Admin Portal
        destinationScreen = const AdminDashboardScreen();
      } else {
        // Tier 4: Citizen Resident Dashboard
        destinationScreen = const DashboardScreen();
      }

      Navigator.of(
        context,
      ).pushReplacement(MaterialPageRoute(builder: (_) => destinationScreen));
    } on ForbiddenException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
      });
    } on UnauthorizedException catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.message;
      });
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
        _errorMessage = 'An unexpected error occurred. Please try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28.0),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: IntrinsicHeight(
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 36),

                        if (!_isOfficialMode)
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

                        // Logo & Brand Name with Hidden Toggle
                        Center(
                          child: GestureDetector(
                            onLongPress: () {
                              setState(() {
                                _isOfficialMode = !_isOfficialMode;
                                _errorMessage = null;
                              });
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    _isOfficialMode
                                        ? 'Barangay Personnel Official Mode Activated'
                                        : context.tr('Switched to Citizen Resident Portal'),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  backgroundColor: _isOfficialMode
                                      ? const Color(0xFFD97706)
                                      : const Color(0xFF0284C7),
                                  duration: const Duration(seconds: 2),
                                  behavior: SnackBarBehavior.floating,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                ),
                              );
                            },
                            child: const KapitBayanLogo(iconSize: 64, textSize: 24),
                          ),
                        ),
                        const SizedBox(height: 24),

                        if (_isOfficialMode) ...[
                          Center(
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFEF3C7),
                                borderRadius: BorderRadius.circular(20),
                                border: Border.all(
                                  color: const Color(0xFFFCD34D),
                                ),
                              ),
                              child: const Text(
                                'BARANGAY PERSONNEL ACCESS',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF92400E),
                                  letterSpacing: 0.8,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                        ] else ...[
                          const SizedBox(height: 16),
                        ],

                        Text(
                          _isOfficialMode ? 'Official Sign In' : context.tr('Welcome Back'),
                          style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _isOfficialMode
                              ? 'Authorized officials, Tanod, and barangay administrators'
                              : context.tr('Please enter your citizen credentials to continue'),
                          style: const TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w400,
                            color: AppColors.textSecondary,
                            height: 1.35,
                          ),
                        ),

                        const SizedBox(height: 40),

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

                        LoginCredentialsSection(
                          usernameController: _usernameController,
                          passwordController: _passwordController,
                          isOfficialMode: _isOfficialMode,
                          isLoading: _isLoading,
                          obscurePassword: _obscurePassword,
                          onTogglePasswordVisibility: () => setState(
                            () => _obscurePassword = !_obscurePassword,
                          ),
                          onForgotPassword: () => Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => ForgotPasswordScreen(
                                authService: _authService,
                              ),
                            ),
                          ),
                          onSubmit: _handleLogin,
                        ),

                        const SizedBox(height: 32),

                        // Don't have an account? Register here (Resident mode only)
                        if (!_isOfficialMode) ...[
                          const SizedBox(height: 32),
                          Center(
                            child: GestureDetector(
                              onTap: _isLoading
                                  ? null
                                  : () {
                                      Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => RegisterScreen(
                                            authService: _authService,
                                          ),
                                        ),
                                      );
                                    },
                              child: Text.rich(
                                const TextSpan(
                                  text: "Don't have an account? ",
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: AppColors.textSecondary,
                                    fontWeight: FontWeight.w500,
                                  ),
                                  children: [
                                    TextSpan(
                                      text: 'Register here',
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
                        ],

                        const Spacer(),
                        const SizedBox(height: 24),

                        // Footer Link: Privacy Policy
                        Center(
                          child: GestureDetector(
                            onTap: () => _showPrivacyPolicyModal(context),
                            child: const Text(
                              'PRIVACY POLICY',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: AppColors.textMuted,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  void _showPrivacyPolicyModal(BuildContext context) {
    showPrivacyPolicySheet(context);
  }
}
