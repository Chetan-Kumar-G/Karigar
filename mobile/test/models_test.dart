import 'package:artisan_market/core/json.dart';
import 'package:artisan_market/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('json helpers', () {
    test('asInt / asDouble / asBool are lenient', () {
      expect(asInt('42'), 42);
      expect(asInt(null, 7), 7);
      expect(asDouble('3.5'), 3.5);
      expect(asBool('true'), true);
      expect(asBool(1), true);
      expect(asMapList('not a list'), isEmpty);
    });
  });

  group('model parsing', () {
    test('ReadinessResult parses F1 output shape', () {
      final r = ReadinessResult.fromJson({
        'readiness_score': 58,
        'decision': 'auto_enhance',
        'component_scores': {
          'sharpness': 40,
          'exposure': 55,
          'framing': 80,
          'background_cleanliness': 45,
          'resolution': 90,
        },
        'confidence': 0.82,
        'before_after': {'before': {}, 'after': {}},
        '_meta': {'mode': 'REAL'},
      });
      expect(r.score, 58);
      expect(r.decision, 'auto_enhance');
      expect(r.components['sharpness'], 40);
      expect(r.beforeAfter, isNotNull);
      expect(r.meta['mode'], 'REAL');
    });

    test('CatalogResult parses F2 claim-consistency block', () {
      final c = CatalogResult.fromJson({
        'transcript_raw': 'cotton dupatta, block printed, Madhubani',
        'detected_language': 'hi',
        'extracted_attributes': {'material': 'cotton'},
        'grounding_check': {'material': 'confirmed_from_voice'},
        'visual_consistency_check': {},
        'claims': [
          {
            'claim': 'Made of cotton',
            'attribute': 'material',
            'status': 'UNKNOWN',
            'confidence': 0.2,
            'evidence': 'Cannot be established from a photo.',
            'checkable': true,
          },
          {
            'claim': 'Made entirely by hand by the artisan',
            'attribute': 'handmade',
            'status': 'UNKNOWN',
            'confidence': 0.0,
            'evidence': 'Needs artisan verification.',
            'checkable': false,
          },
        ],
        'verification_summary': {
          'headline': 'AI checks whether the artisan\'s claims are consistent '
              'with available visual evidence and trusted craft data.',
          'disclaimer': 'This is a consistency check, not proof.',
          'overall': 'insufficient_evidence',
        },
        'description_en': 'x',
        'description_hi': 'y',
        'seo_title': 't',
        'seo_keywords': ['a'],
        'hallucination_flags': [],
        'asr_confidence': 0.8,
        'asr_engine': 'typed-input',
      });
      expect(c.claims.length, 2);
      expect(c.claims.first['status'], 'UNKNOWN');
      expect(c.verificationSummary['headline'], startsWith('AI checks whether'));
    });

    test('PriceResult exposes floor invariant fields', () {
      final p = PriceResult.fromJson({
        'sustainable_floor_inr': 580,
        'recommended_price_inr': 649,
        'competitive_range_inr': [600, 780],
        'premium_opportunity_inr': 900,
        'floor_is_binding': false,
        'why_plain': 'Fair for this piece.',
        'explanation': {'top_positive_factors': ['Craft rarity']},
      });
      expect(p.floor, 580);
      expect(p.recommended, greaterThanOrEqualTo(p.floor));
      expect(p.range, [600, 780]);
    });

    test('OrderResult reads allocations + Shapley fields', () {
      final o = OrderResult.fromJson({
        'order_id': 'ORD-1',
        'status': 'fully_allocated',
        'total_quantity': 5000,
        'total_allocated': 5000,
        'fulfillment_pct': 100.0,
        'allocations': [
          {
            'artisan_id': 'A',
            'artisan_name': 'Asha',
            'allocated_units': 2000,
            'payment_share_inr': 460000,
            'proportional_share_inr': 440000,
            'shapley_marginal_inr': 12000,
          }
        ],
      });
      expect(o.totalAllocated, 5000);
      expect(o.allocations.single.units, 2000);
      expect(o.allocations.single.payment,
          isNot(equals(o.allocations.single.proportional)));
    });

    test('SearchResult keeps score breakdown', () {
      final s = SearchResult.fromJson({
        'session_id': 'S1',
        'query': 'cotton',
        'fairness_applied': true,
        'exposure_gap_metric': {'gap': 0.4},
        'results': [
          {
            'rank': 1,
            'listing_id': 'L1',
            'product_id': 'P1',
            'artisan_name': 'Meera',
            'craft': 'Madhubani',
            'region': 'Bihar',
            'price_inr': 649,
            'rating': 4.5,
            'score_breakdown': {
              'relevance': 0.9,
              'new_seller_boost': 1.0,
              'underserved_region_boost': 0.8,
              'exposure_penalty': 0.0,
              'final_score': 2.1,
            },
            'why': 'new artisan boost',
          }
        ],
      });
      expect(s.items.single.breakdown['final_score'], 2.1);
      expect(s.fairnessApplied, true);
    });
  });
}
