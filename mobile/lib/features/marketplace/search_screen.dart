import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/json.dart';
import '../../core/theme.dart';
import '../../l10n/i18n.dart';
import '../../models/models.dart';
import '../../providers/app_state.dart';
import '../../widgets/common.dart';

/// F7 — Fair Market Discovery (spec §16, §32).
class SearchScreen extends StatefulWidget {
  const SearchScreen({this.standalone = false, super.key});
  final bool standalone;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _q = TextEditingController(text: 'handwoven cotton dupatta');
  bool _fairness = true;
  bool _loading = false;
  String? _error;
  SearchResult? _result;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _run());
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Future<void> _run() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await context.read<AppState>().api.search(
            _q.text.trim(),
            fairness: _fairness,
            sessionId: _result?.sessionId,
          );
      setState(() => _result = res);
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final body = Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Column(
            children: [
              TextField(
                controller: _q,
                textInputAction: TextInputAction.search,
                onSubmitted: (_) => _run(),
                decoration: InputDecoration(
                  hintText: 'Search crafts, materials, regions…',
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.arrow_forward_rounded),
                    onPressed: _run,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  FilterChip(
                    label: const Text('Fair ranking'),
                    selected: _fairness,
                    onSelected: (v) {
                      setState(() => _fairness = v);
                      _run();
                    },
                  ),
                  const Spacer(),
                  if (_result != null)
                    TextButton.icon(
                      onPressed: () => _showCompare(context, _q.text.trim()),
                      icon: const Icon(Icons.compare_arrows_rounded, size: 18),
                      label: const Text('Compare'),
                    ),
                ],
              ),
            ],
          ),
        ),
        Expanded(child: _resultsArea()),
      ],
    );

    if (!widget.standalone) {
      return Scaffold(appBar: AppBar(title: Text(tr('Market'))), body: body);
    }
    return Scaffold(
      appBar: AppBar(title: Text(tr('Browse market'))),
      body: body,
    );
  }

  Widget _resultsArea() {
    if (_loading && _result == null) {
      return const LoadingView(label: 'Searching…');
    }
    if (_error != null && _result == null) {
      return ErrorView(_error!, onRetry: _run);
    }
    final r = _result;
    if (r == null || r.items.isEmpty) {
      return EmptyView(
          icon: Icons.search_off_rounded,
          title: tr('No results'),
          message: 'Try a broader search term.');
    }
    return RefreshIndicator(
      onRefresh: _run,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
        children: [
          _ExposureGapBanner(gap: r.exposureGap, fairness: r.fairnessApplied),
          const SizedBox(height: 10),
          for (final item in r.items)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _ResultCard(
                item: item,
                onTap: () {
                  context
                      .read<AppState>()
                      .api
                      .recordClick(item.listingId, r.sessionId);
                  context.push('/product/${item.productId}');
                },
              ),
            ),
        ],
      ),
    );
  }

  void _showCompare(BuildContext context, String q) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _CompareSheet(query: q),
    );
  }
}

class _ExposureGapBanner extends StatelessWidget {
  const _ExposureGapBanner({required this.gap, required this.fairness});
  final J gap;
  final bool fairness;

  @override
  Widget build(BuildContext context) {
    final g = gap['gap'];
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: fairness ? AppTheme.leafBg : AppTheme.amberBg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(fairness ? Icons.balance_rounded : Icons.trending_up_rounded,
              color: fairness ? AppTheme.leaf : AppTheme.ochre, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              fairness
                  ? 'Fair ranking on — new & underserved-region artisans get an '
                      'exposure boost. Exposure gap: ${g ?? '—'}'
                  : 'Fair ranking off — pure relevance. Exposure gap: ${g ?? '—'}',
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.item, required this.onTap});
  final SearchItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final b = item.breakdown;
    final boost = asDouble(b['new_seller_boost']);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Stack(
                    children: [
                      RemoteImage(item.thumbnail, width: 82, height: 82),
                      Positioned(
                        left: 4,
                        top: 4,
                        child: CircleAvatar(
                          radius: 11,
                          backgroundColor: AppTheme.ink.withValues(alpha: 0.75),
                          child: Text('${item.rank}',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(item.craft,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontWeight: FontWeight.w800)),
                        const SizedBox(height: 2),
                        Text('${item.artisanName} · ${item.region}',
                            style: Theme.of(context).textTheme.bodySmall),
                        const SizedBox(height: 6),
                        Row(children: [
                          Text('₹${item.price}',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                  color: AppTheme.terracotta)),
                          const SizedBox(width: 10),
                          const Icon(Icons.star_rounded,
                              size: 15, color: AppTheme.ochre),
                          Text(' ${item.rating}',
                              style: Theme.of(context).textTheme.bodySmall),
                        ]),
                      ],
                    ),
                  ),
                ],
              ),
              if (boost > 0.3) ...[
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                  decoration: BoxDecoration(
                    color: AppTheme.skyBg,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(item.why,
                      style: const TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.indigo)),
                ),
              ],
              const SizedBox(height: 6),
              Text(
                'rel ${b['relevance']} · new-seller ${b['new_seller_boost']} · '
                'region ${b['underserved_region_boost']} · '
                'exposure −${b['exposure_penalty']} · score ${b['final_score']}',
                style: const TextStyle(fontSize: 10.5, color: AppTheme.inkSoft),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CompareSheet extends StatefulWidget {
  const _CompareSheet({required this.query});
  final String query;

  @override
  State<_CompareSheet> createState() => _CompareSheetState();
}

class _CompareSheetState extends State<_CompareSheet> {
  late Future<J> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AppState>().api.searchCompare(widget.query);
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      builder: (_, controller) => FutureBuilder<J>(
        future: _future,
        builder: (context, snap) {
          if (!snap.hasData) return const LoadingView();
          final d = snap.data!;
          final on = asMapList(d['fairness_on']);
          final off = asMapList(d['fairness_off']);
          return ListView(
            controller: controller,
            padding: const EdgeInsets.all(16),
            children: [
              Text('Fairness ON vs OFF — "${widget.query}"',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                'gap on ${asMap(d['exposure_gap_on'])['gap']} · '
                'gap off ${asMap(d['exposure_gap_off'])['gap']}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: _Col(title: 'Fair ON', rows: on)),
                  const SizedBox(width: 10),
                  Expanded(child: _Col(title: 'Fair OFF', rows: off)),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Col extends StatelessWidget {
  const _Col({required this.title, required this.rows});
  final String title;
  final List<J> rows;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        for (final r in rows)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Text(
              '${r['rank']}. ${r['artisan']} — ${r['craft']}',
              style: const TextStyle(fontSize: 12),
            ),
          ),
      ],
    );
  }
}
