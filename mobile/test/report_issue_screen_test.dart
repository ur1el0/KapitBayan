import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/screens/report_issue_screen.dart';
import 'package:mobile/services/issue_service.dart';

class _FakeIssueService extends IssueService {
  _FakeIssueService() : super(apiClient: ApiClient());

  String? submittedTitle;
  XFile? submittedImage;

  @override
  Future<void> submitIssue({
    required String title,
    required String description,
    required String location,
    required String category,
    required String urgency,
    XFile? imageFile,
  }) async {
    submittedTitle = title;
    submittedImage = imageFile;
  }
}

void main() {
  testWidgets(
    'supports Take Photo (camera) and Choose Gallery plus optional emergency submit',
    (tester) async {
      final service = _FakeIssueService();
      ImageSource? requestedSource;

      await tester.pumpWidget(
        MaterialApp(
          home: ReportIssueScreen(
            issueService: service,
            onPickImage: (source) async {
              requestedSource = source;
              return XFile('/tmp/camera_snap.jpg', name: 'camera_snap.jpg');
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Take Photo'), findsOneWidget);
      expect(find.text('Choose Gallery'), findsOneWidget);

      await tester.ensureVisible(find.text('Take Photo'));
      await tester.tap(find.text('Take Photo'));
      await tester.pumpAndSettle();

      expect(requestedSource, ImageSource.camera);
      expect(find.text('Photo selected: camera_snap.jpg'), findsOneWidget);
      expect(find.text('Remove Photo'), findsOneWidget);

      await tester.ensureVisible(find.text('Remove Photo'));
      await tester.tap(find.text('Remove Photo'));
      await tester.pumpAndSettle();
      expect(find.text('Photo selected: camera_snap.jpg'), findsNothing);

      final textFields = find.byType(TextFormField);
      await tester.enterText(textFields.at(0), 'Downed Power Line');
      await tester.enterText(textFields.at(1), 'Purok 1');
      await tester.enterText(
        textFields.at(2),
        'Sparking wire near the corner post.',
      );

      await tester.drag(find.byType(SingleChildScrollView), const Offset(0, -300));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Submit Report'));
      await tester.pumpAndSettle();

      expect(service.submittedTitle, 'Downed Power Line');
      expect(service.submittedImage, isNull);
    },
  );
}
