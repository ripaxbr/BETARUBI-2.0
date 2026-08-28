"""Catálogo inicial de obras em domínio público para o WEBPLAY.

Regra de segurança: a obra só entra como candidata quando a proteção patrimonial
já expirou na jurisdição indicada. A edição/tradução específica deve ser verificada
separadamente; o sistema não assume que uma tradução moderna é domínio público.
"""

PUBLIC_DOMAIN_BOOKS = [
    ("Dom Casmurro", "Machado de Assis", "Brasil", "Português", "Romance", 1899, "https://www.dominiopublico.gov.br"),
    ("Memórias Póstumas de Brás Cubas", "Machado de Assis", "Brasil", "Português", "Romance/Sátira", 1881, "https://www.dominiopublico.gov.br"),
    ("O Cortiço", "Aluísio Azevedo", "Brasil", "Português", "Naturalismo", 1890, "https://www.dominiopublico.gov.br"),
    ("Iracema", "José de Alencar", "Brasil", "Português", "Romantismo", 1865, "https://www.dominiopublico.gov.br"),
    ("Os Sertões", "Euclides da Cunha", "Brasil", "Português", "Literatura/História", 1902, "https://www.dominiopublico.gov.br"),
    ("Alice's Adventures in Wonderland", "Lewis Carroll", "Reino Unido", "Inglês", "Fantasia", 1865, "https://www.gutenberg.org"),
    ("Frankenstein; or, The Modern Prometheus", "Mary Shelley", "Reino Unido", "Inglês", "Terror/Fantasia", 1818, "https://www.gutenberg.org"),
    ("The Adventures of Sherlock Holmes", "Arthur Conan Doyle", "Reino Unido", "Inglês", "Mistério", 1892, "https://www.gutenberg.org"),
    ("The Great Gatsby", "F. Scott Fitzgerald", "Estados Unidos", "Inglês", "Drama", 1925, "https://www.gutenberg.org"),
    ("Les Misérables", "Victor Hugo", "França", "Francês", "Romance", 1862, "https://www.gutenberg.org"),
    ("The Count of Monte Cristo", "Alexandre Dumas", "França", "Francês", "Aventura", 1844, "https://www.gutenberg.org"),
    ("Don Quixote", "Miguel de Cervantes", "Espanha", "Espanhol", "Aventura/Sátira", 1605, "https://www.gutenberg.org"),
    ("Crime and Punishment", "Fyodor Dostoevsky", "Rússia", "Russo", "Romance Psicológico", 1866, "https://www.gutenberg.org"),
    ("War and Peace", "Leo Tolstoy", "Rússia", "Russo", "Histórico", 1869, "https://www.gutenberg.org"),
]

def ensure_public_domain_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS acervo_livres (
        id BIGSERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        autor TEXT NOT NULL,
        pais TEXT NOT NULL,
        idioma TEXT NOT NULL,
        genero TEXT NOT NULL,
        ano_publicacao INTEGER,
        fonte_oficial TEXT NOT NULL,
        jurisdicao_verificada TEXT NOT NULL DEFAULT 'requer_verificacao_por_edicao',
        status_direitos TEXT NOT NULL DEFAULT 'candidato_dominio_publico',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(titulo, autor, idioma)
    )""")
    for row in PUBLIC_DOMAIN_BOOKS:
        conn.execute("""INSERT INTO acervo_livres
            (titulo, autor, pais, idioma, genero, ano_publicacao, fonte_oficial)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (titulo, autor, idioma) DO NOTHING""", row)

def seed_public_domain(conn):
    ensure_public_domain_schema(conn)
