"""Produtores determinísticos de hipóteses (Sprint W34).

Cada arquivo é UMA função pura que olha um `TrackState`/`EntityState` e
devolve uma hipótese ou `None`. Deliberadamente chamado `producers/`, não
`rules/` - não há interpretador de regras, não há configuração externa,
não há despacho dinâmico. As condições são código, não dado (ver
documento arquitetural da W34, Seção 6)."""
