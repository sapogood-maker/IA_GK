"""Clientes de infraestrutura externa do Worker, agrupados por sistema:

- `redis/`: fila (consumer group) e Lock distribuido por video.
- `backend_client/`: cliente HTTP da Worker API do backend.
- `storage/`: acesso ao Cloudflare R2 via URL assinada (reservado ate a W3).

Nenhum modulo aqui contem regra de negocio - apenas mecanica de comunicacao
com os tres contratos publicos do Boundary Enforcement.
"""
