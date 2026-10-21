import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'core/theme/app_theme.dart';
import 'core/localization/app_language.dart';
import 'core/navigation/app_navigation_keys.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/admin_dashboard_screen.dart';
import 'screens/field_official_screen.dart';
import 'services/storage_service.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  final storage = await StorageService.init();
  final languageController = await AppLanguageController.load();
  final user = storage.getUser();
  final hasValidSession = storage.getAccessToken() != null && user != null;

  Widget initialScreen = const LoginScreen();
  if (hasValidSession && user.isSupportedRole) {
    switch (user.role.toUpperCase()) {
      case 'ADMIN':
        initialScreen = const AdminDashboardScreen();
        break;
      case 'FIELD_OFFICIAL':
        initialScreen = const FieldOfficialScreen();
        break;
      default:
        initialScreen = const DashboardScreen();
        break;
    }
  } else if (hasValidSession) {
    // Clear cached retired/unknown roles so they cannot enter a resident or
    // staff workspace through a session created by an older app version.
    await storage.clearSession();
  }

  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );

  runApp(KapitBayanApp(home: initialScreen, languageController: languageController));
}

class KapitBayanApp extends StatelessWidget {
  final Widget? home;
  final AppLanguageController? languageController;

  const KapitBayanApp({super.key, this.home, this.languageController});

  @override
  Widget build(BuildContext context) {
    return AppLanguageScope(
      controller: languageController ?? AppLanguageController(),
      child: MaterialApp(
        navigatorKey: appNavigatorKey,
        scaffoldMessengerKey: appScaffoldMessengerKey,
        title: 'KapitBayan - Resident Portal',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        home: home ?? const LoginScreen(),
      ),
    );
  }
}
