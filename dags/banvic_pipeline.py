import pandas as pd # Importa a biblioteca pandas para manipulação e análise de dados em DataFrames.
from sqlalchemy import create_engine # Importa a função create_engine do SQLAlchemy para criar a conexão com o banco de dados.
import os # Importa a biblioteca os para interagir com o sistema de arquivos, como criar diretórios e gerenciar caminhos.
from airflow import DAG # Importa a classe DAG, que é o objeto principal para definir um fluxo de trabalho (pipeline) no Airflow.
from airflow.operators.python import PythonOperator # Importa a classe PythonOperator, usada para executar uma função Python como uma tarefa do Airflow.
from airflow.operators.empty import EmptyOperator # Importa a classe EmptyOperator, uma tarefa que não faz nada, útil para organizar e sincronizar o fluxo do DAG.
from datetime import datetime # Importa a classe datetime para definir a data de início do DAG.

# Credenciais do banco de dados de ORIGEM foram alteradas para "propriedadeprivada" para não compartilhar informações que não me pertencem.
SOURCE_DB_USER = 'propriedadeprivada'
SOURCE_DB_PASSWORD = 'propriedadeprivada'
SOURCE_DB_HOST = 'propriedadeprivada'
SOURCE_DB_PORT = 'propriedadeprivada'
SOURCE_DB_NAME = 'propriedadeprivada'

# Credenciais do Data Warehouse de DESTINO (o banco 'banvic_dwh' no contêiner 'dwh_postgres').
DWH_DB_USER = 'dwh_user'
DWH_DB_PASSWORD = 'dwh_password'
DWH_DB_HOST = 'dwh_postgres'
DWH_DB_PORT = '5432'
DWH_DB_NAME = 'banvic_dwh'

def db_engine(origem=True):
 #Cria e retorna a engine do SQLAlchemy para o banco de dados.
 # A função usa o parâmetro origem para decidir qual conjunto de credenciais usar.
 if origem:
  # Constrói a string de conexão para o banco de dados de origem.
  return create_engine(f'postgresql+psycopg2://{SOURCE_DB_USER}:{SOURCE_DB_PASSWORD}@{SOURCE_DB_HOST}:{SOURCE_DB_PORT}/{SOURCE_DB_NAME}')
 else:
  # Constrói a string de conexão para o banco de dados de destino.
  return create_engine(f'postgresql+psycopg2://{DWH_DB_USER}:{DWH_DB_PASSWORD}@{DWH_DB_HOST}:{DWH_DB_PORT}/{DWH_DB_NAME}')

def extracao_transcoes(**argumentos):
#Extrai dados do arquivo transacoes.csv.
#Esta função lê um arquivo CSV local e salva uma cópia em um novo diretório com o padrão de data.

 data = argumentos['ds'] # 'ds' é uma macro do Airflow que fornece a data da execução do DAG (ex: '2025-09-05').

 nome_origem = 'transacoes'
 
 diretorio_destino = f'/opt/airflow/data/{data}/{nome_origem}' # Define o caminho do diretório onde o arquivo extraído será salvo.
 os.makedirs(diretorio_destino, exist_ok=True) # Cria o diretório de destino, se ele não existir.
 arquivo_destino = os.path.join(diretorio_destino, f'{nome_origem}.csv') # Constrói o caminho completo do arquivo de destino.

 arquivo_origem = '/opt/airflow/dags/transacoes.csv' # Define o caminho do arquivo de origem, que deve estar na pasta dags.

 try:
  df = pd.read_csv(arquivo_origem) # Lê o arquivo CSV de origem em um DataFrame do pandas.
  df.to_csv(arquivo_destino, index=False) # Salva o DataFrame no arquivo de destino, sem o índice padrão do pandas.
  print(f"Arquivo extraído com sucesso: {arquivo_destino}") # Imprime uma mensagem de sucesso no log.
 except FileNotFoundError:
  print(f"Erro: O arquivo {arquivo_origem} não foi encontrado dentro do contêiner.") # Captura o erro se o arquivo de origem não for encontrado.
  raise # Relança a exceção para que o Airflow marque a tarefa como falha.
 except Exception as e:
  print(f"Ocorreu um erro durante a extração: {e}") # Captura qualquer outra exceção inesperada.
  raise # Relança a exceção para o Airflow.

def extracao_sql(**argumentos):
    #Extrai dados de tabelas SQL (do banco `banvic`) e salva em arquivos CSV locais.
    #Os arquivos serão salvos em uma única pasta 'SQL'.
    
    data = argumentos['ds']
    tabelas_extrair = ['agencias', 'clientes', 'contas', 'colaboradores', 'propostas_credito']
    
    engine = db_engine(origem=True)

    try:
        with engine.connect() as conn:
            # Novo: Define um único diretório de destino para todos os arquivos SQL.
            diretorio_destino = f'/opt/airflow/data/{data}/SQL'
            os.makedirs(diretorio_destino, exist_ok=True) # Garante que a pasta 'SQL' exista.
            
            for nome_tabela in tabelas_extrair:
                # Novo: Define o caminho completo do arquivo, salvando-o diretamente na pasta 'SQL'.
                arquivo_destino = os.path.join(diretorio_destino, f'{nome_tabela}.csv')
                
                query = f"SELECT * FROM {nome_tabela}"
                df = pd.read_sql(query, conn)
                df.to_csv(arquivo_destino, index=False)
                print(f"Tabela '{nome_tabela}' extraída e salva em: {arquivo_destino}")
    except Exception as e:
        print(f"Ocorreu um erro durante a extração SQL: {e}")
        raise

def envio_dwh(**argumentos):
 """
 Lê os arquivos CSV extraídos e carrega os dados no Data Warehouse (PostgreSQL).
 """
 ds = argumentos['ds']
 
 tabelas_carregar = ['transacoes', 'agencias', 'clientes', 'contas', 'colaboradores', 'propostas_credito'] # Lista as tabelas para carregar no DWH.
 engine = db_engine(origem=False) # Cria a engine para conectar ao banco de dados de destino (DWH).

 try:
  with engine.connect() as conn: # Abre uma conexão.
   # Drop os tipos de dados antes de carregar, para garantir que não haja conflito.
   tipos = ['tipo_agencia', 'tipo_cliente', 'status_proposta'] # Lista os tipos de dados personalizados.
   for type_name in tipos: # Itera sobre os tipos de dados.
    try:
     # Executa um comando SQL para excluir o tipo de dado, se ele existir.
     conn.execute(f"DROP TYPE IF EXISTS public.{type_name} CASCADE;")
     print(f"Tipo de dado '{type_name}' excluído com sucesso (se existia).")
    except Exception as drop_error:
     print(f"Erro ao tentar excluir o tipo de dado '{type_name}': {drop_error}") # Em caso de erro na exclusão do tipo de dado.

   for nome_tabela in tabelas_carregar: # Itera sobre a lista de tabelas a serem carregadas.
    arquivo_caminho = f'/opt/airflow/data/{ds}/{nome_tabela}/{nome_tabela}.csv' # Constrói o caminho para o arquivo CSV extraído.

    if os.path.exists(arquivo_caminho): # Verifica se o arquivo CSV existe antes de tentar lê-lo.
     df = pd.read_csv(arquivo_caminho) # Lê o arquivo CSV em um DataFrame.

     # Usa o método to_sql para carregar o DataFrame no banco de dados.
     # if_exists='replace' garante que a tabela seja recriada a cada execução,
     # resolvendo o problema de idempotência.
     df.to_sql(nome_tabela, conn, if_exists='replace', index=False)
     print(f"Dados do arquivo {arquivo_caminho} carregados na tabela {nome_tabela} com sucesso.")
    else:
     print(f"Aviso: Arquivo {arquivo_caminho} não encontrado. Pulando...") # Imprime um aviso se o arquivo estiver faltando.
 except Exception as e:
  print(f"Ocorreu um erro durante o carregamento dos dados: {e}")
  raise

# Definição do DAG do Airflow
with DAG(
 dag_id='banvic_pipeline', # O ID único para o DAG.
 start_date=datetime(2025, 1, 1), # A data a partir da qual o Airflow pode começar a agendar execuções.
 schedule_interval='35 7 * * *', # Agendamento do DAG. Aqui, significa "todos os dias, às 04:35", o 7 foi colocado ao invés de 4 por conta do fuso horário brasileiro que é -3.
 catchup=False, # Define se o Airflow deve executar as DAGs que foram perdidas desde o start_date.
 tags=['desafio', 'banvic'] # Tags para ajudar a categorizar e filtrar o DAG na interface do Airflow.
) as dag:
 # --- Definição das Tarefas (Tasks) ---

 # Tarefa para extrair os dados do arquivo CSV.
 extrair_transacoes_task = PythonOperator(
  task_id='extrair_transacoes', # O ID único da tarefa.
  python_callable=extracao_transcoes, # A função Python que a tarefa irá executar.
 )

 # Tarefa para extrair os dados das tabelas SQL do banco de origem.
 extrair_sql_task = PythonOperator(
  task_id='extrair_sql',
  python_callable=extracao_sql,
 )

 # Tarefa de sincronização. Ela espera que as tarefas de extração acima sejam concluídas com sucesso.
 sincronizar_extracao = EmptyOperator(
  task_id='sincronizar_extracao',
  trigger_rule='all_success' # A regra de gatilho para executar esta tarefa apenas se todas as tarefas upstream forem bem-sucedidas.
 )
 
 # Tarefa para carregar os dados no Data Warehouse de destino.
 carregar_no_dwh = PythonOperator(
  task_id='envio_dwh',
  python_callable=envio_dwh,
 )

 # --- Orquestração ---

 # Define o fluxo de dependências.
 # As duas tarefas de extração ([...]) podem ser executadas em paralelo.
 # Ambas devem ser concluídas com sucesso antes que a tarefa de sincronização seja executada.
 # A tarefa de sincronização então dispara a tarefa de carregamento.
 [extrair_transacoes_task, extrair_sql_task] >> sincronizar_extracao >> carregar_no_dwh
