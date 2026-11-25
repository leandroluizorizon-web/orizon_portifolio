# Orizon Sales

Dashboard de inteligência comercial da Orizon para uma distribuidora fictícia. O projeto demonstra a geração reproduzível, o diagnóstico, o tratamento, a análise exploratória e a apresentação comercial de 36 meses de dados.

## Abrir o dashboard

Use Python 3.11 a 3.13 e execute na raiz do projeto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O app lê o lote local `dados/processamento/base_padrao` e o perfil `dados/relatorios/base_padrao`. Se eles ainda não existirem, a primeira sessão gera, diagnostica e trata a base em um diretório temporário. A instância reutiliza o resultado em memória. As execuções persistidas pelo pipeline permanecem disponíveis para auditoria.

## Módulos

| Módulo | Conteúdo |
| --- | --- |
| Visão executiva | Indicadores centrais, evolução mensal e faturamento por filial |
| Desempenho comercial | Crescimento mensal e anual, evolução e sazonalidade |
| Análise financeira | Faturamento, descontos, tributos, custos e resultado por competência |
| Análise de clientes | Clientes ativos, frequência, segmentos e ticket |
| Desempenho dos produtos | Curva ABC e rentabilidade por produto |
| Comparação entre filiais | Receita, lucro, margem, pedidos, ticket e evolução |
| Desempenho dos vendedores | Ranking, evolução e tabela comparativa |
| Qualidade dos dados | Ocorrências por regra e reconciliação por tabela |

Os filtros comerciais são compartilhados entre módulos. Qualidade mostra o lote completo. A análise financeira usa despesas apenas quando os filtros incluem meses completos e filiais com cobertura confiável. Consulte o [planejamento](PLANEJAMENTO.md) para as fórmulas e a [análise exploratória](docs/analise_exploratoria.md) para os resultados da base padrão.

## Reproduzir o pipeline

Instale o projeto com as dependências de revisão para ter acesso aos quatro comandos:

```powershell
python -m pip install -e ".[teste,exploracao]"
orizon-gerar
orizon-diagnosticar
orizon-tratar
orizon-explorar
python -m pytest
```

O gerador parte de 100.000 itens válidos e produz 100.800 itens brutos depois de acrescentar duplicatas. A execução padrão cobre janeiro de 2023 a dezembro de 2025, com 5.000 clientes cadastrados, 500 produtos, cinco filiais e 30 vendedores. O manifesto registra sementes, versões de dependências, contagens e hashes SHA-256. Para reexecutar sem sobrescrever artefatos, indique destinos novos:

```powershell
orizon-gerar --destino dados/brutos/reproducao --semente 42 --semente-defeitos 137 --itens 100000
orizon-diagnosticar --origem dados/brutos/reproducao --destino dados/relatorios/reproducao
orizon-tratar --origem dados/brutos/reproducao --destino dados/processamento/reproducao
orizon-explorar --lote dados/processamento/reproducao --diagnostico dados/relatorios/reproducao --saida dados/relatorios/reproducao/analise.md
```

| Artefato | Local padrão |
| --- | --- |
| Nove tabelas brutas, trilha de injeção e manifesto | `dados/brutos/base_padrao/` |
| Perfil por tabela e ocorrências por regra | `dados/relatorios/base_padrao/` |
| Tabelas tratadas, quarentena, trilha e reconciliação | `dados/processamento/base_padrao/` |
| Relatório exploratório | `docs/analise_exploratoria.md` |

O diagnóstico lê somente as nove tabelas brutas. A taxa por regra usa o total bruto da tabela como denominador. A taxa geral conta cada registro afetado uma vez. A exposição financeira no CSV de ocorrências representa o valor observado da linha quando calculável. Linhas com múltiplas ocorrências podem aparecer mais de uma vez.

Consulte o [dicionário de dados](docs/dicionario_dados.md) e as [regras de transformação](docs/transformacoes.md). Os dados são inteiramente sintéticos. Os padrões observados refletem as hipóteses do gerador.

## Publicar a demonstração

1. Envie o código para o repositório GitHub destinado ao portfólio. Os arquivos gerados em `dados/` ficam fora do Git.
2. Na Streamlit Community Cloud, conecte o repositório e crie um app com o branch desejado e o caminho `app.py`.
3. Nas opções avançadas da implantação, selecione Python 3.12. A plataforma instala `requirements.txt`.
4. Abra a URL do app após a implantação e confirme que a visão executiva e o diagnóstico carregam. A base é preparada automaticamente no primeiro acesso de cada instância.

O projeto usa o plano gratuito da Streamlit Community Cloud e roda sem banco de dados externo. [Guia oficial de publicação](https://docs.streamlit.io/deploy/streamlit-community-cloud).