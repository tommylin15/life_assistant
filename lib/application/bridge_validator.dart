import 'dart:convert';

const supportedBridgeActions = {
  'create_task',
  'update_task',
  'complete_task',
  'create_calendar_event',
  'update_calendar_event',
  'delete_calendar_event',
  'create_note',
  'update_note',
  'add_shopping_item',
  'create_project',
};

class BridgeActionReview {
  const BridgeActionReview({
    required this.actionId,
    required this.type,
    required this.payload,
    required this.valid,
    this.error,
  });
  final String actionId;
  final String type;
  final Map<String, Object?> payload;
  final bool valid;
  final String? error;
}

class BridgeReview {
  const BridgeReview({required this.requestId, required this.actions});
  final String requestId;
  final List<BridgeActionReview> actions;
}

class BridgeValidator {
  const BridgeValidator({required this.bridgeId});
  final String bridgeId;

  BridgeReview validate(String source) {
    final decoded = jsonDecode(source);
    if (decoded is! Map<String, dynamic>)
      throw const FormatException('INVALID_JSON');
    if (decoded['bridge_id'] != bridgeId)
      throw const FormatException('BRIDGE_ID_MISMATCH');
    final version = decoded['schema_version'];
    if (version is! String || version.split('.').first != '1')
      throw const FormatException('SCHEMA_MISMATCH');
    if (decoded['source'] != 'chatgpt')
      throw const FormatException('INVALID_SOURCE');
    final requestId = decoded['request_id'];
    if (requestId is! String || requestId.isEmpty)
      throw const FormatException('INVALID_REQUEST_ID');
    final rawActions = decoded['actions'];
    if (rawActions is! List) throw const FormatException('INVALID_ACTIONS');
    final seen = <String>{};
    final actions = rawActions.map((raw) {
      if (raw is! Map<String, dynamic>)
        return const BridgeActionReview(
          actionId: '',
          type: '',
          payload: {},
          valid: false,
          error: 'INVALID_ACTION',
        );
      final id = raw['action_id'];
      final type = raw['type'];
      final payload = raw['payload'];
      String? error;
      if (id is! String || id.isEmpty)
        error = 'INVALID_ACTION_ID';
      else if (!seen.add(id))
        error = 'DUPLICATE_ACTION_ID';
      else if (type is! String || !supportedBridgeActions.contains(type))
        error = 'UNKNOWN_ACTION';
      else if (raw['requires_confirmation'] != true)
        error = 'CONFIRMATION_REQUIRED';
      else if (payload is! Map<String, dynamic>)
        error = 'INVALID_PAYLOAD';
      else if (!_requiredPayload(type, payload))
        error = 'INVALID_PAYLOAD';
      return BridgeActionReview(
        actionId: id is String ? id : '',
        type: type is String ? type : '',
        payload: payload is Map<String, dynamic> ? payload : const {},
        valid: error == null,
        error: error,
      );
    }).toList();
    return BridgeReview(requestId: requestId, actions: actions);
  }

  bool _requiredPayload(String type, Map<String, dynamic> payload) =>
      switch (type) {
        'create_task' => payload['title'] is String,
        'update_task' || 'complete_task' => payload['task_id'] is String,
        'create_calendar_event' =>
          payload['title'] is String &&
              _date(payload['starts_at']) &&
              _date(payload['ends_at']),
        'update_calendar_event' ||
        'delete_calendar_event' => payload['google_event_id'] is String,
        'create_note' => payload['body_markdown'] is String,
        'update_note' => payload['note_id'] is String,
        'add_shopping_item' =>
          payload['list_id'] is String && payload['name'] is String,
        'create_project' => payload['name'] is String,
        _ => false,
      };

  bool _date(Object? value) =>
      value is String &&
      DateTime.tryParse(value) != null &&
      RegExp(r'(Z|[+-]\d\d:\d\d)$').hasMatch(value);
}
