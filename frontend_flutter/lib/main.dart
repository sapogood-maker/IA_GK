import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:file_picker/file_picker.dart';

import 'models/auth_user.dart';
import 'models/club.dart';
import 'models/goalkeeper.dart';
import 'models/training_session.dart';
import 'models/video.dart';
import 'providers/auth_provider.dart';
import 'providers/club_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/goalkeeper_provider.dart';
import 'providers/system_provider.dart';
import 'providers/training_session_provider.dart';
import 'providers/user_provider.dart';
import 'providers/video_provider.dart';
import 'repositories/auth_repository.dart';
import 'repositories/club_repository.dart';
import 'repositories/dashboard_repository.dart';
import 'repositories/goalkeeper_repository.dart';
import 'repositories/system_repository.dart';
import 'repositories/training_session_repository.dart';
import 'repositories/user_repository.dart';
import 'repositories/video_repository.dart';
import 'services/api_client.dart';
import 'services/goalkeeper_service.dart';
import 'services/session_service.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final preferences = await SharedPreferences.getInstance();
  final sessionService = SessionService(preferences);
  final apiClient = ApiClient(sessionService);
  final authRepository = AuthRepository(apiClient, sessionService);
  final dashboardRepository = DashboardRepository(apiClient);
  final goalkeeperRepository = GoalkeeperRepository(apiClient);
  final goalkeeperService = GoalkeeperService(goalkeeperRepository);
  final clubRepository = ClubRepository(apiClient);
  final trainingSessionRepository = TrainingSessionRepository(apiClient);
  final videoRepository = VideoRepository(apiClient);
  final userRepository = UserRepository(apiClient);
  final systemRepository = SystemRepository(apiClient);
  final authProvider = AuthProvider(authRepository, sessionService);

  await authProvider.initialize();

  runApp(
    GkPerformanceApp(
      authProvider: authProvider,
      dashboardProvider: DashboardProvider(dashboardRepository),
      goalkeeperProvider: GoalkeeperProvider(goalkeeperService),
      clubProvider: ClubProvider(clubRepository),
      trainingSessionProvider: TrainingSessionProvider(
        trainingSessionRepository,
      ),
      videoProvider: VideoProvider(videoRepository),
      userProvider: UserProvider(userRepository),
      systemProvider: SystemProvider(systemRepository),
    ),
  );
}

GoRouter _createRouter(AuthProvider authProvider) => GoRouter(
  initialLocation: '/painel',
  refreshListenable: authProvider,
  redirect: (context, state) {
    if (authProvider.isLoading) {
      return null;
    }

    final path = state.uri.path;
    final isLogin = path == '/login';

    if (!authProvider.isAuthenticated) {
      return isLogin ? null : '/login';
    }

    if (path == '/' || isLogin) {
      return '/painel';
    }

    return null;
  },
  routes: [
    GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
    ShellRoute(
      builder: (context, state, child) => PainelGoleirosPage(child: child),
      routes: [
        GoRoute(
          path: '/painel',
          builder: (context, state) => const PainelScreen(),
        ),
        GoRoute(
          path: '/clubes',
          builder: (context, state) => const ClubesScreen(),
        ),
        GoRoute(
          path: '/goleiros',
          builder: (context, state) => const GoleirosScreen(),
        ),
        GoRoute(
          path: '/videos',
          builder: (context, state) => const VideosScreen(),
        ),
        GoRoute(
          path: '/analises',
          builder: (context, state) => const AnalisesScreen(),
        ),
        GoRoute(
          path: '/sessoes-de-treino',
          builder: (context, state) => const SessoesTreinoScreen(),
        ),
        GoRoute(
          path: '/relatorios',
          builder: (context, state) => const RelatoriosScreen(),
        ),
        GoRoute(
          path: '/telegram',
          builder: (context, state) => const TelegramScreen(),
        ),
        GoRoute(
          path: '/usuarios',
          builder: (context, state) => const UsuariosScreen(),
        ),
        GoRoute(
          path: '/configuracoes',
          builder: (context, state) => const ConfiguracoesScreen(),
        ),
      ],
    ),
  ],
);

const _itensMenu = [
  _ItemMenu('Painel', Icons.dashboard_outlined, '/painel'),
  _ItemMenu('Clubes', Icons.shield_outlined, '/clubes'),
  _ItemMenu('Goleiros', Icons.sports_handball_outlined, '/goleiros'),
  _ItemMenu('Vídeos', Icons.videocam_outlined, '/videos'),
  _ItemMenu('Análises', Icons.analytics_outlined, '/analises'),
  _ItemMenu(
    'Sessões de Treino',
    Icons.event_note_outlined,
    '/sessoes-de-treino',
  ),
  _ItemMenu('Relatórios', Icons.description_outlined, '/relatorios'),
  _ItemMenu('Telegram', Icons.send_outlined, '/telegram'),
  _ItemMenu('Usuários', Icons.group_outlined, '/usuarios'),
  _ItemMenu('Configurações', Icons.settings_outlined, '/configuracoes'),
];

class GkPerformanceApp extends StatelessWidget {
  const GkPerformanceApp({
    super.key,
    required this.authProvider,
    required this.dashboardProvider,
    required this.goalkeeperProvider,
    required this.clubProvider,
    required this.trainingSessionProvider,
    required this.videoProvider,
    required this.userProvider,
    required this.systemProvider,
  });

  final AuthProvider authProvider;
  final DashboardProvider dashboardProvider;
  final GoalkeeperProvider goalkeeperProvider;
  final ClubProvider clubProvider;
  final TrainingSessionProvider trainingSessionProvider;
  final VideoProvider videoProvider;
  final UserProvider userProvider;
  final SystemProvider systemProvider;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
        ChangeNotifierProvider<DashboardProvider>.value(
          value: dashboardProvider,
        ),
        ChangeNotifierProvider<GoalkeeperProvider>.value(
          value: goalkeeperProvider,
        ),
        ChangeNotifierProvider<ClubProvider>.value(value: clubProvider),
        ChangeNotifierProvider<TrainingSessionProvider>.value(
          value: trainingSessionProvider,
        ),
        ChangeNotifierProvider<VideoProvider>.value(value: videoProvider),
        ChangeNotifierProvider<UserProvider>.value(value: userProvider),
        ChangeNotifierProvider<SystemProvider>.value(value: systemProvider),
      ],
      child: Builder(
        builder: (context) {
          return MaterialApp.router(
            title: 'GK Desempenho',
            debugShowCheckedModeBanner: false,
            themeMode: ThemeMode.dark,
            theme: buildAppTheme(),
            routerConfig: _createRouter(context.read<AuthProvider>()),
          );
        },
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final success = await context.read<AuthProvider>().login(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );

    if (mounted && success) {
      context.go('/painel');
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final isLoading = auth.isLoading;

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const _Marca(),
                      const SizedBox(height: 28),
                      Text(
                        'Entrar',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0,
                            ),
                      ),
                      const SizedBox(height: 18),
                      TextFormField(
                        controller: _emailController,
                        enabled: !isLoading,
                        keyboardType: TextInputType.emailAddress,
                        autofillHints: const [AutofillHints.email],
                        decoration: const InputDecoration(
                          labelText: 'E-mail',
                          prefixIcon: Icon(Icons.mail_outline),
                        ),
                        validator: (value) {
                          final email = value?.trim() ?? '';
                          if (email.isEmpty) {
                            return 'Informe seu e-mail.';
                          }
                          if (!email.contains('@')) {
                            return 'Informe um e-mail válido.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _passwordController,
                        enabled: !isLoading,
                        obscureText: true,
                        autofillHints: const [AutofillHints.password],
                        decoration: const InputDecoration(
                          labelText: 'Senha',
                          prefixIcon: Icon(Icons.lock_outline),
                        ),
                        onFieldSubmitted: (_) => _submit(),
                        validator: (value) {
                          if ((value ?? '').isEmpty) {
                            return 'Informe sua senha.';
                          }
                          return null;
                        },
                      ),
                      if (auth.errorMessage != null) ...[
                        const SizedBox(height: 14),
                        Text(
                          auth.errorMessage!,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(color: AppColors.error),
                        ),
                      ],
                      const SizedBox(height: 22),
                      FilledButton.icon(
                        onPressed: isLoading ? null : _submit,
                        icon: isLoading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.login),
                        label: const Text('Entrar'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class PainelGoleirosPage extends StatefulWidget {
  const PainelGoleirosPage({super.key, required this.child});

  final Widget child;

  @override
  State<PainelGoleirosPage> createState() => _PainelGoleirosPageState();
}

class _PainelGoleirosPageState extends State<PainelGoleirosPage> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth >= 1040;
        final caminhoAtual = GoRouterState.of(context).uri.path;
        final indiceSelecionado = _indiceDaRota(caminhoAtual);
        final tituloAtual = _itensMenu[indiceSelecionado].titulo;
        return Scaffold(
          key: _scaffoldKey,
          appBar: isDesktop
              ? null
              : AppBar(
                  title: Text(tituloAtual),
                  leading: IconButton(
                    tooltip: 'Abrir menu',
                    onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                    icon: const Icon(Icons.menu),
                  ),
                ),
          drawer: isDesktop
              ? null
              : Drawer(
                  backgroundColor: AppColors.sidebar,
                  child: _MenuLateral(
                    itens: _itensMenu,
                    selecionado: indiceSelecionado,
                    aoSelecionar: (item) {
                      context.go(item.caminho);
                      Navigator.pop(context);
                    },
                  ),
                ),
          body: Row(
            children: [
              if (isDesktop)
                _MenuLateral(
                  itens: _itensMenu,
                  selecionado: indiceSelecionado,
                  aoSelecionar: (item) => context.go(item.caminho),
                ),
              Expanded(child: widget.child),
            ],
          ),
        );
      },
    );
  }

  int _indiceDaRota(String caminho) {
    final indice = _itensMenu.indexWhere((item) => item.caminho == caminho);
    return indice == -1 ? 0 : indice;
  }
}

class PainelScreen extends StatefulWidget {
  const PainelScreen({super.key});

  @override
  State<PainelScreen> createState() => _PainelScreenState();
}

class _PainelScreenState extends State<PainelScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<DashboardProvider>().load();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return const _ConteudoPainel(abrirMenu: null);
  }
}

class _ConteudoPainel extends StatelessWidget {
  const _ConteudoPainel({required this.abrirMenu});

  final VoidCallback? abrirMenu;

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
            child: _Cabecalho(abrirMenu: abrirMenu),
          ),
        ),
        const SliverPadding(
          padding: EdgeInsets.fromLTRB(24, 8, 24, 24),
          sliver: SliverToBoxAdapter(child: _ResumoExecutivo()),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
          sliver: SliverToBoxAdapter(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final largura = constraints.maxWidth;
                final isWide = largura >= 1180;
                return isWide
                    ? const Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 7, child: _ColunaPrincipal()),
                          SizedBox(width: 20),
                          Expanded(flex: 4, child: _ColunaSecundaria()),
                        ],
                      )
                    : const Column(
                        children: [
                          _ColunaPrincipal(),
                          SizedBox(height: 20),
                          _ColunaSecundaria(),
                        ],
                      );
              },
            ),
          ),
        ),
      ],
    );
  }
}

class _Cabecalho extends StatelessWidget {
  const _Cabecalho({required this.abrirMenu});

  final VoidCallback? abrirMenu;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compacto = constraints.maxWidth < 840;
        final titulo = _TituloPainel(abrirMenu: abrirMenu);
        final acoes = const _AcoesCabecalho();

        if (compacto) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [titulo, const SizedBox(height: 14), acoes],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(child: titulo),
            const SizedBox(width: 18),
            SizedBox(width: 520, child: acoes),
          ],
        );
      },
    );
  }
}

class _TituloPainel extends StatelessWidget {
  const _TituloPainel({required this.abrirMenu});

  final VoidCallback? abrirMenu;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        if (abrirMenu != null)
          IconButton(
            tooltip: 'Abrir menu',
            onPressed: abrirMenu,
            icon: const Icon(Icons.menu),
          ),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Painel',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Análise de desempenho para goleiros de alto rendimento',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _AcoesCabecalho extends StatelessWidget {
  const _AcoesCabecalho();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Expanded(
          child: TextField(
            decoration: InputDecoration(
              hintText: 'Pesquisar goleiro, clube ou vídeo',
              prefixIcon: Icon(Icons.search),
            ),
          ),
        ),
        const SizedBox(width: 12),
        _BotaoGradiente(
          icon: Icons.cloud_upload_outlined,
          label: 'Enviar Vídeo',
          onPressed: () {},
        ),
      ],
    );
  }
}

/// Botão principal da aplicação ("Enviar Vídeo") - único elemento com
/// gradiente roxo do Design System v2, para se destacar como a chamada
/// visual mais importante da tela (Sprint UX-01). Nunca usado para ações
/// secundárias, mantendo o roxo como cor de destaque, não de preenchimento.
class _BotaoGradiente extends StatefulWidget {
  const _BotaoGradiente({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  State<_BotaoGradiente> createState() => _BotaoGradienteState();
}

class _BotaoGradienteState extends State<_BotaoGradiente> {
  bool _hovering = false;
  bool _pressing = false;

  @override
  Widget build(BuildContext context) {
    final disabled = widget.onPressed == null;
    return MouseRegion(
      cursor: disabled
          ? SystemMouseCursors.basic
          : SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovering = true),
      onExit: (_) => setState(() => _hovering = false),
      child: GestureDetector(
        onTapDown: (_) => setState(() => _pressing = true),
        onTapUp: (_) => setState(() => _pressing = false),
        onTapCancel: () => setState(() => _pressing = false),
        child: AnimatedScale(
          scale: _pressing && !disabled
              ? 0.97
              : _hovering && !disabled
              ? 1.02
              : 1.0,
          duration: const Duration(milliseconds: 140),
          curve: Curves.easeOut,
          child: AnimatedOpacity(
            opacity: disabled ? 0.5 : 1.0,
            duration: const Duration(milliseconds: 180),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              decoration: BoxDecoration(
                gradient: AppGradients.primaryButton,
                borderRadius: BorderRadius.circular(AppRadius.sm),
                boxShadow: _hovering && !disabled
                    ? [
                        BoxShadow(
                          color: AppColors.primary.withValues(alpha: 0.35),
                          blurRadius: 18,
                          offset: const Offset(0, 6),
                        ),
                      ]
                    : const [],
              ),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  onTap: widget.onPressed,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 14,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          widget.icon,
                          color: AppColors.textPrimary,
                          size: 19,
                        ),
                        const SizedBox(width: 10),
                        Text(
                          widget.label,
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ResumoExecutivo extends StatelessWidget {
  const _ResumoExecutivo();

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardProvider>();
    final data = dashboard.data;
    final carregando = dashboard.isLoading && data == null;
    final semDados = !carregando && (data == null || !data.hasAnyData);
    final valorSemDados = semDados ? 'Sem dados disponíveis' : '0';
    final indicadores = [
      _Indicador(
        'Vídeos Enviados',
        carregando ? '...' : data?.totalVideos.toString() ?? valorSemDados,
        semDados ? 'Endpoint sem dados' : 'Total retornado pela API',
        Icons.video_library_outlined,
      ),
      _Indicador(
        'Análises Concluídas',
        carregando
            ? '...'
            : data?.totalAnalisesConcluidas.toString() ?? valorSemDados,
        semDados ? 'Endpoint sem dados' : 'Jobs concluídos na API',
        Icons.check_circle_outline,
      ),
      _Indicador(
        'Sessões de Treino',
        carregando ? '...' : data?.totalSessoes.toString() ?? valorSemDados,
        semDados ? 'Endpoint sem dados' : 'Sessões retornadas pela API',
        Icons.event_note_outlined,
      ),
      _Indicador(
        'Clubes Ativos',
        carregando ? '...' : data?.totalClubes.toString() ?? valorSemDados,
        semDados ? 'Endpoint sem dados' : 'Clubes retornados pela API',
        Icons.shield_outlined,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final columns = width >= 1180
            ? 4
            : width >= 760
            ? 2
            : 1;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: indicadores.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
            mainAxisExtent: 164,
          ),
          itemBuilder: (context, index) =>
              _CardIndicador(indicador: indicadores[index]),
        );
      },
    );
  }
}

class _ColunaPrincipal extends StatelessWidget {
  const _ColunaPrincipal();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [_SecaoAnalises(), SizedBox(height: 20), _SecaoGoleiros()],
    );
  }
}

class _ColunaSecundaria extends StatelessWidget {
  const _ColunaSecundaria();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        _MapaDesempenho(),
        SizedBox(height: 20),
        _SessoesRecentes(),
        SizedBox(height: 20),
        _EnvioRapido(),
      ],
    );
  }
}

class _MenuLateral extends StatelessWidget {
  const _MenuLateral({
    required this.itens,
    required this.selecionado,
    required this.aoSelecionar,
  });

  final List<_ItemMenu> itens;
  final int selecionado;
  final ValueChanged<_ItemMenu> aoSelecionar;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      decoration: const BoxDecoration(
        color: AppColors.sidebar,
        border: Border(right: BorderSide(color: AppColors.border)),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 20, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _Marca(),
              const SizedBox(height: 28),
              Expanded(
                child: ListView.separated(
                  itemCount: itens.length,
                  separatorBuilder: (_, indiceSeparador) =>
                      const SizedBox(height: 4),
                  itemBuilder: (context, index) {
                    final item = itens[index];
                    final ativo = index == selecionado;
                    return _BotaoMenu(
                      item: item,
                      ativo: ativo,
                      onTap: () => aoSelecionar(item),
                    );
                  },
                ),
              ),
              const _StatusProcessamento(),
              const SizedBox(height: 12),
              const _SessaoUsuario(),
            ],
          ),
        ),
      ),
    );
  }
}

class _Marca extends StatelessWidget {
  const _Marca();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(
            Icons.sports_soccer,
            color: AppColors.textPrimary,
            size: 20,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'GK Desempenho',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.1,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                'Análise de goleiros',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _BotaoMenu extends StatelessWidget {
  const _BotaoMenu({
    required this.item,
    required this.ativo,
    required this.onTap,
  });

  final _ItemMenu item;
  final bool ativo;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        hoverColor: AppColors.hover,
        splashColor: AppColors.primary.withValues(alpha: 0.12),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          decoration: BoxDecoration(
            color: ativo ? AppColors.primary.withValues(alpha: 0.12) : null,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 11),
          child: Row(
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: 3,
                height: 18,
                decoration: BoxDecoration(
                  color: ativo ? AppColors.primary : Colors.transparent,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 11),
              Icon(
                item.icone,
                size: 19,
                color: ativo ? AppColors.textPrimary : AppColors.textSecondary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  item.titulo,
                  style: TextStyle(
                    color: ativo
                        ? AppColors.textPrimary
                        : AppColors.textSecondary,
                    fontWeight: ativo ? FontWeight.w600 : FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusProcessamento extends StatelessWidget {
  const _StatusProcessamento();

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardProvider>();
    final totalEmProcessamento = dashboard.data?.totalEmProcessamento;
    final texto = dashboard.isLoading && dashboard.data == null
        ? 'Carregando fila da IA'
        : totalEmProcessamento == null || totalEmProcessamento == 0
        ? 'Sem dados disponíveis'
        : '$totalEmProcessamento vídeos em processamento';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: AppColors.hover,
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                  ),
                  child: const Icon(
                    Icons.memory_outlined,
                    color: AppColors.textSecondary,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Goalkeeper AI',
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(
                          context,
                        ).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      Text(
                        'Cognitive Platform v1.0',
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(
                          context,
                        ).textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: AppColors.success,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  'Pronta para análise',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: AppColors.success,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(height: 1),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: totalEmProcessamento == null
                  ? null
                  : totalEmProcessamento > 0
                  ? 0.68
                  : 0,
              color: AppColors.primary,
              backgroundColor: AppColors.hover,
            ),
            const SizedBox(height: 8),
            Text(
              texto,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}

class _SessaoUsuario extends StatelessWidget {
  const _SessaoUsuario();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (user != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              user.email,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ),
        OutlinedButton.icon(
          onPressed: () async {
            await context.read<AuthProvider>().logout();
            if (context.mounted) {
              context.go('/login');
            }
          },
          icon: const Icon(Icons.logout),
          label: const Text('Sair'),
        ),
      ],
    );
  }
}

class _CardIndicador extends StatelessWidget {
  const _CardIndicador({required this.indicador});

  final _Indicador indicador;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppColors.hover,
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                  ),
                  child: Icon(
                    indicador.icone,
                    color: AppColors.textSecondary,
                    size: 20,
                  ),
                ),
                const Spacer(),
                const Icon(
                  Icons.trending_up,
                  color: AppColors.success,
                  size: 18,
                ),
              ],
            ),
            const Spacer(),
            Text(
              indicador.valor,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style:
                  (indicador.valor.length > 8
                          ? Theme.of(context).textTheme.titleMedium
                          : Theme.of(context).textTheme.headlineMedium)
                      ?.copyWith(
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.4,
                        color: AppColors.textPrimary,
                      ),
            ),
            const SizedBox(height: 4),
            Text(
              indicador.titulo,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              indicador.subtitulo,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}

class _SecaoAnalises extends StatelessWidget {
  const _SecaoAnalises();

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardProvider>();
    final jobs = dashboard.data?.analises ?? const <Map<String, dynamic>>[];
    final analises = jobs.take(4).map((job) {
      final status = job['status']?.toString() ?? 'Sem status';
      final progresso = (job['progress'] as num?)?.toDouble() ?? 0;
      return _Analise(
        'Vídeo ${job['video_id'] ?? 'sem identificação'}',
        'Job ${job['id'] ?? job['job_id'] ?? ''}',
        job['job_type']?.toString() ?? 'Análise de vídeo',
        status,
        (progresso / 100).clamp(0, 1).toDouble(),
      );
    }).toList();

    return _Bloco(
      titulo: 'Fila de análises',
      acao: TextButton.icon(
        onPressed: () {},
        icon: const Icon(Icons.filter_list),
        label: const Text('Filtrar'),
      ),
      child: dashboard.isLoading && analises.isEmpty
          ? const _MensagemSemDados(texto: 'Carregando dados da API')
          : analises.isEmpty
          ? const _MensagemSemDados()
          : Column(
              children: [
                for (final analise in analises) ...[
                  _LinhaAnalise(analise: analise),
                  if (analise != analises.last) const Divider(height: 24),
                ],
              ],
            ),
    );
  }
}

class _LinhaAnalise extends StatelessWidget {
  const _LinhaAnalise({required this.analise});

  final _Analise analise;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(Icons.sports_soccer, color: AppColors.textSecondary),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                analise.goleiro,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                '${analise.clube} • ${analise.foco}',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
        SizedBox(
          width: 128,
          child: LinearProgressIndicator(value: analise.progresso),
        ),
        const SizedBox(width: 14),
        _Etiqueta(texto: analise.status),
        const SizedBox(width: 8),
        IconButton(
          tooltip: 'Abrir análise',
          onPressed: () {},
          icon: const Icon(Icons.open_in_new),
        ),
      ],
    );
  }
}

class _SecaoGoleiros extends StatelessWidget {
  const _SecaoGoleiros();

  @override
  Widget build(BuildContext context) {
    return _Bloco(
      titulo: 'Goleiros em destaque',
      acao: FilledButton.tonalIcon(
        onPressed: () {},
        icon: const Icon(Icons.add),
        label: const Text('Novo Goleiro'),
      ),
      child: const _MensagemSemDados(),
    );
  }
}

class _MapaDesempenho extends StatelessWidget {
  const _MapaDesempenho();

  @override
  Widget build(BuildContext context) {
    return _Bloco(
      titulo: 'Mapa de desempenho',
      child: const _MensagemSemDados(),
    );
  }
}

class _SessoesRecentes extends StatelessWidget {
  const _SessoesRecentes();

  @override
  Widget build(BuildContext context) {
    final dashboard = context.watch<DashboardProvider>();
    final sessoes = (dashboard.data?.sessoesRecentes ?? const []).take(3).map((
      sessao,
    ) {
      final titulo = sessao['title']?.toString() ?? 'Sessão sem título';
      final tipo = sessao['session_type']?.toString();
      return tipo == null || tipo.isEmpty ? titulo : '$titulo • $tipo';
    }).toList();

    return _Bloco(
      titulo: 'Sessões recentes',
      child: dashboard.isLoading && sessoes.isEmpty
          ? const _MensagemSemDados(texto: 'Carregando dados da API')
          : sessoes.isEmpty
          ? const _MensagemSemDados()
          : Column(
              children: [
                for (final sessao in sessoes) ...[
                  Row(
                    children: [
                      const Icon(
                        Icons.event_available_outlined,
                        color: AppColors.textSecondary,
                      ),
                      const SizedBox(width: 10),
                      Expanded(child: Text(sessao)),
                    ],
                  ),
                  if (sessao != sessoes.last) const Divider(height: 24),
                ],
              ],
            ),
    );
  }
}

class _EnvioRapido extends StatelessWidget {
  const _EnvioRapido();

  @override
  Widget build(BuildContext context) {
    return _Bloco(
      titulo: 'Envio rápido',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const TextField(
            decoration: InputDecoration(
              labelText: 'Nome do goleiro',
              prefixIcon: Icon(Icons.person_outline),
            ),
          ),
          const SizedBox(height: 12),
          const TextField(
            decoration: InputDecoration(
              labelText: 'Clube',
              prefixIcon: Icon(Icons.shield_outlined),
            ),
          ),
          const SizedBox(height: 12),
          _BotaoGradiente(
            icon: Icons.cloud_upload_outlined,
            label: 'Enviar Vídeo',
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}

class ClubesScreen extends StatefulWidget {
  const ClubesScreen({super.key});

  @override
  State<ClubesScreen> createState() => _ClubesScreenState();
}

class _ClubesScreenState extends State<ClubesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<ClubProvider>().load();
      }
    });
  }

  Future<void> _abrirFormularioNovoClube() async {
    final criado = await showDialog<bool>(
      context: context,
      builder: (_) => const _DialogNovoClube(),
    );

    if (criado == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Clube cadastrado com sucesso.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final clubProvider = context.watch<ClubProvider>();
    final clubes = clubProvider.clubs;
    final carregando = clubProvider.isLoading && clubes.isEmpty;

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: 'Clubes',
              subtitulo:
                  'Gestão dos clubes atendidos pela plataforma de análise de goleiros',
              acao: 'Novo Clube',
              icone: Icons.shield_outlined,
              onAcao: _abrirFormularioNovoClube,
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Clubes cadastrados',
              child: carregando
                  ? const _MensagemSemDados(texto: 'Carregando clubes')
                  : clubProvider.errorMessage != null && clubes.isEmpty
                  ? _MensagemSemDados(texto: clubProvider.errorMessage!)
                  : clubes.isEmpty
                  ? const _MensagemSemDados(
                      texto: 'Nenhum clube cadastrado ainda',
                    )
                  : Column(
                      children: [
                        for (final clube in clubes) ...[
                          _LinhaClube(clube: clube),
                          if (clube != clubes.last) const Divider(height: 24),
                        ],
                      ],
                    ),
            ),
          ),
        ),
      ],
    );
  }
}

class _LinhaClube extends StatelessWidget {
  const _LinhaClube({required this.clube});

  final Club clube;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(Icons.shield_outlined, color: AppColors.textSecondary),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                clube.name,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                (clube.city == null || clube.city!.isEmpty)
                    ? 'Cidade não informada'
                    : clube.city!,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DialogNovoClube extends StatefulWidget {
  const _DialogNovoClube();

  @override
  State<_DialogNovoClube> createState() => _DialogNovoClubeState();
}

class _DialogNovoClubeState extends State<_DialogNovoClube> {
  final _formKey = GlobalKey<FormState>();
  final _nomeController = TextEditingController();
  final _cidadeController = TextEditingController();
  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _nomeController.dispose();
    _cidadeController.dispose();
    super.dispose();
  }

  Future<void> _salvar() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    setState(() {
      _salvando = true;
      _erro = null;
    });

    final clube = Club(
      id: '',
      name: _nomeController.text.trim(),
      city: _cidadeController.text.trim().isEmpty
          ? null
          : _cidadeController.text.trim(),
    );

    final sucesso = await context.read<ClubProvider>().createClub(clube);

    if (!mounted) return;

    if (sucesso) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _salvando = false;
        _erro = 'Não foi possível cadastrar o clube. Tente novamente.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Novo Clube'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _nomeController,
                enabled: !_salvando,
                decoration: const InputDecoration(labelText: 'Nome do clube'),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Informe o nome do clube.'
                    : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _cidadeController,
                enabled: !_salvando,
                decoration: const InputDecoration(
                  labelText: 'Cidade (opcional)',
                ),
              ),
              if (_erro != null) ...[
                const SizedBox(height: 14),
                Text(_erro!, style: const TextStyle(color: AppColors.error)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _salvando ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _salvando ? null : _salvar,
          child: _salvando
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Salvar'),
        ),
      ],
    );
  }
}

class GoleirosScreen extends StatefulWidget {
  const GoleirosScreen({super.key});

  @override
  State<GoleirosScreen> createState() => _GoleirosScreenState();
}

class _GoleirosScreenState extends State<GoleirosScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<GoalkeeperProvider>().loadAll();
        context.read<ClubProvider>().load();
      }
    });
  }

  Future<void> _abrirFormularioNovoGoleiro() async {
    final clubes = context.read<ClubProvider>().clubs;

    if (clubes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Cadastre um clube antes de adicionar um goleiro.'),
        ),
      );
      return;
    }

    final criado = await showDialog<bool>(
      context: context,
      builder: (_) => _DialogNovoGoleiro(clubes: clubes),
    );

    if (criado == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Goleiro cadastrado com sucesso.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final goalkeeperProvider = context.watch<GoalkeeperProvider>();
    final goleiros = goalkeeperProvider.goalkeepers;
    final carregando = goalkeeperProvider.isLoading && goleiros.isEmpty;

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: 'Goleiros',
              subtitulo:
                  'Acompanhamento técnico individual, evolução e indicadores de desempenho',
              acao: 'Novo Goleiro',
              icone: Icons.sports_handball_outlined,
              onAcao: _abrirFormularioNovoGoleiro,
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Goleiros cadastrados',
              child: carregando
                  ? const _MensagemSemDados(texto: 'Carregando goleiros')
                  : goalkeeperProvider.errorMessage != null && goleiros.isEmpty
                  ? _MensagemSemDados(texto: goalkeeperProvider.errorMessage!)
                  : goleiros.isEmpty
                  ? const _MensagemSemDados(
                      texto: 'Nenhum goleiro cadastrado ainda',
                    )
                  : Column(
                      children: [
                        for (final goleiro in goleiros) ...[
                          _LinhaGoleiro(goleiro: goleiro),
                          if (goleiro != goleiros.last)
                            const Divider(height: 24),
                        ],
                      ],
                    ),
            ),
          ),
        ),
      ],
    );
  }
}

class _LinhaGoleiro extends StatelessWidget {
  const _LinhaGoleiro({required this.goleiro});

  final Goalkeeper goleiro;

  @override
  Widget build(BuildContext context) {
    final detalhes = [
      if ((goleiro.dominantHand ?? '').isNotEmpty)
        'Mão dominante: ${goleiro.dominantHand}',
      if (goleiro.heightCm != null) '${goleiro.heightCm} cm',
      if (goleiro.weightKg != null) '${goleiro.weightKg} kg',
    ].join(' • ');

    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(
            Icons.sports_handball_outlined,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                goleiro.name,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                detalhes.isEmpty ? 'Sem detalhes adicionais' : detalhes,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DialogNovoGoleiro extends StatefulWidget {
  const _DialogNovoGoleiro({required this.clubes});

  final List<Club> clubes;

  @override
  State<_DialogNovoGoleiro> createState() => _DialogNovoGoleiroState();
}

class _DialogNovoGoleiroState extends State<_DialogNovoGoleiro> {
  final _formKey = GlobalKey<FormState>();
  final _nomeController = TextEditingController();
  final _alturaController = TextEditingController();
  final _pesoController = TextEditingController();
  String? _clubeId;
  String? _maoDominante;
  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _nomeController.dispose();
    _alturaController.dispose();
    _pesoController.dispose();
    super.dispose();
  }

  Future<void> _salvar() async {
    final formValido = _formKey.currentState?.validate() ?? false;
    if (!formValido || _clubeId == null) {
      setState(() {
        _erro = _clubeId == null ? 'Selecione um clube.' : null;
      });
      return;
    }

    setState(() {
      _salvando = true;
      _erro = null;
    });

    final goleiro = Goalkeeper(
      id: '',
      clubId: _clubeId!,
      name: _nomeController.text.trim(),
      dominantHand: _maoDominante,
      heightCm: int.tryParse(_alturaController.text.trim()),
      weightKg: double.tryParse(
        _pesoController.text.trim().replaceAll(',', '.'),
      ),
    );

    final sucesso = await context.read<GoalkeeperProvider>().createGoalkeeper(
      goleiro,
    );

    if (!mounted) return;

    if (sucesso) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _salvando = false;
        _erro = 'Não foi possível cadastrar o goleiro. Tente novamente.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Novo Goleiro'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _nomeController,
                enabled: !_salvando,
                decoration: const InputDecoration(labelText: 'Nome'),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Informe o nome do goleiro.'
                    : null,
              ),
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: _clubeId,
                decoration: const InputDecoration(labelText: 'Clube'),
                items: widget.clubes
                    .map(
                      (clube) => DropdownMenuItem(
                        value: clube.id,
                        child: Text(clube.name),
                      ),
                    )
                    .toList(),
                onChanged: _salvando
                    ? null
                    : (value) => setState(() => _clubeId = value),
              ),
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: _maoDominante,
                decoration: const InputDecoration(
                  labelText: 'Mão dominante (opcional)',
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'Esquerda',
                    child: Text('Esquerda'),
                  ),
                  DropdownMenuItem(value: 'Direita', child: Text('Direita')),
                  DropdownMenuItem(
                    value: 'Ambidestro',
                    child: Text('Ambidestro'),
                  ),
                ],
                onChanged: _salvando
                    ? null
                    : (value) => setState(() => _maoDominante = value),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _alturaController,
                enabled: !_salvando,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Altura em cm (opcional)',
                ),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _pesoController,
                enabled: !_salvando,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(
                  labelText: 'Peso em kg (opcional)',
                ),
              ),
              if (_erro != null) ...[
                const SizedBox(height: 14),
                Text(_erro!, style: const TextStyle(color: AppColors.error)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _salvando ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _salvando ? null : _salvar,
          child: _salvando
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Salvar'),
        ),
      ],
    );
  }
}

class VideosScreen extends StatefulWidget {
  const VideosScreen({super.key});

  @override
  State<VideosScreen> createState() => _VideosScreenState();
}

class _VideosScreenState extends State<VideosScreen> {
  String? _clubeId;
  String? _goleiroId;
  String? _sessaoId;

  List<Goalkeeper> _goleirosDoClube = [];
  List<TrainingSession> _sessoesDoGoleiro = [];
  bool _carregandoGoleiros = false;
  bool _carregandoSessoes = false;

  PlatformFile? _arquivoSelecionado;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<ClubProvider>().load();
      }
    });
  }

  void _limparSelecao() {
    setState(() {
      _clubeId = null;
      _goleiroId = null;
      _sessaoId = null;
      _goleirosDoClube = [];
      _sessoesDoGoleiro = [];
      _arquivoSelecionado = null;
    });
  }

  Future<void> _selecionarClube(String? clubeId) async {
    setState(() {
      _clubeId = clubeId;
      _goleiroId = null;
      _sessaoId = null;
      _goleirosDoClube = [];
      _sessoesDoGoleiro = [];
      _arquivoSelecionado = null;
    });

    if (clubeId == null) return;

    setState(() => _carregandoGoleiros = true);
    try {
      final goleiros = await context
          .read<GoalkeeperProvider>()
          .getGoalkeepersByClubId(clubeId);
      if (mounted) {
        setState(() => _goleirosDoClube = goleiros);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Não foi possível carregar os goleiros do clube.'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _carregandoGoleiros = false);
      }
    }
  }

  Future<void> _selecionarGoleiro(String? goleiroId) async {
    setState(() {
      _goleiroId = goleiroId;
      _sessaoId = null;
      _sessoesDoGoleiro = [];
      _arquivoSelecionado = null;
    });

    if (goleiroId == null) return;

    setState(() => _carregandoSessoes = true);
    try {
      final sessoes = await context
          .read<TrainingSessionProvider>()
          .getSessionsByGoalkeeperId(goleiroId);
      if (mounted) {
        setState(() => _sessoesDoGoleiro = sessoes);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Não foi possível carregar as sessões do goleiro.'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _carregandoSessoes = false);
      }
    }
  }

  void _selecionarSessao(String? sessaoId) {
    setState(() {
      _sessaoId = sessaoId;
      _arquivoSelecionado = null;
    });

    if (sessaoId != null) {
      context.read<VideoProvider>().loadBySession(sessaoId);
    }
  }

  Future<void> _selecionarArquivo() async {
    final resultado = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['mp4', 'mov', 'avi', 'mkv'],
      withData: true,
    );

    if (resultado == null || resultado.files.isEmpty) return;

    setState(() => _arquivoSelecionado = resultado.files.single);
  }

  Future<void> _enviarVideo() async {
    final arquivo = _arquivoSelecionado;
    final sessaoId = _sessaoId;

    if (arquivo == null || sessaoId == null || arquivo.bytes == null) {
      return;
    }

    final videoProvider = context.read<VideoProvider>();
    final sucesso = await videoProvider.uploadVideo(
      trainingSessionId: sessaoId,
      filename: arquivo.name,
      bytes: arquivo.bytes!,
    );

    if (!mounted) return;

    if (sucesso) {
      setState(() => _arquivoSelecionado = null);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Vídeo enviado com sucesso.')));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            videoProvider.uploadError ?? 'Não foi possível enviar o vídeo.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final clubProvider = context.watch<ClubProvider>();
    final videoProvider = context.watch<VideoProvider>();

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: 'Vídeos',
              subtitulo:
                  'Envios, processamento por IA e organização do acervo técnico',
              acao: 'Limpar seleção',
              icone: Icons.videocam_outlined,
              onAcao: _limparSelecao,
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Selecionar destino do vídeo',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: _clubeId,
                    decoration: const InputDecoration(labelText: 'Clube'),
                    items: clubProvider.clubs
                        .map(
                          (clube) => DropdownMenuItem(
                            value: clube.id,
                            child: Text(clube.name),
                          ),
                        )
                        .toList(),
                    onChanged: _selecionarClube,
                  ),
                  const SizedBox(height: 14),
                  DropdownButtonFormField<String>(
                    initialValue: _goleiroId,
                    decoration: InputDecoration(
                      labelText: 'Goleiro',
                      helperText: _carregandoGoleiros
                          ? 'Carregando goleiros...'
                          : null,
                    ),
                    items: _goleirosDoClube
                        .map(
                          (goleiro) => DropdownMenuItem(
                            value: goleiro.id,
                            child: Text(goleiro.name),
                          ),
                        )
                        .toList(),
                    onChanged: _clubeId == null ? null : _selecionarGoleiro,
                  ),
                  const SizedBox(height: 14),
                  DropdownButtonFormField<String>(
                    initialValue: _sessaoId,
                    decoration: InputDecoration(
                      labelText: 'Sessão de treino',
                      helperText: _carregandoSessoes
                          ? 'Carregando sessões...'
                          : null,
                    ),
                    items: _sessoesDoGoleiro
                        .map(
                          (sessao) => DropdownMenuItem(
                            value: sessao.id,
                            child: Text(sessao.title),
                          ),
                        )
                        .toList(),
                    onChanged: _goleiroId == null ? null : _selecionarSessao,
                  ),
                ],
              ),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 20),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Enviar vídeo',
              child: _sessaoId == null
                  ? const _MensagemSemDados(
                      texto:
                          'Selecione uma sessão de treino para enviar um vídeo.',
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                _arquivoSelecionado?.name ??
                                    'Nenhum arquivo selecionado',
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ),
                            const SizedBox(width: 12),
                            OutlinedButton.icon(
                              onPressed: videoProvider.isUploading
                                  ? null
                                  : _selecionarArquivo,
                              icon: const Icon(Icons.attach_file),
                              label: const Text('Selecionar arquivo'),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        _BotaoGradiente(
                          icon: Icons.cloud_upload_outlined,
                          label: videoProvider.isUploading
                              ? 'Enviando...'
                              : 'Enviar Vídeo',
                          onPressed:
                              (_arquivoSelecionado == null ||
                                  videoProvider.isUploading)
                              ? null
                              : _enviarVideo,
                        ),
                        if (videoProvider.isUploading) ...[
                          const SizedBox(height: 14),
                          LinearProgressIndicator(
                            value: videoProvider.uploadProgress,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '${(videoProvider.uploadProgress * 100).toStringAsFixed(0)}%',
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: AppColors.textSecondary),
                          ),
                        ],
                      ],
                    ),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Vídeos da sessão selecionada',
              child: _sessaoId == null
                  ? const _MensagemSemDados(
                      texto: 'Selecione uma sessão para ver os vídeos enviados.',
                    )
                  : videoProvider.isLoading && videoProvider.videos.isEmpty
                  ? const _MensagemSemDados(texto: 'Carregando vídeos')
                  : videoProvider.errorMessage != null &&
                        videoProvider.videos.isEmpty
                  ? _MensagemSemDados(texto: videoProvider.errorMessage!)
                  : videoProvider.videos.isEmpty
                  ? const _MensagemSemDados(
                      texto: 'Nenhum vídeo enviado nesta sessão ainda',
                    )
                  : Column(
                      children: [
                        for (final video in videoProvider.videos) ...[
                          _LinhaVideo(video: video),
                          if (video != videoProvider.videos.last)
                            const Divider(height: 24),
                        ],
                      ],
                    ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Rotulo em PT-BR para os estados oficiais do pipeline de IA
/// (ProcessingJobStatus - ver SPRINT5_REPORT.md e AI_WORKER_ARCHITECTURE.md).
String _rotuloStatusVideo(Video video) {
  final jobStatus = video.jobStatus;
  switch (jobStatus) {
    case 'QUEUED':
      return 'Na fila';
    case 'DOWNLOADING':
      return 'Baixando do R2';
    case 'PREPROCESSING':
      return 'Pré-processando';
    case 'INFERENCE':
      return 'Em processamento (IA)';
    case 'POSTPROCESSING':
      return 'Pós-processando';
    case 'GENERATING_REPORT':
      return 'Gerando relatório';
    case 'UPLOADING_RESULTS':
      return 'Enviando resultados';
    case 'COMPLETED':
      return 'Concluído';
    case 'FAILED':
      return 'Falha';
    case 'CANCELLED':
      return 'Cancelado';
  }
  if (video.uploadStatus == 'COMPLETED') return 'Concluído';
  if (video.uploadStatus == 'FAILED') return 'Falha';
  if (video.uploadStatus == 'UPLOADED') return 'No R2';
  return 'Enviado';
}

class _LinhaVideo extends StatelessWidget {
  const _LinhaVideo({required this.video});

  final Video video;

  @override
  Widget build(BuildContext context) {
    final tamanhoMb = video.fileSizeBytes != null
        ? '${(video.fileSizeBytes! / (1024 * 1024)).toStringAsFixed(1)} MB'
        : null;

    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(
            Icons.videocam_outlined,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                video.originalFilename ?? video.filename,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                tamanhoMb ?? 'Tamanho não informado',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
        const SizedBox(width: 14),
        _Etiqueta(texto: _rotuloStatusVideo(video)),
      ],
    );
  }
}

class AnalisesScreen extends StatelessWidget {
  const AnalisesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Análises',
      subtitulo:
          'Leitura técnica dos vídeos com eventos, tendências e recomendações',
      acao: 'Nova Análise',
      icone: Icons.analytics_outlined,
      metricas: [
        _MetricaSecao('Concluídas', '94', 'Validadas por treinador'),
        _MetricaSecao('Em revisão', '11', 'Aguardando parecer'),
        _MetricaSecao('Precisão média', '91%', 'Eventos detectados'),
      ],
      itens: [
        _ItemSecao('Defesas em queda', 'Rafael Monteiro • concluída'),
        _ItemSecao('Saída do gol', 'Caio Nascimento • processando'),
        _ItemSecao('Reposição curta', 'Bruna Alves • revisão técnica'),
      ],
    );
  }
}

class SessoesTreinoScreen extends StatefulWidget {
  const SessoesTreinoScreen({super.key});

  @override
  State<SessoesTreinoScreen> createState() => _SessoesTreinoScreenState();
}

class _SessoesTreinoScreenState extends State<SessoesTreinoScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<TrainingSessionProvider>().loadAll();
        context.read<GoalkeeperProvider>().loadAll();
      }
    });
  }

  Future<void> _abrirFormularioNovaSessao() async {
    final goleiros = context.read<GoalkeeperProvider>().goalkeepers;

    if (goleiros.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Cadastre um goleiro antes de criar uma sessão.'),
        ),
      );
      return;
    }

    final criado = await showDialog<bool>(
      context: context,
      builder: (_) => _DialogNovaSessao(goleiros: goleiros),
    );

    if (criado == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sessão de treino criada com sucesso.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final sessionProvider = context.watch<TrainingSessionProvider>();
    final goalkeeperProvider = context.watch<GoalkeeperProvider>();
    final sessoes = sessionProvider.sessions;
    final carregando = sessionProvider.isLoading && sessoes.isEmpty;

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: 'Sessões de Treino',
              subtitulo:
                  'Planejamento e histórico de treinos orientados por dados de desempenho',
              acao: 'Nova Sessão',
              icone: Icons.event_note_outlined,
              onAcao: _abrirFormularioNovaSessao,
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Sessões cadastradas',
              child: carregando
                  ? const _MensagemSemDados(texto: 'Carregando sessões')
                  : sessionProvider.errorMessage != null && sessoes.isEmpty
                  ? _MensagemSemDados(texto: sessionProvider.errorMessage!)
                  : sessoes.isEmpty
                  ? const _MensagemSemDados(
                      texto: 'Nenhuma sessão de treino cadastrada ainda',
                    )
                  : Column(
                      children: [
                        for (final sessao in sessoes) ...[
                          _LinhaSessao(
                            sessao: sessao,
                            nomeGoleiro: _nomeGoleiro(
                              goalkeeperProvider.goalkeepers,
                              sessao.goalkeeperId,
                            ),
                          ),
                          if (sessao != sessoes.last)
                            const Divider(height: 24),
                        ],
                      ],
                    ),
            ),
          ),
        ),
      ],
    );
  }

  String _nomeGoleiro(List<Goalkeeper> goleiros, String goalkeeperId) {
    for (final goleiro in goleiros) {
      if (goleiro.id == goalkeeperId) {
        return goleiro.name;
      }
    }
    return 'Goleiro não identificado';
  }
}

class _LinhaSessao extends StatelessWidget {
  const _LinhaSessao({required this.sessao, required this.nomeGoleiro});

  final TrainingSession sessao;
  final String nomeGoleiro;

  @override
  Widget build(BuildContext context) {
    final data = sessao.sessionDate;
    final dataFormatada =
        '${data.day.toString().padLeft(2, '0')}/'
        '${data.month.toString().padLeft(2, '0')}/${data.year}';

    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(
            Icons.event_note_outlined,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                sessao.title,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                '${sessao.sessionType} • $nomeGoleiro • $dataFormatada',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DialogNovaSessao extends StatefulWidget {
  const _DialogNovaSessao({required this.goleiros});

  final List<Goalkeeper> goleiros;

  @override
  State<_DialogNovaSessao> createState() => _DialogNovaSessaoState();
}

class _DialogNovaSessaoState extends State<_DialogNovaSessao> {
  final _formKey = GlobalKey<FormState>();
  final _tituloController = TextEditingController();
  final _tipoController = TextEditingController();
  final _notasController = TextEditingController();
  String? _goleiroId;
  DateTime? _data;
  bool _salvando = false;
  String? _erro;

  @override
  void dispose() {
    _tituloController.dispose();
    _tipoController.dispose();
    _notasController.dispose();
    super.dispose();
  }

  Future<void> _selecionarData() async {
    final agora = DateTime.now();
    final selecionada = await showDatePicker(
      context: context,
      initialDate: _data ?? agora,
      firstDate: DateTime(agora.year - 2),
      lastDate: DateTime(agora.year + 2),
    );

    if (selecionada != null) {
      setState(() => _data = selecionada);
    }
  }

  Future<void> _salvar() async {
    final formValido = _formKey.currentState?.validate() ?? false;

    if (!formValido || _goleiroId == null || _data == null) {
      setState(() {
        _erro = _goleiroId == null
            ? 'Selecione um goleiro.'
            : _data == null
            ? 'Selecione a data da sessão.'
            : null;
      });
      return;
    }

    setState(() {
      _salvando = true;
      _erro = null;
    });

    final sessao = TrainingSession(
      id: '',
      goalkeeperId: _goleiroId!,
      title: _tituloController.text.trim(),
      sessionType: _tipoController.text.trim(),
      sessionDate: _data!,
      notes: _notasController.text.trim().isEmpty
          ? null
          : _notasController.text.trim(),
    );

    final sucesso = await context
        .read<TrainingSessionProvider>()
        .createSession(sessao);

    if (!mounted) return;

    if (sucesso) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _salvando = false;
        _erro = 'Não foi possível criar a sessão. Tente novamente.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Nova Sessão de Treino'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _tituloController,
                enabled: !_salvando,
                decoration: const InputDecoration(labelText: 'Título'),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Informe o título da sessão.'
                    : null,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _tipoController,
                enabled: !_salvando,
                decoration: const InputDecoration(
                  labelText: 'Tipo de sessão',
                  hintText: 'Ex.: Treino técnico, Jogo-treino...',
                ),
                validator: (value) => (value == null || value.trim().isEmpty)
                    ? 'Informe o tipo de sessão.'
                    : null,
              ),
              const SizedBox(height: 14),
              DropdownButtonFormField<String>(
                initialValue: _goleiroId,
                decoration: const InputDecoration(labelText: 'Goleiro'),
                items: widget.goleiros
                    .map(
                      (goleiro) => DropdownMenuItem(
                        value: goleiro.id,
                        child: Text(goleiro.name),
                      ),
                    )
                    .toList(),
                onChanged: _salvando
                    ? null
                    : (value) => setState(() => _goleiroId = value),
              ),
              const SizedBox(height: 14),
              InkWell(
                onTap: _salvando ? null : _selecionarData,
                child: InputDecorator(
                  decoration: const InputDecoration(
                    labelText: 'Data da sessão',
                  ),
                  child: Text(
                    _data == null
                        ? 'Selecionar data'
                        : '${_data!.day.toString().padLeft(2, '0')}/'
                              '${_data!.month.toString().padLeft(2, '0')}/${_data!.year}',
                  ),
                ),
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: _notasController,
                enabled: !_salvando,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Notas (opcional)',
                ),
              ),
              if (_erro != null) ...[
                const SizedBox(height: 14),
                Text(_erro!, style: const TextStyle(color: AppColors.error)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _salvando ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _salvando ? null : _salvar,
          child: _salvando
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Salvar'),
        ),
      ],
    );
  }
}

class RelatoriosScreen extends StatelessWidget {
  const RelatoriosScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Relatórios',
      subtitulo:
          'Relatórios profissionais para comissão técnica, clubes e atletas',
      acao: 'Gerar Relatório',
      icone: Icons.description_outlined,
      metricas: [
        _MetricaSecao('Relatórios emitidos', '41', 'Últimos 30 dias'),
        _MetricaSecao('Compartilhados', '29', 'Com clubes'),
        _MetricaSecao('Pendentes', '6', 'Aguardando análise'),
      ],
      itens: [
        _ItemSecao('Evolução mensal - Rafael', 'PDF pronto • enviado ao clube'),
        _ItemSecao('Comparativo Sub-20', 'Em montagem • 6 goleiros'),
        _ItemSecao('Relatório de retorno', 'Bruna Alves • revisão final'),
      ],
    );
  }
}

class TelegramScreen extends StatelessWidget {
  const TelegramScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Telegram',
      subtitulo:
          'Notificações automáticas para treinadores, clubes e responsáveis técnicos',
      acao: 'Configurar Canal',
      icone: Icons.send_outlined,
      metricas: [
        _MetricaSecao('Canais ativos', '8', 'Clubes conectados'),
        _MetricaSecao('Alertas enviados', '156', 'No mês atual'),
        _MetricaSecao('Falhas', '1', 'Requer atenção'),
      ],
      itens: [
        _ItemSecao('Alertas de análise concluída', 'Ativo para 8 clubes'),
        _ItemSecao('Resumo semanal de goleiros', 'Enviado toda segunda-feira'),
        _ItemSecao('Notificação de erro em vídeo', 'Ativa para treinadores'),
      ],
    );
  }
}

String _rotuloPapel(String role) {
  switch (role) {
    case 'system_admin':
      return 'Administrador do Sistema';
    case 'clube':
      return 'Clube';
    case 'treinador':
      return 'Treinador';
    case 'analista':
      return 'Analista';
    default:
      return role;
  }
}

class UsuariosScreen extends StatefulWidget {
  const UsuariosScreen({super.key});

  @override
  State<UsuariosScreen> createState() => _UsuariosScreenState();
}

class _UsuariosScreenState extends State<UsuariosScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<UserProvider>().loadAll();
        context.read<ClubProvider>().load();
      }
    });
  }

  String _nomeClube(List<Club> clubes, String? clubeId) {
    if (clubeId == null) return 'Acesso global (sem clube)';
    for (final clube in clubes) {
      if (clube.id == clubeId) return clube.name;
    }
    return 'Clube não identificado';
  }

  @override
  Widget build(BuildContext context) {
    final userProvider = context.watch<UserProvider>();
    final clubProvider = context.watch<ClubProvider>();
    final usuarios = userProvider.users;
    final carregando = userProvider.isLoading && usuarios.isEmpty;

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: 'Usuários',
              subtitulo:
                  'Acessos de treinadores, analistas e gestores dos clubes',
              acao: 'Atualizar',
              icone: Icons.group_outlined,
              onAcao: () => context.read<UserProvider>().loadAll(),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Usuários cadastrados',
              child: carregando
                  ? const _MensagemSemDados(texto: 'Carregando usuários')
                  : userProvider.isForbidden
                  ? _MensagemSemDados(
                      texto:
                          userProvider.errorMessage ??
                          'Acesso restrito a administradores.',
                    )
                  : userProvider.errorMessage != null && usuarios.isEmpty
                  ? _MensagemSemDados(texto: userProvider.errorMessage!)
                  : usuarios.isEmpty
                  ? const _MensagemSemDados(
                      texto: 'Nenhum usuário cadastrado ainda',
                    )
                  : Column(
                      children: [
                        for (final usuario in usuarios) ...[
                          _LinhaUsuario(
                            usuario: usuario,
                            nomeClube: _nomeClube(
                              clubProvider.clubs,
                              usuario.clubId,
                            ),
                          ),
                          if (usuario != usuarios.last)
                            const Divider(height: 24),
                        ],
                      ],
                    ),
            ),
          ),
        ),
      ],
    );
  }
}

class _LinhaUsuario extends StatelessWidget {
  const _LinhaUsuario({required this.usuario, required this.nomeClube});

  final AuthUser usuario;
  final String nomeClube;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: const Icon(Icons.person_outline, color: AppColors.textSecondary),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                usuario.name,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                '${usuario.email} • $nomeClube',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
        const SizedBox(width: 14),
        _Etiqueta(texto: _rotuloPapel(usuario.role)),
      ],
    );
  }
}

class ConfiguracoesScreen extends StatefulWidget {
  const ConfiguracoesScreen({super.key});

  @override
  State<ConfiguracoesScreen> createState() => _ConfiguracoesScreenState();
}

class _ConfiguracoesScreenState extends State<ConfiguracoesScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<ClubProvider>().load();
        final auth = context.read<AuthProvider>();
        if (auth.user?.role == 'system_admin') {
          context.read<SystemProvider>().loadR2Health();
        }
      }
    });
  }

  String _nomeClube(List<Club> clubes, String? clubeId) {
    if (clubeId == null) return 'Acesso global (sem clube)';
    for (final clube in clubes) {
      if (clube.id == clubeId) return clube.name;
    }
    return 'Clube não identificado';
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final clubProvider = context.watch<ClubProvider>();
    final usuario = auth.user;
    final ehAdmin = usuario?.role == 'system_admin';

    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: 'Configurações',
              subtitulo:
                  'Seu perfil, permissões do papel atual e status do sistema',
              acao: 'Atualizar',
              icone: Icons.settings_outlined,
              onAcao: () {
                context.read<ClubProvider>().load();
                if (ehAdmin) context.read<SystemProvider>().loadR2Health();
              },
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Meu perfil',
              child: usuario == null
                  ? const _MensagemSemDados()
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _LinhaPerfil(rotulo: 'Nome', valor: usuario.name),
                        const Divider(height: 24),
                        _LinhaPerfil(rotulo: 'E-mail', valor: usuario.email),
                        const Divider(height: 24),
                        _LinhaPerfil(
                          rotulo: 'Papel',
                          valor: _rotuloPapel(usuario.role),
                        ),
                        const Divider(height: 24),
                        _LinhaPerfil(
                          rotulo: 'Clube',
                          valor: _nomeClube(
                            clubProvider.clubs,
                            usuario.clubId,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 20),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Permissões por papel',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  _LinhaPermissao(
                    papel: 'Administrador do Sistema',
                    descricao:
                        'Acesso total: vê todos os clubes, cria novos clubes, gerencia usuários e configurações globais.',
                  ),
                  Divider(height: 24),
                  _LinhaPermissao(
                    papel: 'Clube',
                    descricao:
                        'Acessa exclusivamente os próprios dados (goleiros, sessões, vídeos, análises e relatórios do clube).',
                  ),
                  Divider(height: 24),
                  _LinhaPermissao(
                    papel: 'Treinador',
                    descricao: 'Acessa exclusivamente os dados do próprio clube.',
                  ),
                  Divider(height: 24),
                  _LinhaPermissao(
                    papel: 'Analista',
                    descricao: 'Acessa exclusivamente os dados do próprio clube.',
                  ),
                ],
              ),
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Sistema',
              child: !ehAdmin
                  ? const _MensagemSemDados(
                      texto:
                          'Status do sistema visível apenas para administradores.',
                    )
                  : Consumer<SystemProvider>(
                      builder: (context, systemProvider, _) {
                        if (systemProvider.isLoading) {
                          return const _MensagemSemDados(
                            texto: 'Verificando conexão com o R2...',
                          );
                        }
                        final r2 = systemProvider.r2Health;
                        if (r2 == null) {
                          return _MensagemSemDados(
                            texto:
                                systemProvider.errorMessage ??
                                'Não foi possível verificar o R2.',
                          );
                        }
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _LinhaPerfil(
                              rotulo: 'Armazenamento (R2)',
                              valor: r2.bucket,
                            ),
                            const Divider(height: 24),
                            _LinhaPerfil(
                              rotulo: 'Leitura',
                              valor: r2.readAccess ? 'OK' : 'Falhou',
                            ),
                            const Divider(height: 24),
                            _LinhaPerfil(
                              rotulo: 'Escrita',
                              valor: r2.writeAccess ? 'OK' : 'Falhou',
                            ),
                          ],
                        );
                      },
                    ),
            ),
          ),
        ),
      ],
    );
  }
}

class _LinhaPerfil extends StatelessWidget {
  const _LinhaPerfil({required this.rotulo, required this.valor});

  final String rotulo;
  final String valor;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 140,
          child: Text(
            rotulo,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
        ),
        Expanded(
          child: Text(
            valor,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
        ),
      ],
    );
  }
}

class _LinhaPermissao extends StatelessWidget {
  const _LinhaPermissao({required this.papel, required this.descricao});

  final String papel;
  final String descricao;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          papel,
          style: Theme.of(
            context,
          ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 4),
        Text(
          descricao,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}

class _TelaSecao extends StatelessWidget {
  const _TelaSecao({
    required this.titulo,
    required this.subtitulo,
    required this.acao,
    required this.icone,
    required this.metricas,
    required this.itens,
  });

  final String titulo;
  final String subtitulo;
  final String acao;
  final IconData icone;
  final List<_MetricaSecao> metricas;
  final List<_ItemSecao> itens;

  @override
  Widget build(BuildContext context) {
    return CustomScrollView(
      slivers: [
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
            child: _CabecalhoSecao(
              titulo: titulo,
              subtitulo: subtitulo,
              acao: acao,
              icone: icone,
            ),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          sliver: SliverToBoxAdapter(child: _GradeMetricas(metricas: metricas)),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
          sliver: SliverToBoxAdapter(
            child: _Bloco(
              titulo: 'Acompanhamento',
              child: Column(
                children: [
                  for (final item in itens) ...[
                    _LinhaSecao(item: item, icone: icone),
                    if (item != itens.last) const Divider(height: 24),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _CabecalhoSecao extends StatelessWidget {
  const _CabecalhoSecao({
    required this.titulo,
    required this.subtitulo,
    required this.acao,
    required this.icone,
    this.onAcao,
  });

  final String titulo;
  final String subtitulo;
  final String acao;
  final IconData icone;
  final VoidCallback? onAcao;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compacto = constraints.maxWidth < 760;
        final tituloWidget = Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.hover,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Icon(icone, color: AppColors.textSecondary),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    titulo,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitulo,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
        final botao = FilledButton.icon(
          onPressed: onAcao ?? () {},
          icon: Icon(icone),
          label: Text(acao),
        );

        if (compacto) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [tituloWidget, const SizedBox(height: 14), botao],
          );
        }

        return Row(
          children: [
            Expanded(child: tituloWidget),
            const SizedBox(width: 18),
            botao,
          ],
        );
      },
    );
  }
}

class _GradeMetricas extends StatelessWidget {
  const _GradeMetricas({required this.metricas});

  final List<_MetricaSecao> metricas;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final colunas = constraints.maxWidth >= 980
            ? 3
            : constraints.maxWidth >= 640
            ? 2
            : 1;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: metricas.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: colunas,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
            mainAxisExtent: 126,
          ),
          itemBuilder: (context, index) =>
              _CardMetricaSecao(metrica: metricas[index]),
        );
      },
    );
  }
}

class _CardMetricaSecao extends StatelessWidget {
  const _CardMetricaSecao({required this.metrica});

  final _MetricaSecao metrica;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              metrica.valor,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
            const Spacer(),
            Text(
              metrica.titulo,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 2),
            Text(
              metrica.subtitulo,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}

class _LinhaSecao extends StatelessWidget {
  const _LinhaSecao({required this.item, required this.icone});

  final _ItemSecao item;
  final IconData icone;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppColors.hover,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Icon(icone, color: AppColors.textSecondary),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.titulo,
                style: Theme.of(
                  context,
                ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                item.subtitulo,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
        IconButton(
          tooltip: 'Abrir',
          onPressed: () {},
          icon: const Icon(Icons.open_in_new),
        ),
      ],
    );
  }
}

class _Bloco extends StatelessWidget {
  const _Bloco({required this.titulo, required this.child, this.acao});

  final String titulo;
  final Widget child;
  final Widget? acao;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    titulo,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                ?acao,
              ],
            ),
            const SizedBox(height: 18),
            child,
          ],
        ),
      ),
    );
  }
}

class _MensagemSemDados extends StatelessWidget {
  const _MensagemSemDados({this.texto = 'Sem dados disponíveis'});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const Icon(Icons.info_outline, color: AppColors.textSecondary),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            texto,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
        ),
      ],
    );
  }
}

/// Chip de status (Sprint UX-01, Design System v2). Reconhece por
/// palavra-chave (case-insensitive) o status de processamento real
/// (Queued/Running/Completed/Failed) e escolhe a cor correspondente; textos
/// não reconhecidos (ex.: papel de usuário, que reutiliza este mesmo
/// widget) recebem um chip neutro - nunca mais sempre verde independente do
/// conteúdo.
class _Etiqueta extends StatelessWidget {
  const _Etiqueta({required this.texto});

  final String texto;

  static const _palavrasFila = [
    'fila',
    'queued',
    'pendente',
  ];
  static const _palavrasEmAndamento = [
    'processando',
    'processamento',
    'baixando',
    'pré-processando',
    'pre-processando',
    'pós-processando',
    'pos-processando',
    'gerando',
    'enviando',
    'running',
    'downloading',
    'preprocessing',
    'inference',
    'postprocessing',
    'uploading',
  ];
  static const _palavrasConcluido = [
    'conclu',
    'completed',
    'sucesso',
    'confirmado',
  ];
  static const _palavrasFalha = [
    'falha',
    'failed',
    'erro',
    'cancelado',
    'cancelled',
  ];

  Color? get _corStatus {
    final normalizado = texto.toLowerCase();
    if (_palavrasFila.any(normalizado.contains)) return AppColors.statusQueued;
    if (_palavrasEmAndamento.any(normalizado.contains)) {
      return AppColors.warning;
    }
    if (_palavrasConcluido.any(normalizado.contains)) return AppColors.success;
    if (_palavrasFalha.any(normalizado.contains)) return AppColors.error;
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final cor = _corStatus;
    final corTexto = cor ?? AppColors.neutralChipText;
    final corFundo = cor?.withValues(alpha: 0.14) ?? AppColors.neutralChipBackground;
    final corBorda = cor?.withValues(alpha: 0.4) ?? AppColors.neutralChipBorder;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: corFundo,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: corBorda),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: corTexto, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            texto,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: corTexto,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _ItemMenu {
  const _ItemMenu(this.titulo, this.icone, this.caminho);

  final String titulo;
  final IconData icone;
  final String caminho;
}

class _Indicador {
  const _Indicador(this.titulo, this.valor, this.subtitulo, this.icone);

  final String titulo;
  final String valor;
  final String subtitulo;
  final IconData icone;
}

class _Analise {
  const _Analise(
    this.clube,
    this.goleiro,
    this.foco,
    this.status,
    this.progresso,
  );

  final String clube;
  final String goleiro;
  final String foco;
  final String status;
  final double progresso;
}

class _MetricaSecao {
  const _MetricaSecao(this.titulo, this.valor, this.subtitulo);

  final String titulo;
  final String valor;
  final String subtitulo;
}

class _ItemSecao {
  const _ItemSecao(this.titulo, this.subtitulo);

  final String titulo;
  final String subtitulo;
}
