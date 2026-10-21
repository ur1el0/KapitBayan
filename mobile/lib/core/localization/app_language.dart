import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppLanguageController extends ChangeNotifier {
  static const _preferenceKey = 'gridy_resident_language';
  String _languageCode = 'en';

  String get languageCode => _languageCode;
  bool get isFilipino => _languageCode == 'fil';

  static Future<AppLanguageController> load() async {
    final controller = AppLanguageController();
    try {
      final preferences = await SharedPreferences.getInstance();
      controller._languageCode = preferences.getString(_preferenceKey) == 'fil'
          ? 'fil'
          : 'en';
    } catch (_) {
      // Keep English if device preferences are unavailable.
    }
    return controller;
  }

  Future<void> setLanguage(String languageCode) async {
    final next = languageCode == 'fil' ? 'fil' : 'en';
    if (_languageCode == next) return;
    _languageCode = next;
    notifyListeners();
    try {
      final preferences = await SharedPreferences.getInstance();
      await preferences.setString(_preferenceKey, next);
    } catch (_) {
      // The choice remains active for the current app session.
    }
  }

  String translate(String source) =>
      isFilipino ? _filipino[source] ?? source : source;
}

class AppLanguageScope extends InheritedNotifier<AppLanguageController> {
  static final AppLanguageController _fallbackController =
      _EnglishFallbackLanguageController();

  const AppLanguageScope({
    super.key,
    required AppLanguageController controller,
    required super.child,
  }) : super(notifier: controller);

  static AppLanguageController of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppLanguageScope>();
    // Screens used outside the application shell (for example in tests and
    // previews) remain readable in English without sharing mutable language
    // state with other standalone screens.
    return scope?.notifier ?? _fallbackController;
  }
}

class _EnglishFallbackLanguageController extends AppLanguageController {
  @override
  Future<void> setLanguage(String languageCode) async {}
}

extension AppLanguageText on BuildContext {
  String tr(String source) => AppLanguageScope.of(this).translate(source);
}

const Map<String, String> _filipino = {
  'Official Sign In': 'Pag-sign in ng Kawani',
  'BARANGAY PERSONNEL ACCESS': 'PAGPASOK NG KAWANI NG BARANGAY',
  'Authorized officials, Tanod, and barangay administrators':
      'Mga awtorisadong opisyal, tanod, at administrador ng barangay.',
  'Barangay Personnel Official Mode Activated':
      'Naka-on ang opisyal na mode para sa mga kawani ng barangay.',
  'Official Email': 'Opisyal na Email',
  'Please enter your official email address':
      'Ilagay ang iyong opisyal na email address.',
  'Authenticate Official': 'Mag-sign in bilang Kawani',
  'Executive Console': 'Konsol ng Barangay',
  'Barangay Captain': 'Punong Barangay',
  'Logout': 'Mag-logout',
  'Executive Mode Active': 'Aktibo ang Mode ng Administrasyon',
  'OVERVIEW METRICS': 'MGA SUKAT NG PANGKALAHATANG-IDEYA',
  'Total Residents': 'Kabuuang Residente',
  'Pending Docs': 'Mga Nakabinbing Dokumento',
  'Waiting Queue': 'Naghihintay sa Pila',
  'Serving: {ticket}': 'Tinatawag: {ticket}',
  'Active Reports': 'Mga Aktibong Ulat',
  'EXECUTIVE OPERATIONS': 'MGA OPERASYON NG ADMINISTRASYON',
  'Field Operations Desk': 'Tanggapan ng Operasyon sa Field',
  'Advance queue ticker, verify clearance QR, triage incidents':
      'I-update ang pila, beripikahin ang QR ng sertipikasyon, at suriin ang mga insidente.',
  'Live Queue Desk': 'Tanggapan ng Live na Pila',
  'Monitor tickets, manage priority lane':
      'Subaybayan ang mga tiket at pamahalaan ang prayoridad.',
  'Welcome Back': 'Maligayang Pagbabalik',
  'Please enter your citizen credentials to continue':
      'Ilagay ang detalye ng iyong account upang magpatuloy.',
  'Username or Email': 'Username o Email',
  'Password': 'Password',
  'Forgot Password?': 'Nakalimutan ang Password?',
  'Sign In': 'Mag-sign In',
  'Create an Account': 'Gumawa ng Account',
  'Please provide your details to join our\ncommunity.':
      'Ilagay ang iyong detalye upang makasali sa\naming komunidad.',
  'Register Account': 'Irehistro ang Account',
  'Already have an account? ': 'May account ka na ba? ',
  'Login here': 'Mag-login dito',
  'Log in here': 'Mag-login dito',
  'Dashboard': 'Dashboard',
  'Queue': 'Pila',
  'Documents': 'Mga Dokumento',
  'Schedule': 'Iskedyul',
  'Announcements': 'Mga Anunsyo',
  'Assistance': 'Tulong',
  'Profile': 'Profile',
  'My Profile': 'Aking Profile',
  'Edit Profile': 'I-edit ang Profile',
  'Save Changes': 'I-save ang mga Pagbabago',
  'Cancel': 'Kanselahin',
  'Log Out': 'Mag-logout',
  'Language': 'Wika',
  'Choose language': 'Pumili ng wika',
  'English': 'English',
  'Filipino (Tagalog)': 'Filipino (Tagalog)',
  'Notification Preferences': 'Mga Paraan ng Pag-abiso',
  'Push notifications': 'Mga push notification',
  'Email updates': 'Mga update sa email',
  "Today's Queue": 'Pila Ngayong Araw',
  'Currently at Counter': 'Kasalukuyang Tinatawag',
  'Your Ticket': 'Iyong Numero sa Pila',
  'Estimated Call': 'Tinatayang Oras ng Tawag',
  'Live Capacity': 'Dami ng Naghihintay',
  'Get Ticket': 'Kumuha ng Numero',
  'Recent Completions': 'Mga Katatapos na Serbisyo',
  'No completed queue tickets yet': 'Wala pang natatapos na serbisyo sa pila.',
  'Request Document': 'Humiling ng Dokumento',
  'Request a Document': 'Humiling ng Dokumento',
  'Report an Issue': 'Mag-ulat ng Suliranin',
  'Submit Report': 'Ipadala ang Ulat',
  'Name': 'Pangalan',
  'Full name': 'Buong pangalan',
  'Contact number': 'Numero ng telepono',
  'Purok or Zone': 'Purok o Sona',
  'Barangay': 'Barangay',
  'Service Required': 'Serbisyong Kailangan',
  'Description': 'Paglalarawan',
  'Location': 'Lokasyon',
  'Category': 'Kategorya',
  'Urgency': 'Antas ng Pagkaapurahan',
  'Submit Request': 'Ipadala ang Kahilingan',
  'Request submitted successfully.': 'Naipadala na ang kahilingan.',
  'Issue reported successfully!': 'Naipadala na ang ulat tungkol sa suliranin.',
  'Push alerts are managed in profile settings.':
      'Pamahalaan ang mga push alert sa mga setting ng profile.',
  'Help & Tutorials': 'Tulong at mga Gabay',
  'Try again': 'Subukan muli',
  'Switched to Citizen Resident Portal': 'Lumipat sa Portal ng Residente',
  'BIRTH DATE': 'PETSA NG KAPANGANAKAN',
  'CONTACT NUMBER': 'NUMERO NG TELEPONO',
  'Choose how you receive queue, document, and community updates.':
      'Piliin kung paano mo matatanggap ang mga update tungkol sa pila, dokumento, at barangay.',
  'Could not load preferences. Try again.':
      'Hindi ma-load ang mga setting. Subukan muli.',
  'FULL NAME': 'BUONG PANGALAN',
  'Citizen ID / Username': 'ID ng residente / username',
  'Receive queue calls and service updates on this device.':
      'Tumanggap ng tawag sa pila at update sa serbisyo sa device na ito.',
  'Review your resident information, verification documents, and account details.':
      'Suriin ang iyong impormasyon, mga dokumento para sa pagpapatunay, at detalye ng account.',
  'Update your resident information and verification documents below.':
      'I-update sa ibaba ang iyong impormasyon at mga dokumento para sa pagpapatunay.',
  'CURRENTLY AT COUNTER': 'KASALUKUYANG TINATAWAG',
  'LIVE QUEUE STATUS': 'KALAGAYAN NG PILA',
  'Live Queue Unavailable': 'Hindi Makita ang Live na Pila',
  'Retry loading live queue status': 'Subukang i-load muli ang pila',
  'Retrying…': 'Sinusubukan muli…',
  'Ticket generated!': 'Nakuha na ang numero sa pila!',
  'Unable to connect to live queue desk.':
      'Hindi makakonekta sa pila ng barangay.',
  'Unable to connect to queue system.':
      'Hindi makakonekta sa sistema ng pila.',
  'Unable to load live queue status': 'Hindi ma-load ang kalagayan ng pila',
  'Viewing complete queue history': 'Ipinapakita ang buong kasaysayan ng pila',
  'Attach Photo': 'Maglakip ng Larawan',
  'Change Photo': 'Palitan ang Larawan',
  'Describe the issue in detail...': 'Ilarawan nang malinaw ang suliranin…',
  'History': 'Kasaysayan',
  'Issue Title': 'Pamagat ng Suliranin',
  'No photo attached': 'Walang kalakip na larawan',
  'Photo selected:': 'Napiling larawan:',
  'Please enter a description': 'Ilagay ang paglalarawan.',
  'Please enter a location': 'Ilagay ang lokasyon.',
  'Please enter a title': 'Ilagay ang pamagat.',
  'e.g. Broken Streetlight': 'hal. Sirang poste ng ilaw',
  'e.g. Main St. corner Elm St.': 'hal. Kanto ng Main St. at Elm St.',
  'DASHBOARD': 'DASHBOARD',
  'DOCUMENTS': 'MGA DOKUMENTO',
  'QUEUE': 'PILA',
  'SCHEDULE': 'ISKEDYUL',
  'Please enter your citizen ID or username':
      'Ilagay ang iyong citizen ID o username.',
  'Please enter your password': 'Ilagay ang iyong password.',
  'Sign In to Citizen Portal': 'Mag-sign In sa Portal ng Residente',
  'Barangay Hotline': 'Hotline ng Barangay',
  'Help & FAQs': 'Tulong at mga Madalas Itanong',
  'My Reports': 'Mga Ulat Ko',
  'Quick Services': 'Mga Serbisyong Mabilis Ma-access',
  'Report Issue': 'Mag-ulat ng Suliranin',
  'Request Assistance': 'Humiling ng Tulong',
  'PENDING VERIFICATION': 'NAKABINBIN ANG PAGPAPATUNAY',
  'VERIFIED RESIDENT': 'BERIPIKADONG RESIDENTE',
  'Welcome back': 'Maligayang pagbabalik',
  'Your status is current. All your records are up to date.':
      'Maayos ang katayuan mo. Napapanahon ang lahat ng iyong tala.',
  'Your status is current. There are': 'Maayos ang katayuan mo. Mayroon kang',
  'pending actions for your review.': 'nakabinbing aksyon na kailangang suriin.',
  'IDENTITY & RESIDENCY VERIFICATION':
      'PAGPAPATUNAY NG PAGKAKAKILANLAN AT PANINIRAHAN',
  'Document attached (Tap to view/edit)':
      'May kalakip na dokumento (Pindutin upang tingnan o i-edit)',
  'Required: upload at least one ID or proof of residency':
      'Kailangan: mag-upload ng kahit isang ID o patunay ng paninirahan',
  'Upload at least one image to register: a PhilSys ID, a secondary valid ID, or proof of residency such as a utility bill or lease. A typed ID number alone does not count.':
      'Mag-upload ng kahit isang larawan para makapagparehistro: PhilSys ID, pangalawang balidong ID, o patunay ng paninirahan gaya ng bill o kontrata sa upa. Hindi sapat ang pag-type lamang ng numero ng ID.',
  'PHILSYS NATIONAL ID NUMBER': 'NUMERO NG PHILSYS NATIONAL ID',
  'PHILSYS ID CARD PHOTO': 'LARAWAN NG PHILSYS ID CARD',
  'Upload PhilSys ID Photo': 'I-upload ang Larawan ng PhilSys ID',
  'BILLING STATEMENT TYPE': 'URI NG BILLING STATEMENT',
  'UPLOAD BILLING RECEIPT': 'I-UPLOAD ANG BILLING RECEIPT',
  'Upload Billing Receipt Photo': 'I-upload ang Larawan ng Billing Receipt',
  'SECONDARY VALID ID (OPTIONAL)': 'PANGALAWANG BALIDONG ID (OPSYONAL)',
  'UPLOAD SECONDARY ID': 'I-UPLOAD ANG PANGALAWANG ID',
  'Upload Secondary ID Photo': 'I-upload ang Larawan ng Pangalawang ID',
  'I consent to provide my personal data as a resident for barangay verification, in accordance with the RA 10173 Data Privacy Act.':
      'Sumasang-ayon akong ibigay ang aking personal na datos para sa pagpapatunay ng barangay, alinsunod sa RA 10173 o Data Privacy Act.',
  'Address details must be 255 characters or fewer':
      'Hindi dapat lumampas sa 255 character ang detalye ng tirahan.',
  'CONFIRM PASSWORD': 'KUMPIRMAHIN ANG PASSWORD',
  'DATE OF BIRTH': 'PETSA NG KAPANGANAKAN',
  'CONTACT NUMBER (OPTIONAL)': 'NUMERO NG TELEPONO (OPSYONAL)',
  'EMAIL ADDRESS': 'EMAIL ADDRESS',
  'BARANGAY ID / USERNAME': 'ID NG BARANGAY / USERNAME',
  'HOUSE / STREET / LANDMARK (OPTIONAL)':
      'BAHAY / KALYE / PALATANDAAN (OPSYONAL)',
  'LOCAL BARANGAY JURISDICTION': 'IYONG BARANGAY',
  'Loading approved barangays…': 'Kinukuha ang listahan ng mga aprubadong barangay…',
  'PASSWORD': 'PASSWORD',
  'PUROK / ZONE': 'PUROK / SONA',
  'Password must be at least 8 characters':
      'Dapat ay hindi bababa sa 8 character ang password.',
  'Passwords do not match': 'Hindi magkatugma ang mga password.',
  'Please confirm your password': 'Kumpirmahin ang iyong password.',
  'Please enter a password': 'Ilagay ang iyong password.',
  'Please enter a valid email address': 'Ilagay ang wastong email address.',
  'Please enter your Purok or Zone': 'Ilagay ang iyong purok o sona.',
  'Please enter your email address': 'Ilagay ang iyong email address.',
  'Please enter your full name': 'Ilagay ang iyong buong pangalan.',
  'Please enter your barangay ID or username':
      'Ilagay ang iyong ID ng barangay o username.',
  'Please enter your username': 'Ilagay ang iyong username.',
  'Purok or Zone must be 100 characters or fewer':
      'Hindi dapat lumampas sa 100 character ang purok o sona.',
  'Registered Voter in this Barangay': 'Botante sa Barangay na ito',
  'Residents under 18 must be registered under a verified parent or guardian.':
      'Ang wala pang 18 taong gulang ay kailangang irehistro ng beripikadong magulang o tagapag-alaga.',
  "GUARDIAN'S REGISTERED ID (REQUIRED)":
      'ID NG TAGAPAG-ALAGA NA NAKAREHISTRO (KINAKAILANGAN)',
  'Select your birth date': 'Piliin ang petsa ng iyong kapanganakan.',
  'No registered barangays are currently available.':
      'Wala pang aprubadong barangay sa ngayon.',
  'None / Not Applicable': 'Wala / Hindi Naaangkop',
  'Passport': 'Pasaporte',
  "Driver's License": 'Lisensya sa Pagmamaneho',
  'UMID': 'UMID',
  'Postal ID': 'Postal ID',
  "Voter's ID": 'Voter’s ID',
  'PRC ID': 'PRC ID',
  'Senior Citizen ID': 'Senior Citizen ID',
  'PWD ID': 'PWD ID',
  'Other Valid ID': 'Iba pang Balidong ID',
  'Electric / Meralco': 'Kuryente / Meralco',
  'Water Utility': 'Tubig',
  'Internet / Telecom': 'Internet / Telecom',
  'Barangay Certification': 'Sertipikasyon ng Barangay',
  'Lease Contract': 'Kontrata sa Pag-upa',
  'CENTRAL REGISTRY': 'PANGKALAHATANG TALAAN',
  'My Document Requests': 'Mga Kahilingan Kong Dokumento',
  'All topics': 'Lahat ng paksa',
  'Check your internet connection and try again. If the problem continues, contact your Barangay using verified office information.':
      'Tingnan ang koneksyon sa internet at subukan muli. Kung magpatuloy ang problema, kontakin ang barangay gamit ang beripikadong impormasyon ng tanggapan.',
  'Clear search': 'I-clear ang paghahanap',
  'Do not share your password, OTP, or identity documents in personal messages. Confirm local eligibility, fees, required documents, and office hours with your Barangay.':
      'Huwag ibahagi sa pribadong mensahe ang iyong password, OTP, o mga dokumento ng pagkakakilanlan. Kumpirmahin sa barangay ang kwalipikasyon, bayarin, mga kailangang dokumento, at oras ng opisina.',
  'Find answers about your account and Barangay services. Local steps and programs can differ, so confirm current instructions with your Barangay.':
      'Maghanap ng sagot tungkol sa iyong account at mga serbisyo ng barangay. Maaaring mag-iba ang proseso at programa, kaya kumpirmahin sa barangay ang kasalukuyang mga tagubilin.',
  'For current local instructions, contact your Barangay office.':
      'Para sa kasalukuyang tagubilin, kontakin ang tanggapan ng barangay.',
  'For example: request a document': 'Halimbawa: paghingi ng dokumento',
  'Help and FAQs': 'Tulong at mga Madalas Itanong',
  'Help could not be loaded.': 'Hindi ma-load ang tulong.',
  'No FAQs are available yet.': 'Wala pang mga madalas itanong.',
  'No answers match your search.': 'Walang sagot na tumutugma sa paghahanap mo.',
  'Open the simple tutorial for help finding services and using your account.':
      'Buksan ang gabay para matutunan kung paano hanapin ang mga serbisyo at gamitin ang iyong account.',
  'Search help questions and answers': 'Maghanap sa mga tanong at sagot',
  'Tutorial': 'Gabay',
  'Want a step-by-step guide?': 'Gusto mo ba ng sunod-sunod na gabay?',
  'A simple resident guide': 'Simpleng gabay para sa residente',
  'After signing in, use the menu or service cards to choose what you need. You can return to the Dashboard whenever you want.':
      'Pagkatapos mag-sign in, gamitin ang menu o mga card ng serbisyo para piliin ang kailangan mo. Maaari kang bumalik sa Dashboard anumang oras.',
  'Check queue and schedules': 'Tingnan ang pila at mga iskedyul',
  'Find other services': 'Maghanap ng iba pang serbisyo',
  'Make the app easier and safer to use': 'Gawing mas madali at ligtas gamitin ang app',
  'Open Announcements to read community updates. Check the date and details, and confirm urgent information with your Barangay through a verified contact.':
      'Buksan ang Mga Anunsyo para basahin ang mga update ng komunidad. Tingnan ang petsa at detalye, at kumpirmahin sa barangay ang mga agarang impormasyon gamit ang beripikadong contact.',
  'Open Documents, choose the service you need, and follow the instructions. Review your information before sending. Return to Documents later to check the request status.':
      'Buksan ang Mga Dokumento, piliin ang serbisyong kailangan mo, at sundin ang mga tagubilin. Suriin ang iyong impormasyon bago ipadala. Bumalik sa Mga Dokumento para tingnan ang kalagayan ng kahilingan.',
  'Open Queue for queue information. If your Barangay has posted an appointment or activity schedule, check the date, time, and location before going.':
      'Buksan ang Pila para sa impormasyon tungkol dito. Kung may iskedyul ng appointment o aktibidad ang barangay, tingnan ang petsa, oras, at lugar bago pumunta.',
  'Read community updates': 'Basahin ang mga update ng komunidad',
  'Request a document': 'Humiling ng dokumento',
  'Start at your Dashboard': 'Magsimula sa Dashboard',
  'Take one step at a time. You can open this guide whenever you need it. Button names may vary a little between the mobile app and website.\n\nNew here? On the sign-in screen, choose Register as Resident and follow the instructions. If a message says your account needs review, follow the message or contact your Barangay before making another account. If you already have an account, sign in and start at your Dashboard.':
      'Sundin ang mga hakbang nang paisa-isa. Maaari mong buksan ang gabay na ito anumang oras. Maaaring bahagyang magkaiba ang pangalan ng mga button sa mobile app at website.\n\nBago ka rito? Sa sign-in screen, piliin ang Magparehistro bilang Residente at sundin ang mga tagubilin. Kung may mensaheng kailangang suriin ang account mo, sundin ito o kontakin ang barangay bago gumawa ng panibagong account. Kung mayroon ka nang account, mag-sign in at magsimula sa Dashboard.',
  'Use Assistance or Report Issue when you need those services. Follow the instructions shown. Local requirements and service availability can differ.':
      'Gamitin ang Tulong o Mag-ulat ng Suliranin kung kailangan mo ang mga serbisyong ito. Sundin ang mga tagubilin. Maaaring mag-iba ang mga kinakailangan at serbisyong available sa bawat lugar.',
  'ACTIVE ONGOING REQUESTS': 'MGA KASALUKUYANG KAHILINGAN',
  'Active': 'Aktibo',
  'COMMUNITY CALENDAR': 'KALENDARYO NG KOMUNIDAD',
  'Calendar opened. Review and save the event there.':
      'Binuksan ang kalendaryo. Suriin at i-save doon ang aktibidad.',
  'Could not open your device calendar.': 'Hindi mabuksan ang kalendaryo ng iyong device.',
  'MY APPOINTMENTS': 'MGA APPOINTMENT KO',
  'No appointments scheduled for this date': 'Walang appointment sa petsang ito',
  'No community events scheduled': 'Walang nakaiskedyul na aktibidad ng komunidad',
  'Retry': 'Subukan muli',
  'Retrying...': 'Sinusubukan muli…',
  'Unable to load schedule data': 'Hindi ma-load ang mga iskedyul',
  'Unable to update appointments.': 'Hindi ma-update ang mga appointment.',
  'Unable to update community events.': 'Hindi ma-update ang mga aktibidad ng komunidad.',
  'Upcoming Events': 'Mga Susunod na Aktibidad',
  'View All Activities': 'Tingnan ang Lahat ng Aktibidad',
  'Community Schedule': 'Iskedyul ng Komunidad',
  'Trying again…': 'Sinusubukan muli…',
  'Search for certificates or permits...': 'Maghanap ng sertipiko o permit…',
  'No active document requests': 'Wala kang kasalukuyang kahilingan para sa dokumento',
  'No requests matching': 'Walang tumutugmang kahilingan para sa',
  'Tap any certificate above to submit a new request.': 'Pumili ng sertipiko sa itaas upang magpadala ng bagong kahilingan.',
  'Try adjusting your search query or clear the filter.': 'Baguhin ang hinahanap o alisin ang filter.',
  'ESTIMATED CALL': 'TANTYANG ORAS NG TAWAG',
  'LIVE CAPACITY': 'KASALUKUYANG DAMI NG NAGHIHINTAY',
  'Not available': 'Hindi available',
  'No completed queue tickets yet today': 'Wala pang natatapos na pila ngayong araw',
  'VIEW ALL': 'TINGNAN LAHAT',
  '1-3 Business Days': '1–3 araw ng trabaho',
  'DOCUMENT TYPE': 'URI NG DOKUMENTO',
  'Fill in the details below to submit your official request.': 'Punan ang mga detalye sa ibaba upang ipadala ang iyong opisyal na kahilingan.',
  'New Document Request': 'Bagong Kahilingan para sa Dokumento',
  'PROCESSING SPEED': 'BILIS NG PAGPROSESO',
  'Regular': 'Karaniwan',
  'Request for': 'Kahilingan para sa',
  'STATED PURPOSE (OPTIONAL)': 'LAYUNIN (OPSYONAL)',
  'Same Day / Priority': 'Ngayong araw / Prayoridad',
  'Urgent': 'Agarang Proseso',
  'e.g. For local employment application': 'hal. Para sa lokal na aplikasyon sa trabaho',
  'submitted successfully!': 'ay naipadala na!',
  'No matching certificate or permit type found.': 'Walang sertipiko o permit na tumutugma sa paghahanap.',
  'Request New': 'Humiling ng Bago',
  'View All': 'Tingnan Lahat',
  'Additional Notes (Optional)': 'Karagdagang Tala (Opsyonal)',
  'Barangay staff verify priority lane eligibility. If you qualify, ask the service desk to review your waiting ticket.':
      'Beripikahin ng kawani ng barangay kung kuwalipikado ka sa priority lane. Kung kuwalipikado, ipasuri sa service desk ang iyong numero sa pila.',
  'Close': 'Isara',
  'Request Queue Ticket': 'Kumuha ng Numero sa Pila',
  'e.g. Requesting 2 copies': 'hal. Humihingi ng 2 kopya',
  'Add to Calendar': 'Idagdag sa Kalendaryo',
  'No Active Ticket': 'Walang Aktibong Numero sa Pila',
  'Retry loading ticket': 'I-load muli ang numero sa pila',
  'Tap retry to check ticket status': 'Pindutin ang subukan muli upang tingnan ang kalagayan ng numero',
  'Unable to Load Ticket': 'Hindi Ma-load ang Numero sa Pila',
  'YOUR TICKET': 'IYONG NUMERO SA PILA',
  'Document Issuance': 'Pag-isyu ng Dokumento',
  'Tax Clearance': 'Sertipikasyon sa Buwis',
  'General Inquiry': 'Pangkalahatang Katanungan',
  'Certificate of Indigency': 'Sertipiko ng Indigency',
  'Residency Certificate': 'Sertipiko ng Paninirahan',
  'Community Tax Certificate (Cedula)': 'Community Tax Certificate (Cedula)',
  'Barangay\nClearance': 'Sertipikasyon ng\nBarangay',
  'Standard residency proof': 'Karaniwang patunay ng paninirahan',
  'Certificate of\nIndigency': 'Sertipiko ng\nIndigency',
  'For social service aid': 'Para sa tulong panlipunan',
  'Residency\nCertificate': 'Sertipiko ng\nPaninirahan',
  'Address verification': 'Pagpapatunay ng tirahan',
  'Local trade registration': 'Pagpaparehistro ng lokal na negosyo',
  'Vaccination Drive': 'Programa ng Bakunahan',
  'Town Hall Meeting': 'Pulong ng Barangay',
  'Eco-Waste Clean Up': 'Paglilinis para sa Kapaligiran',
  'Free basic immunization and health checkup for residents': 'Libreng bakuna at pagsusuri sa kalusugan para sa mga residente',
  'Quarterly barangay assembly and community forum': 'Kapat na pulong ng barangay at talakayan ng komunidad',
  'Barangay Center': 'Sentro ng Barangay',
  'Covered Court': 'Covered Court',
  'Rail Road Lines': 'Riles ng Tren',
  'PEACE AND ORDER': 'KAPAYAPAAN AT KAAYUSAN',
  'PUBLIC HEALTH': 'KALUSUGAN NG PUBLIKO',
  'INFRASTRUCTURE': 'IMPRASITRUKTURA',
  'ENVIRONMENT': 'KAPALIGIRAN',
  'OTHER': 'IBA PA',
  'MINOR': 'MABABA',
  'MODERATE': 'KATAMTAMAN',
  'HAZARD': 'PANGANIB',
  'EMERGENCY': 'EMERGENCY',
  'BROADCAST': 'ANUNSYO',
  'Barangay Bulletin': 'Mga Anunsyo ng Barangay',
  'Close Bulletin': 'Isara ang anunsyo',
  'No announcements broadcasted yet.': 'Wala pang inilalathalang anunsyo.',
  'PINNED ANNOUNCEMENT': 'NAKA-PIN NA ANUNSYO',
  'Recent': 'Kamakailan',
  'Could not launch phone dialer': 'Hindi mabuksan ang pantawag sa telepono',
  'Emergency Hotlines': 'Mga Emergency Hotline',
  'No matching emergency contacts found.': 'Walang nahanap na tumutugmang emergency contact.',
  'Number copied to clipboard': 'Nakopya ang numero',
  'Search hotlines, departments...': 'Maghanap ng hotline o tanggapan…',
  'Could not load reports.': 'Hindi ma-load ang mga ulat.',
  'Image unavailable': 'Hindi makita ang larawan',
  'My Report History': 'Kasaysayan ng mga Ulat Ko',
  'No reports submitted yet.': 'Wala ka pang naipapasang ulat.',
  'Could not enable push alerts. Allow notifications and check your connection, then try again.':
      'Hindi ma-enable ang push notification. Payagan ang mga notification, tingnan ang koneksyon, at subukan muli.',
  'Could not save notification preference.': 'Hindi na-save ang setting ng notification.',
  'How to use KapitBayan': 'Paano gamitin ang KapitBayan',
  '• To make text larger, use your phone’s text or display size setting.\n':
      '• Para palakihin ang teksto, gamitin ang setting ng laki ng teksto o display ng iyong telepono.\n',
  'Advisory Category: {category}\n\nOfficial notice regarding "{title}". Check your document requests or community bulletin for real-time status updates.':
      'Kategorya ng Paalala: {category}\n\nOpisyal na paalala tungkol sa "{title}". Tingnan ang iyong mga kahilingan sa dokumento o mga anunsyo ng barangay para sa kasalukuyang update.',
  'Dismiss': 'Isara',
  'No recent notifications': 'Walang bagong notification',
  'Notification Center': 'Sentro ng mga Notification',
  'Unable to load notifications': 'Hindi ma-load ang mga notification',
  'ANNOUNCEMENTS': 'MGA ANUNSYO',
  'MY PENDING\nREQUESTS': 'MGA NAKABINBIN\nKONG KAHILINGAN',
  'New': 'Bago',
  'No new notifications at this time.': 'Wala pang bagong notification sa ngayon.',
  'Recent Notifications': 'Mga Kamakailang Notification',
  'Retry loading notifications': 'Subukang i-load muli ang mga notification',
  'Some notifications could not load': 'May ilang notification na hindi na-load',
  'View all': 'Tingnan lahat',
  'Select Service': 'Pumili ng Serbisyo',
  "GUARDIAN'S REGISTERED USERNAME *": 'NAKAREHISTRO NANG USERNAME NG TAGAPAG-ALAGA *',
  'Could not load assistance requests.': 'Hindi ma-load ang mga kahilingan para sa tulong.',
  'Request submitted for barangay staff review.': 'Naipadala na ang kahilingan para suriin ng kawani ng barangay.',
  'Could not submit your assistance request.': 'Hindi naipadala ang iyong kahilingan para sa tulong.',
  'Under review': 'Sinusuri',
  'Approved': 'Naaprubahan',
  'Declined': 'Tinanggihan',
  'Pending review': 'Naghihintay ng pagsusuri',
  'Barangay Assistance': 'Tulong ng Barangay',
  'Request assistance': 'Humiling ng tulong',
  'Barangay staff will review your request manually. Submission does not guarantee approval.': 'Manu-manong susuriin ng kawani ng barangay ang iyong kahilingan. Hindi garantiya ng pag-apruba ang pagpapasa nito.',
  'Type of assistance': 'Uri ng tulong',
  'Reason for request': 'Dahilan ng kahilingan',
  'Submitting…': 'Ipinapadala…',
  'Submit for review': 'Ipadala para suriin',
  'Your requests': 'Iyong mga kahilingan',
  'No assistance requests have been submitted.': 'Wala pang naipapasang kahilingan para sa tulong.',
  'Assistance request': 'Kahilingan para sa tulong',
  'Staff note: ': 'Tala ng kawani: ',
  'Medical assistance': 'Tulong medikal',
  'Food assistance': 'Tulong sa pagkain',
  'Educational assistance': 'Tulong pang-edukasyon',
  'Emergency assistance': 'Tulong sa oras ng emergency',
  'Other barangay assistance': 'Iba pang tulong mula sa barangay',
  'Password Recovery': 'Pagbawi ng Password',
  'Set a new password': 'Magtakda ng bagong password',
  'Recover your account': 'Ibalik ang access sa account',
  'If the address is registered, a reset link was sent. Open it in your browser, or copy the complete link and paste it below to finish in this app.': 'Kung nakarehistro ang email, nagpadala kami ng link para magpalit ng password. Buksan ito sa browser o kopyahin ang buong link at idikit sa ibaba upang matapos sa app na ito.',
  'Enter the email address associated with your account. We will send reset instructions if it is registered.': 'Ilagay ang email address ng iyong account. Magpapadala kami ng tagubilin kung nakarehistro ito.',
  'Enter your email address.': 'Ilagay ang iyong email address.',
  'Enter a valid email address.': 'Maglagay ng wastong email address.',
  'Registered email': 'Nakarehistrong email',
  'Reset link from email': 'Link mula sa email',
  'Paste the complete password reset link': 'Idikit ang buong link para magpalit ng password',
  'Paste the complete, valid reset link from your email.': 'Idikit ang buo at wastong link mula sa iyong email.',
  'Paste reset link': 'Idikit ang reset link',
  'New password': 'Bagong password',
  'At least 8 characters': 'Hindi bababa sa 8 karakter',
  'Use at least 8 characters.': 'Gumamit ng hindi bababa sa 8 karakter.',
  'Confirm new password': 'Kumpirmahin ang bagong password',
  'Re-enter the new password': 'Ilagay muli ang bagong password',
  'Passwords do not match.': 'Hindi magkatugma ang mga password.',
  'Reset Password': 'Palitan ang password',
  'Send Reset Link': 'Ipadala ang link para magpalit ng password',
  'Use a different email': 'Gumamit ng ibang email',
  'Copy the reset link from your email first.': 'Kopyahin muna ang reset link mula sa iyong email.',
  'Password updated': 'Napalitan na ang password',
  'You can now return to the login screen and sign in with your new password.': 'Bumalik sa login screen at mag-sign in gamit ang bagong password.',
  'Return to Login': 'Bumalik sa pag-login',
  'No additional details provided.': 'Walang karagdagang detalye.',
  'OK': 'Sige',
};
