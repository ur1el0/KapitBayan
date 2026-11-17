import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/screens/my_issues_screen.dart';
import 'package:mobile/services/issue_service.dart';

class _FakePagedIssueService extends IssueService {
  _FakePagedIssueService() : super(apiClient: ApiClient());

  final List<IssueReport> _all = List.generate(7, (idx) {
    final numLabel = idx + 1;
    final hour = 10 + idx;
    return IssueReport(
      id: numLabel,
      title: 'Issue #$numLabel',
      description: 'Description for issue #$numLabel',
      location: 'Purok $numLabel',
      status: numLabel >= 6 ? 'RESOLVED' : 'PENDING',
      category: numLabel.isEven ? 'INFRASTRUCTURE' : 'ENVIRONMENT',
      createdAt: '2026-11-17T${hour.toString().padLeft(2, '0')}:15:00Z',
    );
  });

  String? lastStatusFilter;
  String? lastSearch;

  @override
  Future<PaginatedIssueResult> getMyIssuesPage({
    int page = 1,
    int pageSize = 5,
    String? statusFilter,
    String? categoryFilter,
    String? search,
  }) async {
    lastStatusFilter = statusFilter;
    lastSearch = search;

    var filtered = _all.reversed.toList();
    if (statusFilter != null && statusFilter != 'ALL') {
      filtered = filtered
          .where((item) => item.status == statusFilter)
          .toList();
    }
    if (categoryFilter != null && categoryFilter != 'ALL') {
      filtered = filtered
          .where((item) => item.category == categoryFilter)
          .toList();
    }
    if (search != null && search.trim().isNotEmpty) {
      filtered = filtered
          .where((item) => item.title.contains(search.trim()))
          .toList();
    }

    final start = (page - 1) * pageSize;
    final items = filtered.sublist(
      start,
      (start + pageSize).clamp(0, filtered.length),
    );
    return PaginatedIssueResult(
      items: items,
      totalCount: filtered.length,
      page: page,
      pageSize: pageSize,
      hasNext: start + pageSize < filtered.length,
      hasPrevious: page > 1,
    );
  }
}

void main() {
  testWidgets('displays first 5 most recent reports, paginates, and filters', (
    tester,
  ) async {
    final service = _FakePagedIssueService();

    await tester.pumpWidget(
      MaterialApp(home: MyIssuesScreen(issueService: service)),
    );
    await tester.pumpAndSettle();

    // First 5 newest show up on page 1 (Issue #7 down to Issue #3)
    expect(find.text('Issue #7'), findsOneWidget);
    final verticalList = find.byType(Scrollable).last;
    await tester.scrollUntilVisible(
      find.text('Issue #3'),
      200,
      scrollable: verticalList,
    );
    expect(find.text('Issue #3'), findsOneWidget);
    expect(find.text('Issue #2'), findsNothing);

    // Navigate to Page 2
    await tester.scrollUntilVisible(
      find.text('Next'),
      200,
      scrollable: verticalList,
    );
    expect(find.text('Page 1 of 2 (7 total)'), findsOneWidget);
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    expect(find.text('Issue #2'), findsOneWidget);
    expect(find.text('Issue #1'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Page 2 of 2 (7 total)'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('Page 2 of 2 (7 total)'), findsOneWidget);

    // Filter by Resolved resets to page 1 and filters cleanly
    await tester.tap(find.widgetWithText(ChoiceChip, 'Resolved'));
    await tester.pumpAndSettle();

    expect(service.lastStatusFilter, 'RESOLVED');
    expect(find.text('Issue #7'), findsOneWidget);
    expect(find.text('Issue #6'), findsOneWidget);
    expect(find.text('Page 1 of 1 (2 total)'), findsOneWidget);
  });
}
