/// Buyer-facing issue categories (spec §6) — plain language, no jargon.
const List<({String value, String label, String icon})> kComplaintCategories = [
  (value: 'product_not_as_described', label: 'Product not as described', icon: '📦'),
  (value: 'fake_counterfeit', label: 'Fake / counterfeit claim', icon: '🚫'),
  (value: 'wrong_material', label: 'Wrong material', icon: '🧵'),
  (value: 'wrong_quantity', label: 'Wrong quantity', icon: '🔢'),
  (value: 'poor_quality', label: 'Poor quality', icon: '⭐'),
  (value: 'not_delivered', label: 'Order not delivered', icon: '🚚'),
  (value: 'repeated_cancellation', label: 'Repeated cancellation', icon: '↩️'),
  (value: 'misleading_gi_claim', label: 'Misleading certification / GI claim', icon: '🏷️'),
  (value: 'other', label: 'Something else', icon: '❓'),
];

String complaintLabel(String value) => kComplaintCategories
    .firstWhere((c) => c.value == value,
        orElse: () => (value: value, label: value.replaceAll('_', ' '), icon: '❓'))
    .label;
