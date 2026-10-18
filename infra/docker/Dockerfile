
FROM python:3.11-slim

LABEL maintainer="Christian Lorenzo Oliveira Wislocki"
LABEL project="Berka Bank Full-Stack Data & Analytics"

# Evita geração de ficheiros .pyc e força logs em tempo real no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências de sistema necessárias para compilar psycopg2 e conectores
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as bibliotecas Python do projeto
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte e a aplicação Streamlit
COPY src/ /app/src/
COPY app/ /app/app/

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]