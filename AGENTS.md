# Diretrizes permanentes do Orizon Sales

## Escopo e fluxo

- Este repositório contém o projeto Orizon Sales, demonstração de inteligência comercial para uma distribuidora fictícia.
- Siga a sequência e os critérios de conclusão de PLANEJAMENTO.md. Antes da primeira implementação, aguarde aprovação explícita do planejamento. Registre alterações de arquitetura, contrato ou regra de negócio nos documentos correspondentes.
- Use Python, Pandas, NumPy, SciPy, Plotly, Streamlit, Faker e Pytest conforme a responsabilidade de cada etapa. Mantenha o projeto executável localmente e adequado para demonstração gratuita.
- Escreva documentação, mensagens da interface, comentários e docstrings em português brasileiro. Use identificadores consistentes e nomes de colunas em snake_case.

## Dados e rastreabilidade

- Trabalhe exclusivamente com dados sintéticos. Não armazene credenciais, informações reais ou dados confidenciais no código, dados, logs ou documentação.
- Fixe a semente, a janela de referência e as versões das dependências para reproduzir a base e os defeitos. Mantenha metadados da execução e registre a versão das regras aplicadas.
- Trate os arquivos brutos como imutáveis. Grave dados tratados, quarentena e relatórios em diretórios separados. Execute a limpeza a partir dos brutos e mantenha rastreabilidade por arquivo, registro e regra.
- Documente granularidade, chaves, unidades, campos obrigatórios e regras de validação no dicionário de dados. Explique o efeito de cada transformação e reconcilie contagens e valores financeiros calculáveis.
- Use centavos inteiros para valores monetários armazenados e defina o arredondamento nas regras de negócio.

## Código, testes e apresentação

- Separe geração, qualidade, tratamento, indicadores e interface. A interface consome resultados do módulo analítico, onde ficam as fórmulas compartilhadas.
- Use Pytest para validar reprodutibilidade, casos de limpeza, integridade referencial, reconciliação e indicadores. Mantenha exemplos de teste pequenos e determinísticos.
- Exiba valores em reais, datas e números no padrão brasileiro. Use filtros coerentes, rótulos acessíveis e estados explícitos para ausência de dados ou indisponibilidade de indicadores.
- Mantenha o README.md com instalação, execução, testes, pipeline, limitações e instruções de demonstração. Versione código, configuração e documentação. Preserve as bases completas como artefatos reproduzíveis e inclua no Git apenas amostras pequenas quando necessárias.