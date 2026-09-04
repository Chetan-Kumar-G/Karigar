@TestOn('browser')
library;

import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:flutter_test/flutter_test.dart';

/// Proves the bytes-based multipart path compiles AND runs in a browser
/// (no `dart:io`). Run with:  flutter test --platform chrome
void main() {
  test('MultipartFile.fromBytes works on web', () {
    final part = http.MultipartFile.fromBytes(
      'image',
      Uint8List.fromList([1, 2, 3, 4]),
      filename: 'photo.jpg',
    );
    expect(part.field, 'image');
    expect(part.length, 4);
    expect(part.filename, 'photo.jpg');
  });

  test('MultipartRequest accepts a bytes part and finalises on web', () async {
    final req = http.MultipartRequest('POST', Uri.parse('https://example.com/x'))
      ..fields['k'] = 'v'
      ..files.add(http.MultipartFile.fromBytes(
          'voice_note', Uint8List.fromList(List.filled(64, 7)),
          filename: 'voice.m4a'));
    final bytes = await req.finalize().toBytes();
    expect(bytes.length, greaterThan(64));
  });
}
