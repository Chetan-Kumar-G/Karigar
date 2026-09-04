/// Defensive JSON accessors — the backend is trusted but parsing should never
/// throw and crash a screen.
library;

typedef J = Map<String, dynamic>;

J asMap(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

List<J> asMapList(dynamic v) =>
    v is List ? v.map((e) => asMap(e)).toList() : <J>[];

List<String> asStringList(dynamic v) =>
    v is List ? v.map((e) => '$e').toList() : <String>[];

String asStr(dynamic v, [String fallback = '']) => v == null ? fallback : '$v';

int asInt(dynamic v, [int fallback = 0]) {
  if (v is int) return v;
  if (v is num) return v.round();
  return int.tryParse('$v') ?? fallback;
}

double asDouble(dynamic v, [double fallback = 0]) {
  if (v is num) return v.toDouble();
  return double.tryParse('$v') ?? fallback;
}

bool asBool(dynamic v, [bool fallback = false]) {
  if (v is bool) return v;
  if (v is num) return v != 0;
  if (v is String) return v.toLowerCase() == 'true';
  return fallback;
}
