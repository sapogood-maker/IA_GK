import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'providers/auth_provider.dart';
import 'providers/dashboard_provider.dart';
import 'repositories/auth_repository.dart';
import 'repositories/dashboard_repository.dart';
import 'services/api_client.dart';
import 'services/session_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final preferences = await SharedPreferences.getInstance();
  final sessionService = SessionService(preferences);
  final apiClient = ApiClient(sessionService);
  final authRepository = AuthRepository(apiClient, sessionService);
  final dashboardRepository = DashboardRepository(apiClient);
  final authProvider = AuthProvider(authRepository, sessionService);

  await authProvider.initialize();

  runApp(
    GkPerformanceApp(
      authProvider: authProvider,
      dashboardProvider: DashboardProvider(dashboardRepository),
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
  });

  final AuthProvider authProvider;
  final DashboardProvider dashboardProvider;

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF28C76F);
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
        ChangeNotifierProvider<DashboardProvider>.value(
          value: dashboardProvider,
        ),
      ],
      child: Builder(
        builder: (context) {
          return MaterialApp.router(
            title: 'GK Desempenho',
            debugShowCheckedModeBanner: false,
            themeMode: ThemeMode.dark,
            theme: ThemeData(
              useMaterial3: true,
              brightness: Brightness.dark,
              colorScheme: ColorScheme.fromSeed(
                seedColor: seed,
                brightness: Brightness.dark,
                surface: const Color(0xFF101512),
              ),
              scaffoldBackgroundColor: const Color(0xFF070A08),
              fontFamily: 'Roboto',
              cardTheme: CardThemeData(
                color: const Color(0xFF111A15),
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: const BorderSide(color: Color(0xFF26342B)),
                ),
              ),
              inputDecorationTheme: InputDecorationTheme(
                filled: true,
                fillColor: const Color(0xFF101812),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF29382F)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF29382F)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: seed, width: 1.4),
                ),
              ),
            ),
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
                              ?.copyWith(color: const Color(0xFFFFB4AB)),
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
                  backgroundColor: const Color(0xFF0C110E),
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
                  color: const Color(0xFF9CAEA2),
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
        FilledButton.icon(
          onPressed: () {},
          icon: const Icon(Icons.cloud_upload_outlined),
          label: const Text('Enviar Vídeo'),
        ),
      ],
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
      width: 288,
      decoration: const BoxDecoration(
        color: Color(0xFF0C110E),
        border: Border(right: BorderSide(color: Color(0xFF233128))),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
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
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: const Color(0xFF28C76F),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.sports_soccer, color: Color(0xFF061008)),
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
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0,
                ),
              ),
              Text(
                'Análise de goleiros',
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: const Color(0xFF8FA196)),
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
      color: ativo ? const Color(0xFF153823) : Colors.transparent,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Row(
            children: [
              Icon(
                item.icone,
                size: 21,
                color: ativo
                    ? const Color(0xFF55E08F)
                    : const Color(0xFF9BAAA1),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  item.titulo,
                  style: TextStyle(
                    color: ativo
                        ? const Color(0xFFEAF7EF)
                        : const Color(0xFFB7C5BC),
                    fontWeight: ativo ? FontWeight.w700 : FontWeight.w500,
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
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.memory_outlined, color: Color(0xFF55E08F)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'IA em operação',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            LinearProgressIndicator(
              value: totalEmProcessamento == null
                  ? null
                  : totalEmProcessamento > 0
                  ? 0.68
                  : 0,
            ),
            const SizedBox(height: 8),
            Text(
              texto,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
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
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
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
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: const Color(0xFF183B25),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    indicador.icone,
                    color: const Color(0xFF55E08F),
                    size: 22,
                  ),
                ),
                const Spacer(),
                const Icon(
                  Icons.trending_up,
                  color: Color(0xFF55E08F),
                  size: 20,
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
                      ?.copyWith(fontWeight: FontWeight.w900, letterSpacing: 0),
            ),
            const SizedBox(height: 4),
            Text(
              indicador.titulo,
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 2),
            Text(
              indicador.subtitulo,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
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
            color: const Color(0xFF16251B),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.sports_soccer, color: Color(0xFF55E08F)),
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
                ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
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
                        color: Color(0xFF55E08F),
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
          FilledButton.icon(
            onPressed: () {},
            icon: const Icon(Icons.cloud_upload_outlined),
            label: const Text('Enviar Vídeo'),
          ),
        ],
      ),
    );
  }
}

class ClubesScreen extends StatelessWidget {
  const ClubesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Clubes',
      subtitulo:
          'Gestão dos clubes atendidos pela plataforma de análise de goleiros',
      acao: 'Novo Clube',
      icone: Icons.shield_outlined,
      metricas: [
        _MetricaSecao('Clubes ativos', '12', 'Base e profissional'),
        _MetricaSecao('Goleiros vinculados', '36', 'Com monitoramento ativo'),
        _MetricaSecao('Vídeos no mês', '74', 'Enviados pelos clubes'),
      ],
      itens: [
        _ItemSecao(
          'São Paulo FC Sub-20',
          '8 goleiros • 24 análises concluídas',
        ),
        _ItemSecao('Palmeiras Base', '6 goleiros • 18 vídeos processados'),
        _ItemSecao('Santos FC Feminino', '4 goleiras • 12 relatórios emitidos'),
      ],
    );
  }
}

class GoleirosScreen extends StatelessWidget {
  const GoleirosScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Goleiros',
      subtitulo:
          'Acompanhamento técnico individual, evolução e indicadores de desempenho',
      acao: 'Novo Goleiro',
      icone: Icons.sports_handball_outlined,
      metricas: [
        _MetricaSecao('Goleiros ativos', '36', 'Em acompanhamento'),
        _MetricaSecao('GK Score médio', '82,4', 'Últimos 30 dias'),
        _MetricaSecao('Alertas técnicos', '9', 'Prioridade para treino'),
      ],
      itens: [
        _ItemSecao('Rafael Monteiro', 'GK 88 • destaque em reflexo'),
        _ItemSecao('Bruna Alves', 'GK 85 • reposição acima da média'),
        _ItemSecao('Caio Nascimento', 'GK 79 • evolução em cobertura'),
      ],
    );
  }
}

class VideosScreen extends StatelessWidget {
  const VideosScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Vídeos',
      subtitulo: 'Envios, processamento por IA e organização do acervo técnico',
      acao: 'Enviar Vídeo',
      icone: Icons.videocam_outlined,
      metricas: [
        _MetricaSecao('Vídeos enviados', '128', 'Total disponível'),
        _MetricaSecao('Processando', '17', 'Na fila da IA'),
        _MetricaSecao('Com erro', '2', 'Exigem revisão'),
      ],
      itens: [
        _ItemSecao(
          'Treino de reflexo - Rafael',
          'Concluído • 18 eventos detectados',
        ),
        _ItemSecao('Cruzamentos - Bruna', 'Processando • 64%'),
        _ItemSecao('Jogo-treino - Caio', 'Aguardando IA • enviado hoje'),
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

class SessoesTreinoScreen extends StatelessWidget {
  const SessoesTreinoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Sessões de Treino',
      subtitulo:
          'Planejamento e histórico de treinos orientados por dados de desempenho',
      acao: 'Nova Sessão',
      icone: Icons.event_note_outlined,
      metricas: [
        _MetricaSecao('Sessões agendadas', '18', 'Próximos 7 dias'),
        _MetricaSecao('Sessões concluídas', '63', 'No mês atual'),
        _MetricaSecao('Focos técnicos', '7', 'Fundamentos monitorados'),
      ],
      itens: [
        _ItemSecao('Treino de reflexo', 'Hoje, 09:30 • Rafael Monteiro'),
        _ItemSecao('Cruzamentos laterais', 'Ontem, 16:10 • Bruna Alves'),
        _ItemSecao('Saída curta com pés', '08/06, 14:00 • Caio Nascimento'),
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

class UsuariosScreen extends StatelessWidget {
  const UsuariosScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Usuários',
      subtitulo:
          'Acessos de treinadores, analistas e gestores dos clubes brasileiros',
      acao: 'Novo Usuário',
      icone: Icons.group_outlined,
      metricas: [
        _MetricaSecao('Usuários ativos', '48', 'Com acesso liberado'),
        _MetricaSecao('Treinadores', '31', 'Perfil técnico'),
        _MetricaSecao('Convites pendentes', '5', 'Aguardando aceite'),
      ],
      itens: [
        _ItemSecao('Marcos Oliveira', 'Treinador • São Paulo FC Sub-20'),
        _ItemSecao('Fernanda Costa', 'Analista • Santos FC Feminino'),
        _ItemSecao('Rogério Lima', 'Gestor • Palmeiras Base'),
      ],
    );
  }
}

class ConfiguracoesScreen extends StatelessWidget {
  const ConfiguracoesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _TelaSecao(
      titulo: 'Configurações',
      subtitulo:
          'Parâmetros da plataforma, integrações e preferências de análise',
      acao: 'Salvar',
      icone: Icons.settings_outlined,
      metricas: [
        _MetricaSecao('Integrações', '4', 'Serviços conectados'),
        _MetricaSecao('Modelos de análise', '3', 'Perfis técnicos'),
        _MetricaSecao('Permissões', '6', 'Papéis configurados'),
      ],
      itens: [
        _ItemSecao('Critérios do GK Score', 'Pesos técnicos por fundamento'),
        _ItemSecao('Armazenamento de vídeos', 'Bucket R2 conectado'),
        _ItemSecao('Notificações', 'Telegram e alertas internos'),
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
  });

  final String titulo;
  final String subtitulo;
  final String acao;
  final IconData icone;

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
                color: const Color(0xFF183B25),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icone, color: const Color(0xFF55E08F)),
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
                      color: const Color(0xFF9CAEA2),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
        final botao = FilledButton.icon(
          onPressed: () {},
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
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
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
            color: const Color(0xFF16251B),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icone, color: const Color(0xFF55E08F)),
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
                ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
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
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    titulo,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0,
                    ),
                  ),
                ),
                ?acao,
              ],
            ),
            const SizedBox(height: 16),
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
        const Icon(Icons.info_outline, color: Color(0xFF9CAEA2)),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            texto,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: const Color(0xFF9CAEA2)),
          ),
        ),
      ],
    );
  }
}

class _Etiqueta extends StatelessWidget {
  const _Etiqueta({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF173823),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF2F6E45)),
      ),
      child: Text(
        texto,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: const Color(0xFFB9F6CA),
          fontWeight: FontWeight.w700,
        ),
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
