"""Download/upload REAL de bytes via URL assinada do R2 (Sprint W3).

Nunca usa credenciais mestras nem SDK do S3 - so HTTP simples contra a URL
ja assinada, obtida via `infrastructure.backend_client` (Boundary Enforcement).
"""
