import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Regression guard for a bug that shipped across ~15 screens:
///
///   setState(() => _future = api.something());
///
/// An arrow closure `() => _x = expr` *returns* the value of `expr`. When that
/// value is a `Future`, `State.setState` hits its debug assertion
/// "setState() callback argument returned a Future." and paints the red error
/// screen at runtime — but `flutter analyze` stays green, so nothing caught it.
///
/// The fix is always the same: use a block body so the closure returns void:
///
///   setState(() { _future = api.something(); });
///
/// This test fails if the arrow form creeps back in.
void main() {
  test('no setState(() => ... = ...) arrow closures that can return a Future',
      () {
    final libDir = Directory('lib');
    expect(libDir.existsSync(), isTrue, reason: 'run from the mobile/ package');

    // Arrow-body setState whose assignment can evaluate to a Future:
    //  - the target is a `_future` field, or
    //  - the right-hand side calls an API (`.api.`), a `_load*()` helper, or
    //    builds a `Future.` directly.
    final arrowAssign = RegExp(r'setState\(\s*\(\)\s*=>\s*([\w.]+)\s*=\s*(.*)');
    final futureRhs = RegExp(r'\.api\.|_load\w*\(|Future\.');

    final hits = <String>[];
    for (final entity in libDir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final lines = entity.readAsLinesSync();
      for (var i = 0; i < lines.length; i++) {
        final m = arrowAssign.firstMatch(lines[i]);
        if (m == null) continue;
        final target = m.group(1)!;
        final rhs = m.group(2)!;
        if (target.endsWith('_future') || futureRhs.hasMatch(rhs)) {
          hits.add('${entity.path}:${i + 1}  ${lines[i].trim()}');
        }
      }
    }

    expect(
      hits,
      isEmpty,
      reason: 'Use a block body — setState(() { x = ...; }) — so the closure '
          'returns void:\n${hits.join('\n')}',
    );
  });
}
