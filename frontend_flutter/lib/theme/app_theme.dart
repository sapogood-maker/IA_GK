import 'package:flutter/material.dart';

/// Design tokens do Goalkeeper Premium UI (Design System v2, Sprint UX-01).
///
/// Tema escuro premium: roxo é usado apenas como cor de DESTAQUE (botão
/// principal, seleção da sidebar, ícone de marca) - nunca como preenchimento
/// dominante de cards ou telas inteiras. Verde é reservado exclusivamente
/// para sucesso/online/concluído/confirmado.
class AppColors {
  const AppColors._();

  static const Color background = Color(0xFF09090B);
  static const Color sidebar = Color(0xFF111113);
  static const Color card = Color(0xFF18181B);
  static const Color hover = Color(0xFF232329);
  static const Color border = Color(0xFF27272A);

  static const Color textPrimary = Color(0xFFFAFAFA);
  static const Color textSecondary = Color(0xFFA1A1AA);

  static const Color primary = Color(0xFF7C3AED);
  static const Color primaryHover = Color(0xFF8B5CF6);
  static const Color accent = Color(0xFFA855F7);

  static const Color success = Color(0xFF22C55E);
  static const Color error = Color(0xFFEF4444);
  static const Color warning = Color(0xFFF59E0B);

  /// Não faz parte da paleta original do enunciado - adicionado para dar a
  /// "Queued" um tom azul/roxo visualmente distinto do roxo de destaque
  /// (usado no botão principal e na seleção da sidebar), evitando que dois
  /// conceitos diferentes (status "na fila" x cor de marca) pareçam iguais.
  static const Color statusQueued = Color(0xFF6366F1);

  /// Chip neutro para textos que reusam o mesmo componente de "etiqueta"
  /// mas não representam um status de processamento (ex.: papel de
  /// usuário) - cinza, nunca verde por padrão.
  static const Color neutralChipBackground = hover;
  static const Color neutralChipBorder = border;
  static const Color neutralChipText = textSecondary;
}

class AppRadius {
  const AppRadius._();

  static const double sm = 10;
  static const double md = 14;
  static const double lg = 18;
}

class AppSpacing {
  const AppSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;
}

/// Único gradiente do Design System v2 - reservado para o botão principal
/// ("Enviar Vídeo", a chamada visual mais importante da aplicação). Cards,
/// sidebar e ícones usam cores sólidas para manter o roxo como destaque, não
/// como preenchimento repetido.
class AppGradients {
  const AppGradients._();

  static const LinearGradient primaryButton = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [AppColors.primary, AppColors.accent],
  );
}

ThemeData buildAppTheme() {
  const colorScheme = ColorScheme.dark(
    brightness: Brightness.dark,
    primary: AppColors.primary,
    onPrimary: AppColors.textPrimary,
    secondary: AppColors.accent,
    onSecondary: AppColors.textPrimary,
    error: AppColors.error,
    onError: AppColors.textPrimary,
    surface: AppColors.card,
    onSurface: AppColors.textPrimary,
    surfaceContainerHighest: AppColors.hover,
    outline: AppColors.border,
  );

  const baseTextTheme = TextTheme(
    headlineMedium: TextStyle(
      fontWeight: FontWeight.w700,
      letterSpacing: -0.4,
      height: 1.2,
    ),
    headlineSmall: TextStyle(
      fontWeight: FontWeight.w700,
      letterSpacing: -0.3,
      height: 1.25,
    ),
    titleLarge: TextStyle(
      fontWeight: FontWeight.w700,
      letterSpacing: -0.2,
    ),
    titleMedium: TextStyle(fontWeight: FontWeight.w600, letterSpacing: -0.1),
    titleSmall: TextStyle(fontWeight: FontWeight.w600),
    bodyMedium: TextStyle(height: 1.45),
    bodySmall: TextStyle(color: AppColors.textSecondary, height: 1.4),
    labelMedium: TextStyle(fontWeight: FontWeight.w600, letterSpacing: 0.1),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: AppColors.background,
    canvasColor: AppColors.background,
    fontFamily: 'Roboto',
    textTheme: baseTextTheme,
    dividerTheme: const DividerThemeData(
      color: AppColors.border,
      thickness: 1,
      space: 24,
    ),
    iconTheme: const IconThemeData(size: 20, color: AppColors.textSecondary),
    cardTheme: CardThemeData(
      color: AppColors.card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.hover,
      hintStyle: const TextStyle(color: AppColors.textSecondary),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.4),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.hover,
        foregroundColor: AppColors.textPrimary,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xl,
          vertical: AppSpacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        side: const BorderSide(color: AppColors.border),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.textSecondary),
    ),
  );
}
