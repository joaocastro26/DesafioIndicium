# Projeto de Pipeline ETL com Airflow

Este projeto demonstra a construção de um pipeline ETL (Extract, Transform, Load) para integrar dados de diferentes fontes em um Data Warehouse centralizado. A orquestração do fluxo de trabalho é realizada utilizando Apache Airflow, e todo o ambiente é gerenciado com Docker Compose para garantir a reprodutibilidade.

## ⚙️ Tecnologias Utilizadas
Apache Airflow: Orquestrador de workflows para agendamento, monitoramento e execução do pipeline ETL.

Docker e Docker Compose: Usados para criar e gerenciar um ambiente de desenvolvimento isolado, com todos os serviços necessários (bancos de dados, Airflow, etc.).

PostgreSQL: Utilizado tanto como banco de dados de origem (simulando o sistema transacional BanVic) quanto como Data Warehouse (DWH) de destino.

Python: Linguagem de programação para o desenvolvimento das tarefas de extração e carregamento de dados.

Pandas: Biblioteca para manipulação e processamento de dados em Python.

SQLAlchemy: Toolkit SQL para facilitar a conexão e a interação com os bancos de dados.

## 📁 Estrutura do Projeto
A estrutura do projeto é organizada da seguinte forma:

└── docker-compose.yml

├── dags/

│   └── banvic_pipeline.py

├── data/

├── dbdata/

├── dwhdata/

├── airflow_metadata/


dags/: Contém o código do pipeline ETL (banvic_pipeline.py) que é lido pelo Airflow.

data/: Diretório para armazenar os arquivos CSV extraídos temporariamente. 

dbdata/: Volume persistente para os dados do banco de origem.

dwhdata/: Volume persistente para os dados do Data Warehouse.

airflow_metadata/: Volume persistente para os metadados do Airflow.

docker-compose.yml: Arquivo de configuração que define e interconecta todos os serviços (contêineres) do projeto.

As pastas data, dbdata, dwhdata e airflow_metadata serão criadas automáticamente após a execução.

## 🚀 Como Executar o Projeto
Para colocar o projeto em funcionamento, você só precisa ter o Docker e o Docker Compose instalados na sua máquina.

Clone o Repositório:

```Bash
git clone https://github.com/joaocastro26/DesafioIndicium.git
cd DesafioIndicium
```
Inicie os Contêineres:
No diretório raiz do projeto, execute o comando abaixo para construir as imagens e iniciar todos os serviços em segundo plano.

```Bash

docker-compose up -d
```
Aguarde alguns minutos. Na primeira execução, o Docker irá baixar as imagens necessárias e os serviços de inicialização do Airflow configurarão o ambiente, incluindo a criação de um usuário administrador.

Acesse a Interface do Airflow:
Após os contêineres estarem em execução, abra seu navegador e acesse:
```Bash
http://localhost:8080
```
Faça login com as credenciais padrão:

```Bash
Login: airflow

Senha: airflow
```
Execute o Pipeline:
Na interface do Airflow, localize a DAG chamada banvic_pipeline. Você pode ativá-la e disparar uma execução manualmente clicando no botão de Play. O Airflow irá então executar as tarefas de extração e carregamento, movendo os dados das fontes para o Data Warehouse.

## 🎯 Visão Geral do Pipeline
O pipeline banvic_pipeline.py é um fluxo de trabalho ETL com três etapas principais:

Extração de Dados (extract):

Uma tarefa extrai dados do arquivo transacoes.csv.

Outra tarefa se conecta ao banco de dados PostgreSQL de origem (db) e extrai dados de múltiplas tabelas (agencias, clientes, contas, etc.).

Ambas as extrações rodam em paralelo e salvam os dados em arquivos CSV temporários.

Sincronização (sync):

Um operador de sincronização (EmptyOperator) garante que a próxima etapa só comece se todas as tarefas de extração tiverem sido concluídas com sucesso.

Carregamento de Dados (load):

A etapa final carrega os dados dos arquivos CSV extraídos para as tabelas correspondentes no Data Warehouse (dwh_postgres). A lógica de carregamento utiliza a função to_sql do pandas, que gerencia a criação das tabelas no destino, garantindo a idempotência do processo.
