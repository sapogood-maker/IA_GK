import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

void main() {
  runApp(const GkPerformanceApp());
}

final _router = GoRouter(
  initialLocation: '/painel',
  redirect: (context, state) => state.uri.path == '/' ? '/painel' : null,
  routes: [
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
  const GkPerformanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF28C76F);
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
      routerConfig: _router,
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

class PainelScreen extends StatelessWidget {
  const PainelScreen({super.key});

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
    const indicadores = [
      _Indicador(
        'Vídeos Enviados',
        '128',
        '+18 esta semana',
        Icons.video_library_outlined,
      ),
      _Indicador(
        'Análises Concluídas',
        '94',
        '73% da fila processada',
        Icons.check_circle_outline,
      ),
      _Indicador(
        'GK Score Médio',
        '82,4',
        '+4,8 vs. mês anterior',
        Icons.speed_outlined,
      ),
      _Indicador(
        'Goleiros Ativos',
        '36',
        '12 clubes monitorados',
        Icons.sports_handball_outlined,
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
            const LinearProgressIndicator(value: 0.68),
            const SizedBox(height: 8),
            Text(
              '17 vídeos em processamento',
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
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
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
    const analises = [
      _Analise(
        'São Paulo FC Sub-20',
        'Rafael Monteiro',
        'Defesas em queda',
        'Concluída',
        0.92,
      ),
      _Analise(
        'Palmeiras Base',
        'Caio Nascimento',
        'Saída do gol',
        'Processando',
        0.64,
      ),
      _Analise(
        'Santos FC Feminino',
        'Bruna Alves',
        'Reposição curta',
        'Revisão técnica',
        0.81,
      ),
      _Analise(
        'Grêmio Sub-17',
        'Henrique Lima',
        'Bolas aéreas',
        'Aguardando IA',
        0.28,
      ),
    ];

    return _Bloco(
      titulo: 'Fila de análises',
      acao: TextButton.icon(
        onPressed: () {},
        icon: const Icon(Icons.filter_list),
        label: const Text('Filtrar'),
      ),
      child: Column(
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
    const goleiros = [
      _Goleiro(
        'Rafael Monteiro',
        'São Paulo FC Sub-20',
        '88',
        'Reflexo',
        'Alta evolução',
      ),
      _Goleiro(
        'Bruna Alves',
        'Santos FC Feminino',
        '85',
        'Reposição',
        'Pronta para jogo',
      ),
      _Goleiro(
        'Caio Nascimento',
        'Palmeiras Base',
        '79',
        'Cobertura',
        'Atenção em cruzamentos',
      ),
    ];

    return _Bloco(
      titulo: 'Goleiros em destaque',
      acao: FilledButton.tonalIcon(
        onPressed: () {},
        icon: const Icon(Icons.add),
        label: const Text('Novo Goleiro'),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final columns = constraints.maxWidth >= 820 ? 3 : 1;
          return GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: goleiros.length,
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: columns,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              mainAxisExtent: 190,
            ),
            itemBuilder: (context, index) =>
                _CardGoleiro(goleiro: goleiros[index]),
          );
        },
      ),
    );
  }
}

class _CardGoleiro extends StatelessWidget {
  const _CardGoleiro({required this.goleiro});

  final _Goleiro goleiro;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: const Color(0xFF20452C),
                  child: Text(
                    goleiro.nome.characters.first,
                    style: const TextStyle(
                      color: Color(0xFFEAF7EF),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const Spacer(),
                _Etiqueta(texto: 'GK ${goleiro.score}'),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              goleiro.nome,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              goleiro.clube,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFF9CAEA2)),
            ),
            const Spacer(),
            Row(
              children: [
                const Icon(
                  Icons.bolt_outlined,
                  size: 18,
                  color: Color(0xFF55E08F),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    goleiro.fundamento,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              goleiro.alerta,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFFB7C5BC)),
            ),
          ],
        ),
      ),
    );
  }
}

class _MapaDesempenho extends StatelessWidget {
  const _MapaDesempenho();

  @override
  Widget build(BuildContext context) {
    const fundamentos = [
      _Fundamento('Reflexo', 0.88),
      _Fundamento('Posicionamento', 0.81),
      _Fundamento('Bolas aéreas', 0.74),
      _Fundamento('Um contra um', 0.78),
      _Fundamento('Reposição', 0.86),
    ];

    return _Bloco(
      titulo: 'Mapa de desempenho',
      child: Column(
        children: [
          for (final item in fundamentos) ...[
            Row(
              children: [
                SizedBox(width: 116, child: Text(item.nome)),
                Expanded(child: LinearProgressIndicator(value: item.valor)),
                const SizedBox(width: 12),
                Text('${(item.valor * 100).round()}%'),
              ],
            ),
            if (item != fundamentos.last) const SizedBox(height: 16),
          ],
        ],
      ),
    );
  }
}

class _SessoesRecentes extends StatelessWidget {
  const _SessoesRecentes();

  @override
  Widget build(BuildContext context) {
    const sessoes = [
      'Treino de reflexo • Hoje, 09:30',
      'Cruzamentos laterais • Ontem, 16:10',
      'Saída curta com pés • 08/06, 14:00',
    ];

    return _Bloco(
      titulo: 'Sessões recentes',
      child: Column(
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

class _Goleiro {
  const _Goleiro(
    this.nome,
    this.clube,
    this.score,
    this.fundamento,
    this.alerta,
  );

  final String nome;
  final String clube;
  final String score;
  final String fundamento;
  final String alerta;
}

class _Fundamento {
  const _Fundamento(this.nome, this.valor);

  final String nome;
  final double valor;
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
