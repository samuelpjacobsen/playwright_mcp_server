# MCP Playwright Server

Um servidor MCP (Model Context Protocol) para automação web usando Playwright, com suporte para N8N via SSE.

## 🚀 Funcionalidades

- ✅ Navegação para URLs
- ✅ Cliques em elementos  
- ✅ Captura de screenshots
- ✅ Digitação de texto
- ✅ Seleção de opções em dropdowns
- ✅ Aguardar elementos aparecerem
- ✅ Obter conteúdo da página
- ✅ Fechar navegador
- ✅ Abrir novas abas
- ✅ Hover sobre elementos

## 📦 Instalação

```bash
# Clone o repositório
git clone <seu-repo>
cd mcp-playwright-server

# Instale as dependências
pip install -r requirements.txt

# Instale os navegadores do Playwright
playwright install chromium
```

## 🎯 Uso

### Para Claude Desktop (MCP via stdio):
```bash
python server.py
```

### Para N8N (MCP via SSE):
```bash
python server_sse.py
```
Acesse: http://localhost:8000/sse

## 🔧 Configuração no N8N

Use o nó **MCP Client** com:
- **URL**: `https://seu-servidor.com/sse`
- **Transport**: SSE

## 🛠️ Ferramentas Disponíveis

| Ferramenta | Descrição | Parâmetros |
|------------|-----------|------------|
| `navigate` | Navega para URL | `url` (obrigatório) |
| `click` | Clica em elemento | `selector` (obrigatório) |
| `take_screenshot` | Captura screenshot | `path` (opcional) |
| `type_text` | Digita texto | `selector`, `text` |
| `get_page_content` | Obtém HTML da página | - |
| `close_browser` | Fecha navegador | - |

## 🌐 Deploy

### Coolify / Docker:
O projeto inclui suporte completo para deploy em containers.

### Variáveis de Ambiente:
- `PORT`: Porta do servidor (padrão: 8000)
- `HOST`: Host do servidor (padrão: 0.0.0.0)

## 🧪 Testes

```bash
# Testar servidor SSE
python test_sse.py
```

## 📡 Endpoints

- `GET /health` - Health check
- `GET /sse` - Stream SSE para N8N
- `POST /mcp` - Comandos MCP
- `GET /` - Informações do servidor

## 🔗 Compatibilidade

- ✅ **Claude Desktop** (via `server.py`)
- ✅ **N8N** (via `server_sse.py`)
- ✅ **Coolify Deploy**
- ✅ **Docker**

## 📋 Licença

MIT