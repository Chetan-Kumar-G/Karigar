import '../core/json.dart';

// ── identity ──────────────────────────────────────────────────────────────
class Session {
  Session({required this.token, required this.role, required this.profile});
  final String token;
  final String role; // artisan | buyer
  final J profile;

  String get id => asStr(profile['artisan_id'] ?? profile['buyer_id']);
  String get name => asStr(profile['name'], 'Guest');
  String? get region => profile['region'] as String?;
  String? get state => profile['state'] as String?;
  int get capacity => asInt(profile['monthly_capacity_units'], 400);
  bool get isArtisan => role == 'artisan';

  factory Session.fromJson(J j) => Session(
        token: asStr(j['access_token'] ?? j['token']),
        role: asStr(j['role'], 'artisan'),
        profile: asMap(j['profile'] ?? j),
      );
}

// ── reference lookups ────────────────────────────────────────────────────
class RefItem {
  RefItem(this.id, this.name, {this.extra = const {}});
  final String id;
  final String name;
  final J extra;
  factory RefItem.fromJson(J j) =>
      RefItem(asStr(j['id']), asStr(j['name']), extra: j);
}

class ReferenceData {
  ReferenceData({
    required this.regions,
    required this.crafts,
    required this.techniques,
    required this.materials,
  });
  final List<RefItem> regions;
  final List<RefItem> crafts;
  final List<RefItem> techniques;
  final List<RefItem> materials;

  factory ReferenceData.fromJson(J j) => ReferenceData(
        regions: asMapList(j['regions']).map(RefItem.fromJson).toList(),
        crafts: asMapList(j['crafts']).map(RefItem.fromJson).toList(),
        techniques: asMapList(j['techniques']).map(RefItem.fromJson).toList(),
        materials: asMapList(j['materials']).map(RefItem.fromJson).toList(),
      );
}

// ── product ─────────────────────────────────────────────────────────────
class ProductImageInfo {
  ProductImageInfo({
    required this.imageId,
    required this.url,
    this.enhancedUrl,
    this.maskUrl,
    this.readinessScore,
    this.componentScores = const {},
    this.decision,
  });
  final String imageId;
  final String url;
  final String? enhancedUrl;
  final String? maskUrl;
  final int? readinessScore;
  final J componentScores;
  final String? decision;

  factory ProductImageInfo.fromJson(J j) => ProductImageInfo(
        imageId: asStr(j['image_id']),
        url: asStr(j['url']),
        enhancedUrl: j['enhanced_url'] as String?,
        maskUrl: j['mask_url'] as String?,
        readinessScore: j['readiness_score'] == null
            ? null
            : asInt(j['readiness_score']),
        componentScores: asMap(j['component_scores']),
        decision: j['decision'] as String?,
      );
}

class Product {
  Product({
    required this.id,
    required this.title,
    required this.status,
    this.category,
    this.craftId,
    this.craftName,
    this.descriptionEn,
    this.descriptionHi,
    this.seoTitle,
    this.seoKeywords = const [],
    this.primaryImage,
    this.images = const [],
    this.listing,
    this.passportId,
    this.artisanId,
    this.artisanName,
    this.isDemo = false,
  });

  final String id;
  final String title;
  final String status;
  final String? category;
  final String? craftId;
  final String? craftName;
  final String? descriptionEn;
  final String? descriptionHi;
  final String? seoTitle;
  final List<String> seoKeywords;
  final String? primaryImage;
  final List<ProductImageInfo> images;
  final J? listing;
  final String? passportId;
  final String? artisanId;
  final String? artisanName;
  final bool isDemo;

  double? get price => listing == null ? null : asDouble(listing!['price_inr']);
  double? get floor =>
      listing == null ? null : asDouble(listing!['sustainable_floor_inr']);

  factory Product.fromJson(J j) => Product(
        id: asStr(j['product_id']),
        title: asStr(j['title'], 'Untitled product'),
        status: asStr(j['status'], 'draft'),
        category: j['category'] as String?,
        craftId: j['craft_id'] as String?,
        craftName: j['craft_name'] as String?,
        descriptionEn: j['description_en'] as String?,
        descriptionHi: j['description_hi'] as String?,
        seoTitle: j['seo_title'] as String?,
        seoKeywords: asStringList(j['seo_keywords']),
        primaryImage: j['primary_image'] as String?,
        images: asMapList(j['images']).map(ProductImageInfo.fromJson).toList(),
        listing: j['listing'] == null ? null : asMap(j['listing']),
        passportId: j['passport_id'] as String?,
        artisanId: j['artisan_id'] as String?,
        artisanName: j['artisan_name'] as String?,
        isDemo: asBool(j['is_demo']),
      );
}

// ── F1 ──────────────────────────────────────────────────────────────────
class ReadinessResult {
  ReadinessResult({
    required this.score,
    required this.decision,
    required this.components,
    required this.confidence,
    this.originalUrl,
    this.enhancedUrl,
    this.maskUrl,
    this.failureReason,
    this.retakeGuidance,
    this.beforeAfter,
    this.enhancementGate = const {},
    this.meta = const {},
  });

  final int score;
  final String decision; // accept | auto_enhance | retake
  final Map<String, int> components;
  final double confidence;
  final String? originalUrl;
  final String? enhancedUrl;
  final String? maskUrl;
  final String? failureReason;
  final J? retakeGuidance;
  final J? beforeAfter;
  final J enhancementGate; // Phase 4 safety gate: verdict, reasons, colour ΔE …
  final J meta;

  String get gateVerdict => asStr(enhancementGate['verdict'], '');
  List<String> get gateReasons =>
      asStringList(enhancementGate['reasons']);

  factory ReadinessResult.fromJson(J j) => ReadinessResult(
        score: asInt(j['readiness_score']),
        decision: asStr(j['decision'], 'retake'),
        components: asMap(j['component_scores'])
            .map((k, v) => MapEntry(k, asInt(v))),
        confidence: asDouble(j['confidence'], 0.7),
        originalUrl: j['original_url'] as String?,
        enhancedUrl: j['enhanced_url'] as String?,
        maskUrl: j['mask_url'] as String?,
        failureReason: j['failure_reason'] as String?,
        retakeGuidance: j['retake_guidance'] == null ? null : asMap(j['retake_guidance']),
        beforeAfter: j['before_after'] == null ? null : asMap(j['before_after']),
        enhancementGate: asMap(j['enhancement_gate']),
        meta: asMap(j['_meta']),
      );
}

// ── F2 ──────────────────────────────────────────────────────────────────
class CatalogResult {
  CatalogResult({
    required this.transcript,
    required this.language,
    required this.attributes,
    required this.grounding,
    required this.visual,
    required this.claims,
    required this.verificationSummary,
    required this.descriptionEn,
    required this.descriptionHi,
    required this.seoTitle,
    required this.seoKeywords,
    required this.flags,
    required this.asrConfidence,
    required this.asrEngine,
    this.asrMode = 'REAL',
    this.asrIsDemoFallback = false,
    this.meta = const {},
  });

  final String transcript;
  final String language;
  final J attributes;
  final Map<String, String> grounding;
  final J visual;

  /// F2 claim-consistency: each = {claim, attribute, status, confidence,
  /// evidence, checkable}. status ∈ SUPPORTED | VISUALLY_CONSISTENT |
  /// CONTRADICTED | UNKNOWN | NEEDS_HUMAN_REVIEW.
  final List<J> claims;
  final J verificationSummary; // {headline, disclaimer, counts, overall}

  final String descriptionEn;
  final String descriptionHi;
  final String seoTitle;
  final List<String> seoKeywords;
  final List<String> flags;
  final double asrConfidence;
  final String asrEngine;
  final String asrMode; // REAL | FALLBACK
  final bool asrIsDemoFallback; // true → transcript is NOT the user's speech
  final J meta;

  factory CatalogResult.fromJson(J j) => CatalogResult(
        transcript: asStr(j['transcript_raw']),
        language: asStr(j['detected_language'], 'hi'),
        attributes: asMap(j['extracted_attributes']),
        grounding: asMap(j['grounding_check'])
            .map((k, v) => MapEntry(k, '$v')),
        visual: asMap(j['visual_consistency_check']),
        claims: asMapList(j['claims']),
        verificationSummary: asMap(j['verification_summary']),
        descriptionEn: asStr(j['description_en']),
        descriptionHi: asStr(j['description_hi']),
        seoTitle: asStr(j['seo_title']),
        seoKeywords: asStringList(j['seo_keywords']),
        flags: asStringList(j['hallucination_flags']),
        asrConfidence: asDouble(j['asr_confidence'], 0.8),
        asrEngine: asStr(j['asr_engine'], 'demo'),
        asrMode: asStr(j['asr_mode'], 'REAL'),
        asrIsDemoFallback: asBool(j['asr_is_demo_fallback']),
        meta: asMap(j['_meta']),
      );
}

// ── F3 ──────────────────────────────────────────────────────────────────
class Passport {
  Passport(this.raw);
  final J raw;

  String get productTitle => asStr(raw['product_title']);
  String get craftName => asStr(asMap(raw['craft'])['name'], '—');
  String get techniqueName => asStr(asMap(raw['technique'])['name'], '—');
  List<String> get materials =>
      asMapList(raw['materials']).map((m) => asStr(m['name'])).toList();
  String get regionName {
    final r = asMap(raw['region']);
    return r.isEmpty ? '—' : '${r['name']}, ${r['state']}';
  }

  String get giStatus => asStr(raw['gi_status'], 'unregistered');
  String? get odopCluster => raw['odop_cluster'] as String?;
  double get confidence => asDouble(raw['provenance_confidence']);
  J get breakdown => asMap(raw['confidence_breakdown']);
  String get visualStatus => asStr(raw['visual_authenticity_status'], 'neutral');
  String get storyEn => asStr(raw['story_snippet_en']);
  String get storyHi => asStr(raw['story_snippet_hi']);
  String? get heritageNote => raw['heritage_note'] as String?;
  List<J> get relatedCrafts => asMapList(raw['related_crafts']);
  List<J> get certifications => asMapList(raw['certifications']);
  String get artisanName => asStr(asMap(raw['artisan'])['name']);

  factory Passport.fromJson(J j) => Passport(j);
}

// ── F4 ──────────────────────────────────────────────────────────────────
class PriceResult {
  PriceResult(this.raw);
  final J raw;

  int get floor => asInt(raw['sustainable_floor_inr']);
  int get recommended => asInt(raw['recommended_price_inr']);
  int get premium => asInt(raw['premium_opportunity_inr']);
  List<int> get range => asStringList(raw['competitive_range_inr'])
      .map((e) => int.tryParse(e) ?? 0)
      .toList();
  bool get floorBinding => asBool(raw['floor_is_binding']);
  double get confidence => asDouble(raw['confidence'], 0.7);
  String get whyPlain => asStr(raw['why_plain']);
  J get explanation => asMap(raw['explanation']);
  J get costBreakdown => asMap(raw['cost_breakdown']);
  List<J> get pricingPipeline => asMapList(raw['pricing_pipeline']);
  String get trainingDataNote => asStr(raw['training_data_note']);
  int get rawModelPrice => asInt(raw['raw_model_price_inr']);
  int get marketMedianUsed => asInt(raw['market_median_used_inr']);
  bool get modelClippedHigh => asBool(raw['model_clipped_to_market_cap']);
  J get meta => asMap(raw['_meta']);

  factory PriceResult.fromJson(J j) => PriceResult(j);
}

// ── F5 ──────────────────────────────────────────────────────────────────
class DemandResult {
  DemandResult(this.raw);
  final J raw;

  String get category => asStr(raw['category']);
  int get windowDays => asInt(raw['forecast_window_days'], 30);
  int get predicted => asInt(raw['predicted_demand_units']);
  double get trendPct => asDouble(raw['trend_pct']);
  List<int> get ci => (raw['confidence_interval'] as List? ?? [])
      .map((e) => asInt(e))
      .toList();
  double get seasonalIndex => asDouble(raw['seasonal_index'], 1);
  bool get isSimulated => asBool(raw['is_simulated'], true);
  String get simulatedNote => asStr(raw['simulated_note']);
  J get action => asMap(raw['action_recommendation']);
  List<double> get curveP50 => (asMap(raw['daily_curve'])['p50'] as List? ?? [])
      .map((e) => asDouble(e))
      .toList();
  List<double> get curveP10 => (asMap(raw['daily_curve'])['p10'] as List? ?? [])
      .map((e) => asDouble(e))
      .toList();
  List<double> get curveP90 => (asMap(raw['daily_curve'])['p90'] as List? ?? [])
      .map((e) => asDouble(e))
      .toList();
  J get meta => asMap(raw['_meta']);

  factory DemandResult.fromJson(J j) => DemandResult(j);
}

// ── F6 ──────────────────────────────────────────────────────────────────
class Requirement {
  Requirement(this.raw);
  final J raw;
  String get id => asStr(raw['requirement_id']);
  String get title => asStr(raw['title']);
  String get buyerName => asStr(raw['buyer_name']);
  String get buyerType => asStr(raw['buyer_type'], 'B2B');
  String? get craftName => raw['craft_name'] as String?;
  int get quantity => asInt(raw['quantity']);
  double get priceMin => asDouble(raw['price_min']);
  double get priceMax => asDouble(raw['price_max']);
  int? get daysLeft => raw['days_left'] == null ? null : asInt(raw['days_left']);
  String get status => asStr(raw['status'], 'open');
  String get notes => asStr(raw['notes']);
  bool get isDemo => asBool(raw['is_demo']);
  factory Requirement.fromJson(J j) => Requirement(j);
}

class Allocation {
  Allocation(this.raw);
  final J raw;
  String get id => asStr(raw['allocation_id']);
  String get artisanId => asStr(raw['artisan_id']);
  String get artisanName => asStr(raw['artisan_name'], asStr(raw['artisan_id']));
  int get units => asInt(raw['allocated_units']);
  int get payment => asInt(raw['payment_share_inr']);
  int get proportional => asInt(raw['proportional_share_inr']);
  int get shapleyMarginal => asInt(raw['shapley_marginal_inr']);
  double get quality => asDouble(raw['quality_score']);
  double get reliability => asDouble(raw['reliability_score']);
  int get capacity => asInt(raw['capacity_units']);
  J get matchReasons => asMap(raw['match_reasons']);
  String get allocationRationale => asStr(raw['allocation_rationale']);
  String get paymentRationale => asStr(raw['payment_rationale']);
  String get status => asStr(raw['status'], 'proposed');
  bool get verified => asBool(raw['verified']);
  String get verificationStatus =>
      asStr(raw['verification_status'], 'PENDING');
  double? get reliabilityPct =>
      raw['reliability_pct'] == null ? null : asDouble(raw['reliability_pct']);
  factory Allocation.fromJson(J j) => Allocation(j);
}

class OrderResult {
  OrderResult(this.raw);
  final J raw;
  String get id => asStr(raw['order_id']);
  String get status => asStr(raw['status']);
  int get totalQuantity => asInt(raw['total_quantity']);
  int get totalAllocated => asInt(raw['total_allocated']);
  double get fulfillmentPct => asDouble(raw['fulfillment_pct']);
  int get totalCost => asInt(raw['total_cost_inr']);
  int get totalBuyerPayment => asInt(raw['total_buyer_payment_inr']);
  double? get objectiveValue =>
      raw['objective_value'] == null ? null : asDouble(raw['objective_value']);
  double? get solveTimeMs =>
      raw['solve_time_ms'] == null ? null : asDouble(raw['solve_time_ms']);
  String get solver => asStr(raw['solver'], 'cp_sat');
  J get optimizationMeta => asMap(raw['optimization_meta']);
  J get rawResult => asMap(raw['raw_result']);
  List<Allocation> get allocations {
    final list = raw['allocations'] as List? ??
        (asMap(raw['raw_result'])['allocations'] as List? ?? []);
    return list.map((e) => Allocation(asMap(e))).toList();
  }

  factory OrderResult.fromJson(J j) => OrderResult(j);
}

// ── F7 ──────────────────────────────────────────────────────────────────
class SearchItem {
  SearchItem(this.raw);
  final J raw;
  int get rank => asInt(raw['rank']);
  String get listingId => asStr(raw['listing_id']);
  String get productId => asStr(raw['product_id']);
  String get artisanName => asStr(raw['artisan_name']);
  String get craft => asStr(raw['craft']);
  String get region => asStr(raw['region']);
  int get price => asInt(raw['price_inr']);
  double get rating => asDouble(raw['rating']);
  String? get thumbnail => raw['thumbnail_url'] as String?;
  J get breakdown => asMap(raw['score_breakdown']);
  String get why => asStr(raw['why']);
  factory SearchItem.fromJson(J j) => SearchItem(j);
}

class SearchResult {
  SearchResult({
    required this.sessionId,
    required this.query,
    required this.items,
    required this.weights,
    required this.fairnessApplied,
    required this.exposureGap,
  });
  final String sessionId;
  final String query;
  final List<SearchItem> items;
  final J weights;
  final bool fairnessApplied;
  final J exposureGap;

  factory SearchResult.fromJson(J j) => SearchResult(
        sessionId: asStr(j['session_id']),
        query: asStr(j['query']),
        items: asMapList(j['results']).map(SearchItem.fromJson).toList(),
        weights: asMap(j['weights']),
        fairnessApplied: asBool(j['fairness_applied'], true),
        exposureGap: asMap(j['exposure_gap_metric']),
      );
}

// ── Copilot / dashboard ────────────────────────────────────────────────
class CopilotCard {
  CopilotCard(this.raw);
  final J raw;
  String get type => asStr(raw['type'], 'opportunity');
  String get colour => asStr(raw['colour'], 'blue');
  String get feature => asStr(raw['feature']);
  String get title => asStr(raw['title']);
  String get observation => asStr(raw['observation']);
  String get action => asStr(raw['action']);
  List<String> get signals => asStringList(raw['supporting_signals']);
  double get confidence => asDouble(raw['confidence'], 0.7);
  String? get productId => raw['product_id'] as String?;
  String? get requirementId => raw['requirement_id'] as String?;
  factory CopilotCard.fromJson(J j) => CopilotCard(j);
}

class Dashboard {
  Dashboard(this.raw);
  final J raw;
  String get greeting => asStr(raw['greeting'], 'Hello');
  String get artisanName => asStr(raw['artisan_name']);
  J get summary => asMap(raw['summary']);
  List<CopilotCard> get attention =>
      asMapList(raw['attention']).map(CopilotCard.fromJson).toList();
  factory Dashboard.fromJson(J j) => Dashboard(j);
}

// ── Trust & Verification ──────────────────────────────────────────────
class TrustBadge {
  TrustBadge(this.raw);
  final J raw;
  String get key => asStr(raw['key']);
  String get label => asStr(raw['label']);
  String get tone => asStr(raw['tone'], 'blue'); // green | blue | amber | red
  factory TrustBadge.fromJson(J j) => TrustBadge(j);
}

/// Public "Verified Artisan / Verified Business" card projection.
class VerifiedCard {
  VerifiedCard(this.raw);
  final J raw;

  String get subjectType => asStr(raw['subject_type'], 'artisan');
  bool get isBusiness => subjectType == 'business';
  String get subjectId =>
      asStr(raw['artisan_id'] ?? raw['buyer_id'] ?? raw['subject_id']);
  String get name => asStr(raw['name']);
  String get status => asStr(raw['verification_status'], 'PENDING');
  List<TrustBadge> get badges =>
      asMapList(raw['badges']).map(TrustBadge.fromJson).toList();

  String? get region => raw['region'] as String?;
  String? get state => raw['state'] as String?;
  String? get craft => raw['craft'] as String?;
  String? get bio => raw['bio'] as String?;
  String get giStatus => asStr(raw['gi_status'], 'not_registered');
  int get completedOrders => asInt(raw['completed_orders']);
  double get onTimePct => asDouble(raw['on_time_pct']);
  double get reliabilityScore => asDouble(raw['reliability_score']);
  J get reliabilityBreakdown => asMap(raw['reliability_breakdown']);
  int get productsListed => asInt(raw['products_listed']);
  String? get joinedDate => raw['joined_date'] as String?;
  bool get b2bEligible => asBool(raw['b2b_eligible']);
  int get openComplaints => asInt(raw['open_complaints']);
  bool get isDemo => asBool(raw['is_demo']);
  String? get passportProductId => raw['passport_product_id'] as String?;
  String get disclaimer => asStr(raw['disclaimer']);

  // business-only
  String get businessType => asStr(raw['type'], 'B2B');
  int get orderHistoryCount => asInt(raw['order_history_count']);
  int get ordersCompleted => asInt(raw['orders_completed']);

  factory VerifiedCard.fromJson(J j) => VerifiedCard(j);
}

/// Owner / reviewer view of a verification profile.
class VerificationProfileM {
  VerificationProfileM(this.raw);
  final J raw;
  String get profileId => asStr(raw['profile_id']);
  String get subjectId => asStr(raw['subject_id']);
  String get subjectType => asStr(raw['subject_type'], 'artisan');
  String get name => asStr(raw['name']);
  String get status => asStr(raw['verification_status'], 'PENDING');
  List<TrustBadge> get badges =>
      asMapList(raw['badges']).map(TrustBadge.fromJson).toList();
  bool get identityVerified => asBool(raw['identity_verified']);
  bool get craftVerified => asBool(raw['craft_verified']);
  bool get productVerified => asBool(raw['product_verified']);
  bool get businessVerified => asBool(raw['business_verified']);
  bool get contactVerified => asBool(raw['contact_verified']);
  String get giStatus => asStr(raw['gi_status'], 'not_registered');
  double get reliabilityScore => asDouble(raw['reliability_score']);
  J get reliabilityBreakdown => asMap(raw['reliability_breakdown']);
  String? get suspensionReason => raw['suspension_reason'] as String?;
  String? get verificationDate => raw['verification_date'] as String?;
  List<J> get evidence => asMapList(raw['evidence']);
  List<J> get reviews => asMapList(raw['reviews']);
  J get reviewerView => asMap(raw['reviewer_view']);
  List<J> get complaints => asMapList(raw['complaints']);
  List<J> get timeline => asMapList(raw['timeline']);
  factory VerificationProfileM.fromJson(J j) => VerificationProfileM(j);
}

class ReviewerQueueItem {
  ReviewerQueueItem(this.raw);
  final J raw;
  String get profileId => asStr(raw['profile_id']);
  String get subjectId => asStr(raw['subject_id']);
  String get subjectType => asStr(raw['subject_type'], 'artisan');
  String get name => asStr(raw['name']);
  String get status => asStr(raw['verification_status'], 'PENDING');
  String get giStatus => asStr(raw['gi_status'], 'not_registered');
  double get reliabilityScore => asDouble(raw['reliability_score']);
  bool get openComplaints => asBool(raw['open_complaints']);
  bool get needsAttention => asBool(raw['needs_attention']);
  bool get isDemo => asBool(raw['is_demo']);
  factory ReviewerQueueItem.fromJson(J j) => ReviewerQueueItem(j);
}

class ComplaintM {
  ComplaintM(this.raw);
  final J raw;
  String get id => asStr(raw['complaint_id']);
  String get reportedBy => asStr(raw['reported_by']);
  String get artisanId => asStr(raw['artisan_id']);
  String get artisanName => asStr(raw['artisan_name']);
  String? get orderId => raw['order_id'] as String?;
  String get category => asStr(raw['category']);
  String get severity => asStr(raw['severity'], 'medium');
  String get status => asStr(raw['status'], 'open');
  String get description => asStr(raw['description']);
  String? get resolution => raw['resolution'] as String?;
  String? get riskFlag => raw['risk_flag'] as String?;
  String get createdAt => asStr(raw['created_at']);
  factory ComplaintM.fromJson(J j) => ComplaintM(j);
}

class OrderCommitment {
  OrderCommitment(this.raw);
  final J raw;
  String get orderId => asStr(raw['order_id']);
  String get status => asStr(raw['commitment_status'], 'DRAFT');
  List<String> get flow => asStringList(raw['commitment_flow']);
  String get deliveryStatus => asStr(raw['delivery_status'], 'not_started');
  List<J> get milestones => asMapList(raw['payment_milestones']);
  int get paidInr => asInt(raw['paid_inr']);
  int get totalBuyerPaymentInr => asInt(raw['total_buyer_payment_inr']);
  String? get cancellationStage => raw['cancellation_stage'] as String?;
  int get artisanCommittedCostInr => asInt(raw['artisan_committed_cost_inr']);
  int get advanceRetainedInr => asInt(raw['advance_retained_inr']);
  String? get trackingNote => raw['tracking_note'] as String?;
  String? get consequence => raw['consequence'] as String?;
  bool get isSimulated => asBool(raw['is_simulated'], true);
  String get disclaimer => asStr(raw['disclaimer']);
  factory OrderCommitment.fromJson(J j) => OrderCommitment(j);
}

// ── judge screen ──────────────────────────────────────────────────────
class AiRun {
  AiRun(this.raw);
  final J raw;
  String get feature => asStr(raw['feature']);
  String get model => asStr(raw['model']);
  String get mode => asStr(raw['mode']);
  String get subjectId => asStr(raw['subject_id']);
  double get latencyMs => asDouble(raw['latency_ms']);
  J get output => asMap(raw['output']);
  List<String> get inputs => asStringList(raw['inputs'] is List
      ? raw['inputs']
      : asMap(raw['inputs']).keys.toList());
  String get createdAt => asStr(raw['created_at']);
  factory AiRun.fromJson(J j) => AiRun(j);
}
