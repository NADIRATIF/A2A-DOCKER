FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

RUN uv init --package my-project

WORKDIR /app/my-project

RUN uv add git+https://github.com/djsamseng/A2A#subdirectory=samples/python --branch prefixPythonPackage

RUN uv add click requests python-dotenv

RUN mkdir -p src/my_project

COPY src ./src

RUN touch requirements.txt

CMD ["uv", "run", "my-project"]
