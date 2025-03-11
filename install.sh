#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para exibir mensagens de status
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Verificar se está rodando em macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "Este script só funciona em macOS"
    exit 1
fi

# Verificar se Python 3.9+ está instalado
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 não encontrado. Por favor, instale o Python 3.9 ou superior"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION < 3.9" | bc -l) )); then
    print_error "Python 3.9 ou superior é necessário (versão atual: $PYTHON_VERSION)"
    exit 1
fi

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 não encontrado. Por favor, instale o pip3"
    exit 1
fi

# Verificar se o Cursor IDE está instalado
if ! [ -d "/Applications/Cursor.app" ]; then
    print_warning "Cursor IDE não encontrado em /Applications/"
    print_warning "Por favor, instale o Cursor IDE de https://cursor.sh"
fi

# Criar ambiente virtual se não existir
if [ ! -d "supercursor_env" ]; then
    print_status "Criando ambiente virtual..."
    python3 -m venv supercursor_env
else
    print_warning "Ambiente virtual já existe"
fi

# Ativar ambiente virtual
print_status "Ativando ambiente virtual..."
source supercursor_env/bin/activate

# Atualizar pip
print_status "Atualizando pip..."
pip install --upgrade pip

# Instalar dependências
print_status "Instalando dependências..."
pip install -r requirements.txt

# Verificar se arquivo .env existe
if [ ! -f ".env" ]; then
    print_warning "Arquivo .env não encontrado"
    print_warning "Por favor, crie um arquivo .env com sua chave da API OpenAI:"
    echo "OPENAI_API_KEY=sua_chave_aqui" > .env
    print_warning "Edite o arquivo .env e adicione sua chave da API OpenAI"
fi

# Instalar o pacote em modo de desenvolvimento
print_status "Instalando SuperCursor em modo de desenvolvimento..."
pip install -e .

print_status "Instalação concluída!"
print_status "Para iniciar o SuperCursor, execute: python -m super_cursor.main"

# Verificar permissões de acessibilidade
print_warning "IMPORTANTE: O SuperCursor precisa de permissões de acessibilidade"
print_warning "Por favor, vá em Preferências do Sistema > Segurança e Privacidade > Privacidade > Acessibilidade"
print_warning "e adicione o Terminal ou seu IDE à lista de aplicativos permitidos" 