import 'my_issues_screen.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../core/localization/app_language.dart';
import '../core/network/api_client.dart';
import '../services/issue_service.dart';
import '../services/storage_service.dart';

class ReportIssueScreen extends StatefulWidget {
  const ReportIssueScreen({super.key});

  @override
  State<ReportIssueScreen> createState() => _ReportIssueScreenState();
}

class _ReportIssueScreenState extends State<ReportIssueScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _locationController = TextEditingController();
  final _descriptionController = TextEditingController();

  final ImagePicker _picker = ImagePicker();
  XFile? _selectedImage;
  String _selectedCategory = 'OTHER';
  String _selectedUrgency = 'MINOR';

  final List<String> _categories = [
    'PEACE_AND_ORDER', 'PUBLIC_HEALTH', 'INFRASTRUCTURE', 'ENVIRONMENT', 'OTHER'
  ];
  final List<String> _urgencies = [
    'MINOR', 'MODERATE', 'HAZARD', 'EMERGENCY'
  ];
  bool _isLoading = false;
  
  IssueService? _issueService;

  @override
  void initState() {
    super.initState();
    _initService();
  }

  Future<void> _initService() async {
    final storage = await StorageService.init();
    final apiClient = ApiClient();
    final token = storage.getAccessToken();
    if (token != null) {
      apiClient.setAuthCredentials(accessToken: token);
    }
    setState(() {
      _issueService = IssueService(apiClient: apiClient);
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _locationController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() {
        _selectedImage = image;
      });
    }
  }

  Future<void> _submitReport() async {
    if (!_formKey.currentState!.validate()) return;
    if (_issueService == null) return;

    setState(() => _isLoading = true);

    try {
      await _issueService!.submitIssue(
        title: _titleController.text,
        description: _descriptionController.text,
        location: _locationController.text,
        category: _selectedCategory,
        urgency: _selectedUrgency,
        imageFile: _selectedImage,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(context.tr('Issue reported successfully!'))),
        );
        Navigator.pop(context); // Return to dashboard
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          context.tr('Report an Issue'),
          style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Color(0xFF0F172A)),
        actions: [
          TextButton.icon(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const MyIssuesScreen()), // Assuming you import it!
              );
            },
            icon: const Icon(Icons.history, size: 18),
            label: Text(context.tr('History')),
            style: TextButton.styleFrom(
              foregroundColor: const Color(0xFF2563EB), // Tailwind Blue 600
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _issueService == null
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextFormField(
                      controller: _titleController,
                      decoration: InputDecoration(
                        labelText: context.tr('Issue Title'),
                hintText: context.tr('e.g. Broken Streetlight'),
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) =>
                          value!.isEmpty ? context.tr('Please enter a title') : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _locationController,
                      decoration: InputDecoration(
                        labelText: context.tr('Location'),
                        hintText: context.tr('e.g. Main St. corner Elm St.'),
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) =>
                          value!.isEmpty ? context.tr('Please enter a location') : null,
                    ),
                    const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                      initialValue: _selectedCategory,
                      decoration: InputDecoration(
                        labelText: context.tr('Category'),
                        border: OutlineInputBorder(),
                      ),
                      items: _categories.map((c) => DropdownMenuItem(
                        value: c, 
                        child: Text(context.tr(c.replaceAll('_', ' ')))
                      )).toList(),
                      onChanged: (val) => setState(() => _selectedCategory = val!),
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      initialValue: _selectedUrgency,
                      decoration: InputDecoration(
                        labelText: context.tr('Urgency'),
                        border: OutlineInputBorder(),
                      ),
                      items: _urgencies.map((u) => DropdownMenuItem(
                        value: u, 
                        child: Text(context.tr(u))
                      )).toList(),
                      onChanged: (val) => setState(() => _selectedUrgency = val!),
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _descriptionController,
                      maxLines: 4,
                      decoration: InputDecoration(
                        labelText: context.tr('Description'),
                        hintText: context.tr('Describe the issue in detail...'),
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) =>
                          value!.isEmpty ? context.tr('Please enter a description') : null,
                    ),
                    const SizedBox(height: 24),
                    
                    // Image Picker Section
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.grey.shade300),
                      ),
                      child: Column(
                        children: [
                          Icon(
                            _selectedImage == null
                                ? Icons.add_a_photo_outlined
                                : Icons.check_circle_outline,
                            size: 40,
                            color: _selectedImage == null ? Colors.grey : Colors.green,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _selectedImage == null
                                ? context.tr('No photo attached')
                                : '${context.tr('Photo selected:')} ${_selectedImage!.name}',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.grey.shade700),
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: _pickImage,
                            icon: const Icon(Icons.image),
                            label: Text(_selectedImage == null ? context.tr('Attach Photo') : context.tr('Change Photo')),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 32),
                    
                    // Submit Button
                    SizedBox(
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _submitReport,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0047BA),
                          foregroundColor: Colors.white,
                        ),
                        child: _isLoading
                            ? const CircularProgressIndicator(color: Colors.white)
                            : Text(context.tr('Submit Report'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
