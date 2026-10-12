// Implementable Life Assistant visual system for Flutter Web.
// The concept-art posters are references, not images rendered as app screens.
import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../app/theme/app_theme.dart';
import 'session_identity.dart';
import 'appearance_storage.dart';

enum LifeVisualStyle { warm, fresh, focus, animated, pinkBubble }

extension LifeVisualStyleLabel on LifeVisualStyle {
  String get label => switch (this) {
    LifeVisualStyle.warm => '暖心日常',
    LifeVisualStyle.fresh => '清新活力',
    LifeVisualStyle.focus => '知性專注',
    LifeVisualStyle.animated => '動畫風格',
    LifeVisualStyle.pinkBubble => '粉紅泡泡',
  };
  String get description => switch (this) {
    LifeVisualStyle.warm => '溫暖、舒適、有秩序',
    LifeVisualStyle.fresh => '明亮、愉快、喜歡探索',
    LifeVisualStyle.focus => '清晰、可靠、專心做事',
    LifeVisualStyle.animated => '鮮明色塊、趣味圖形、輕量動態，無動漫人物',
    LifeVisualStyle.pinkBubble => '柔和粉彩、圓潤泡泡與甜美卡片',
  };
}

@immutable
class LifeAppearance {
  const LifeAppearance({
    this.style = LifeVisualStyle.warm,
    this.mode = ThemeMode.system,
  });
  final LifeVisualStyle style;
  final ThemeMode mode;
}

class LifeAppearanceController extends StateNotifier<LifeAppearance> {
  LifeAppearanceController(String? account)
      : _key = account == null || account.isEmpty
            ? null
            : 'life.appearance.v1.${sha256.convert(utf8.encode(account.toLowerCase()))}',
        super(_read(account));

  final String? _key;

  static LifeAppearance _read(String? account) {
    if (account == null || account.isEmpty) return const LifeAppearance();
    try {
      final key = 'life.appearance.v1.${sha256.convert(utf8.encode(account.toLowerCase()))}';
      final raw = getStoredAppearance(key);
      if (raw == null) return const LifeAppearance();
      final json = jsonDecode(raw) as Map<String, dynamic>;
      return LifeAppearance(
        style: LifeVisualStyle.values.firstWhere(
          (s) => s.name == json['style'],
          orElse: () => LifeVisualStyle.warm,
        ),
        mode: ThemeMode.values.firstWhere(
          (m) => m.name == json['mode'],
          orElse: () => ThemeMode.system,
        ),
      );
    } catch (_) {
      // Storage may be disabled. Never block the app for a theme preference.
      return const LifeAppearance();
    }
  }

  void setStyle(LifeVisualStyle style) {
    state = LifeAppearance(style: style, mode: state.mode);
    _persist();
  }

  void setMode(ThemeMode mode) {
    state = LifeAppearance(style: state.style, mode: mode);
    _persist();
  }

  void _persist() {
    if (_key == null) return;
    try {
      setStoredAppearance(_key, jsonEncode({
        'style': state.style.name,
        'mode': state.mode.name,
      }));
    } catch (_) {
      // In-memory selection still works in browsers with restricted storage.
    }
  }
}

final lifeAppearanceProvider =
    StateNotifierProvider<LifeAppearanceController, LifeAppearance>((ref) {
  // A different account gets a distinct preference state and storage key.
  return LifeAppearanceController(ref.watch(sessionIdentityProvider));
});

/// A single Material 3 widget tree; palette, geometry and semantics vary.
abstract class LifeVisualTheme {
  static ThemeData build(LifeVisualStyle style, Brightness brightness) {
    final dark = brightness == Brightness.dark;
    final base = dark ? AppTheme.dark : AppTheme.light;
    final canvas = switch (style) {
      LifeVisualStyle.warm => dark ? const Color(0xFF181A18) : const Color(0xFFF7F3EA),
      LifeVisualStyle.fresh => dark ? const Color(0xFF142326) : const Color(0xFFF1FAFC),
      LifeVisualStyle.focus => dark ? const Color(0xFF161C25) : const Color(0xFFF3F5F8),
      LifeVisualStyle.animated => dark ? const Color(0xFF14223B) : const Color(0xFFEAF7FF),
      LifeVisualStyle.pinkBubble => dark ? const Color(0xFF2D1A2A) : const Color(0xFFFFF0F8),
    };
    final paper = switch (style) {
      LifeVisualStyle.warm => dark ? const Color(0xFF252824) : const Color(0xFFFFFCF6),
      LifeVisualStyle.fresh => dark ? const Color(0xFF1D3032) : Colors.white,
      LifeVisualStyle.focus => dark ? const Color(0xFF242D39) : Colors.white,
      LifeVisualStyle.animated => dark ? const Color(0xFF213653) : Colors.white,
      LifeVisualStyle.pinkBubble => dark ? const Color(0xFF402838) : const Color(0xFFFFFBFE),
    };
    final ink = dark ? const Color(0xFFF3F4F1) : const Color(0xFF263449);
    final primary = switch (style) {
      LifeVisualStyle.warm => dark ? const Color(0xFFA4B49C) : const Color(0xFF71896B),
      LifeVisualStyle.fresh => dark ? const Color(0xFF6CE1D0) : const Color(0xFF168D85),
      LifeVisualStyle.focus => dark ? const Color(0xFF98B6D7) : const Color(0xFF405F87),
      LifeVisualStyle.animated => dark ? const Color(0xFF91BAFF) : const Color(0xFF3263CC),
      LifeVisualStyle.pinkBubble => dark ? const Color(0xFFFFACD1) : const Color(0xFFAD3E78),
    };
    final secondary = switch (style) {
      LifeVisualStyle.warm => const Color(0xFFD99A67),
      LifeVisualStyle.fresh => const Color(0xFFFF806C),
      LifeVisualStyle.focus => const Color(0xFF7B92A8),
      LifeVisualStyle.animated => const Color(0xFFE9A423),
      LifeVisualStyle.pinkBubble => const Color(0xFFD47FB5),
    };
    final soft = Color.lerp(primary, paper, dark ? 0.83 : 0.86)!;
    final radius = switch (style) {
      LifeVisualStyle.warm => 16.0,
      LifeVisualStyle.fresh => 22.0,
      LifeVisualStyle.focus => 10.0,
      LifeVisualStyle.animated => 24.0,
      LifeVisualStyle.pinkBubble => 28.0,
    };
    final scheme = base.colorScheme.copyWith(
      primary: primary,
      onPrimary: dark ? const Color(0xFF142326) : Colors.white,
      secondary: secondary,
      surface: paper,
      onSurface: ink,
    );

    return base.copyWith(
      scaffoldBackgroundColor: canvas,
      colorScheme: scheme,
      textTheme: base.textTheme.apply(bodyColor: ink, displayColor: ink),
      appBarTheme: base.appBarTheme.copyWith(
        backgroundColor: canvas,
        foregroundColor: ink,
        titleTextStyle: base.appBarTheme.titleTextStyle?.copyWith(color: ink),
      ),
      cardTheme: base.cardTheme.copyWith(
        color: paper,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radius),
          side: BorderSide(color: primary.withOpacity(dark ? 0.24 : 0.12)),
        ),
      ),
      navigationRailTheme: base.navigationRailTheme.copyWith(
        backgroundColor: paper,
        indicatorColor: soft,
        selectedIconTheme: IconThemeData(color: primary, size: 22),
        selectedLabelTextStyle: TextStyle(color: primary, fontWeight: FontWeight.w600),
      ),
      navigationBarTheme: base.navigationBarTheme.copyWith(
        backgroundColor: paper,
        indicatorColor: soft,
      ),
      floatingActionButtonTheme: base.floatingActionButtonTheme.copyWith(
        backgroundColor: primary,
        foregroundColor: scheme.onPrimary,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: scheme.onPrimary,
          minimumSize: const Size(0, 44),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius * .75)),
        ),
      ),
      inputDecorationTheme: base.inputDecorationTheme.copyWith(
        fillColor: paper,
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radius * .75),
          borderSide: BorderSide(color: primary, width: 1.5),
        ),
      ),
      checkboxTheme: base.checkboxTheme.copyWith(
        fillColor: WidgetStateProperty.resolveWith((states) =>
          states.contains(WidgetState.selected) ? primary : Colors.transparent),
        checkColor: WidgetStatePropertyAll(scheme.onPrimary),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: BorderSide(color: primary),
          minimumSize: const Size(0, 44),
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        selectedColor: soft,
        checkmarkColor: primary,
      ),
    );
  }
}

enum LifeVisualFeature { today, tasks, explore, opportunities, calendar, projects, notes, habits, shopping, drive, personalize }

extension LifeVisualFeatureInfo on LifeVisualFeature {
  String get title => switch (this) {
    LifeVisualFeature.tasks => '待辦',
    LifeVisualFeature.explore => '活動探索',
    LifeVisualFeature.opportunities => '限時機會',
    LifeVisualFeature.calendar => '日曆',
    LifeVisualFeature.projects => '專案',
    LifeVisualFeature.notes => '筆記',
    LifeVisualFeature.today => '今日重點',
    LifeVisualFeature.habits => '習慣',
    LifeVisualFeature.shopping => '購物清單',
    LifeVisualFeature.drive => 'Google Drive 智能整理',
    LifeVisualFeature.personalize => '個人化',
  };

  String get description => switch (this) {
    LifeVisualFeature.tasks => '把想做的事，一件一件完成。',
    LifeVisualFeature.explore => '發現生活中更多值得期待的活動。',
    LifeVisualFeature.opportunities => '留意開報時間，把握喜歡的機會。',
    LifeVisualFeature.calendar => '每一天，都有自己的節奏。',
    LifeVisualFeature.projects => '有計畫地前進，讓想法逐步實現。',
    LifeVisualFeature.notes => '隨手記下生活中的靈感。',
    LifeVisualFeature.today => '掌握今天的重要事項。',
    LifeVisualFeature.habits => '記錄生活習慣與完成進度。',
    LifeVisualFeature.shopping => '依清單整理每次採買。',
    LifeVisualFeature.drive => '管理已授權的雲端文件。',
    LifeVisualFeature.personalize => '調整首頁、導覽、外觀與個人服務。',
  };

  IconData get icon => switch (this) {
    LifeVisualFeature.tasks => Icons.checklist_rounded,
    LifeVisualFeature.explore => Icons.explore_rounded,
    LifeVisualFeature.opportunities => Icons.confirmation_number_outlined,
    LifeVisualFeature.calendar => Icons.calendar_month_rounded,
    LifeVisualFeature.projects => Icons.folder_copy_outlined,
    LifeVisualFeature.notes => Icons.edit_note_rounded,
    LifeVisualFeature.today => Icons.auto_awesome_outlined,
    LifeVisualFeature.habits => Icons.repeat_rounded,
    LifeVisualFeature.shopping => Icons.shopping_cart_outlined,
    LifeVisualFeature.drive => Icons.cloud_outlined,
    LifeVisualFeature.personalize => Icons.tune_rounded,
  };

  Color get color => switch (this) {
    LifeVisualFeature.tasks => const Color(0xFF538E82),
    LifeVisualFeature.explore => const Color(0xFFE09A4B),
    LifeVisualFeature.opportunities => const Color(0xFFD56D70),
    LifeVisualFeature.calendar => const Color(0xFF927BB0),
    LifeVisualFeature.projects => const Color(0xFF6586B2),
    LifeVisualFeature.notes => const Color(0xFFBE9468),
    LifeVisualFeature.today => const Color(0xFFC47BA8),
    LifeVisualFeature.habits => const Color(0xFF6A9A81),
    LifeVisualFeature.shopping => const Color(0xFFD39A53),
    LifeVisualFeature.drive => const Color(0xFF678FB2),
    LifeVisualFeature.personalize => const Color(0xFF8C83BF),
  };
}

/// Lightweight native header. Does not invent photos, deadlines, counts or states.
class LifeFeatureHeader extends ConsumerWidget {
  const LifeFeatureHeader({super.key, required this.feature, this.trailing});
  final LifeVisualFeature feature;
  /// Place the page's primary action in its only visual heading, not a second AppBar.
  final Widget? trailing;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final style = ref.watch(lifeAppearanceProvider).style;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final tint = style == LifeVisualStyle.focus
        ? Color.lerp(feature.color, Theme.of(context).colorScheme.primary, .45)!
        : feature.color;
    final background = Color.lerp(
      Theme.of(context).colorScheme.surface,
      tint,
      dark ? .17 : style == LifeVisualStyle.fresh ? .14 : .09,
    )!;
    final roundness = style == LifeVisualStyle.focus ? 12.0 :
        style == LifeVisualStyle.pinkBubble ? 30.0 :
        style == LifeVisualStyle.animated ? 26.0 : 20.0;
    return Container(
      constraints: const BoxConstraints(minHeight: 66),
      decoration: BoxDecoration(
        gradient: style == LifeVisualStyle.animated || style == LifeVisualStyle.pinkBubble
            ? LinearGradient(colors: [background,
                Color.lerp(background, Theme.of(context).colorScheme.secondary,
                    dark ? .13 : .17)!]) : null,
        color: style == LifeVisualStyle.animated || style == LifeVisualStyle.pinkBubble
            ? null : background,
        borderRadius: BorderRadius.circular(roundness),
        border: Border.all(color: tint.withOpacity(.20)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      child: Row(children: [
        Container(
          width: 42, height: 42,
          decoration: BoxDecoration(
            color: tint.withOpacity(dark ? .23 : .15),
            borderRadius: BorderRadius.circular(style == LifeVisualStyle.focus ? 10 : 16),
          ),
          child: Icon(feature.icon, color: dark ? Color.lerp(tint, Colors.white, .35) : tint, size: 27),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(feature.title, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700)),
            const SizedBox(height: 3),
            Text(feature.description, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall),
          ],
        )),
        if (trailing != null)
          Padding(padding: const EdgeInsets.only(left: 8), child: trailing!)
        else if (style == LifeVisualStyle.animated || style == LifeVisualStyle.pinkBubble)
          Padding(
            padding: const EdgeInsets.only(left: 6),
            child: Icon(style == LifeVisualStyle.animated
                ? Icons.auto_awesome_rounded : Icons.bubble_chart_outlined,
                size: 28, color: tint.withOpacity(.65)),
          ),
      ]),
    );
  }
}
